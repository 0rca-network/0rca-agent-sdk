"""
Property-based tests for market data service.
Tests API retry behavior and market data processing completeness.
"""

import pytest
import requests
import json
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings, HealthCheck
from requests.exceptions import Timeout, RequestException

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_data import MarketDataService, MCPAPIError, MarketDataResponse
from config import MCPConfig

class TestMarketDataService:
    """Property-based tests for MarketDataService"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = MCPConfig(
            api_endpoint="https://test-api.com/market-data",
            timeout_seconds=5,
            retry_attempts=1,
            api_key="test_api_key"
        )
        self.service = MarketDataService(self.config)
    
    @given(
        timeout_count=st.integers(min_value=1, max_value=3)
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_api_retry_behavior(self, timeout_count):
        """
        **Feature: mcp-market-data-agent, Property 2: API retry behavior**
        For any MCP API request that times out, the system should retry exactly once 
        before returning an error response.
        **Validates: Requirements 2.5**
        """
        # Mock the session.get method to simulate timeouts
        with patch.object(self.service.session, 'get') as mock_get:
            # Configure mock to timeout for the specified number of attempts
            mock_get.side_effect = [Timeout("Request timeout")] * timeout_count
            
            # Track the number of actual API calls made
            call_count = 0
            
            def count_calls(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                raise Timeout("Request timeout")
            
            mock_get.side_effect = count_calls
            
            # Patch time.sleep to avoid delays in tests
            with patch('time.sleep'):
                # Attempt to fetch market data
                with pytest.raises(MCPAPIError) as exc_info:
                    self.service.fetch_market_data(["BTC"])
                
                # Verify retry behavior: should make initial attempt + retry_attempts
                expected_calls = self.config.retry_attempts + 1
                assert mock_get.call_count == expected_calls
                
                # Verify error message indicates timeout failure
                assert "timeout" in str(exc_info.value).lower() or "failed after" in str(exc_info.value)
    
    @given(
        symbols=st.lists(
            st.text(min_size=2, max_size=10, alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), min_codepoint=65, max_codepoint=90)),
            min_size=1,
            max_size=5,
            unique=True  # Ensure unique symbols
        ),
        prices=st.lists(
            st.floats(min_value=0.01, max_value=100000.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        ),
        timestamps=st.lists(
            st.integers(min_value=1640995200000, max_value=2000000000000),  # Valid timestamp range
            min_size=1,
            max_size=5
        )
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_market_data_processing_completeness(self, symbols, prices, timestamps):
        """
        **Feature: mcp-market-data-agent, Property 3: Market data processing completeness**
        For any successful API response from MCP Market Data API, the system should extract 
        and validate price, market depth, and timestamp information before processing.
        **Validates: Requirements 2.1, 2.2, 2.3**
        """
        # Ensure we have matching lengths for test data
        min_length = min(len(symbols), len(prices), len(timestamps))
        symbols = symbols[:min_length]
        prices = prices[:min_length]
        timestamps = timestamps[:min_length]
        
        # Create mock API response with required fields
        mock_response_data = {}
        for i, symbol in enumerate(symbols):
            mock_response_data[symbol] = {
                "symbol": symbol,
                "price": prices[i],
                "timestamp": timestamps[i],
                "market_depth": {"bids": [], "asks": []},
                "volume_24h": 1000.0,
                "price_change_24h": 2.5
            }
        
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        
        with patch.object(self.service.session, 'get', return_value=mock_response):
            # Fetch and process market data
            result = self.service.get_market_summary(symbols)
            
            # Verify completeness: all symbols should be processed
            assert len(result) == len(symbols)
            
            # Verify each symbol has complete data extraction
            for symbol in symbols:
                assert symbol in result
                market_data = result[symbol]
                
                # Verify required fields are extracted and validated
                assert isinstance(market_data, MarketDataResponse)
                assert market_data.symbol == symbol
                assert isinstance(market_data.price, float)
                assert market_data.price > 0
                assert isinstance(market_data.timestamp, int)
                assert market_data.timestamp > 0
                assert isinstance(market_data.market_depth, dict)
                
                # Verify data integrity: extracted values match input
                original_data = mock_response_data[symbol]
                assert market_data.price == original_data["price"]
                assert market_data.timestamp == original_data["timestamp"]
    
    def test_api_error_handling_with_various_status_codes(self):
        """Test that API errors are handled appropriately for different status codes"""
        error_cases = [
            (401, "authentication"),
            (403, "forbidden"),
            (404, "not found"),
            (429, "rate limit"),
            (500, "server error"),
            (502, "server error"),
            (503, "server error")
        ]
        
        for status_code, expected_message_part in error_cases:
            mock_response = Mock()
            mock_response.status_code = status_code
            mock_response.json.return_value = {"error": f"Test error {status_code}"}
            mock_response.text = f"Error {status_code}"
            
            with patch.object(self.service.session, 'get', return_value=mock_response):
                with pytest.raises(MCPAPIError) as exc_info:
                    self.service.fetch_market_data(["BTC"])
                
                assert exc_info.value.status_code == status_code
                # Check that error message contains expected content (case insensitive)
                error_msg = str(exc_info.value).lower()
                assert expected_message_part in error_msg, f"Expected '{expected_message_part}' in '{error_msg}'"
    
    def test_response_validation_with_invalid_data(self):
        """Test that response validation catches invalid data formats"""
        invalid_responses = [
            # Missing required fields
            {"BTC": {"symbol": "BTC"}},  # Missing price and timestamp
            {"BTC": {"symbol": "BTC", "price": "invalid"}},  # Invalid price type
            {"BTC": {"symbol": "BTC", "price": 50000, "timestamp": "invalid"}},  # Invalid timestamp type
            # Non-dict response
            [],
            "invalid response",
            None
        ]
        
        for invalid_data in invalid_responses:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = invalid_data
            
            with patch.object(self.service.session, 'get', return_value=mock_response):
                with pytest.raises(MCPAPIError):
                    self.service.fetch_market_data(["BTC"])
    
    def test_network_error_handling(self):
        """Test handling of various network errors"""
        network_errors = [
            RequestException("Connection error"),
            requests.ConnectionError("Failed to connect"),
            requests.HTTPError("HTTP error occurred")
        ]
        
        for error in network_errors:
            with patch.object(self.service.session, 'get', side_effect=error):
                with pytest.raises(MCPAPIError) as exc_info:
                    self.service.fetch_market_data(["BTC"])
                
                # Should not retry on non-timeout network errors
                assert "failed after 1 attempts" in str(exc_info.value)
    
    def test_successful_request_no_retry(self):
        """Test that successful requests don't trigger retry logic"""
        mock_response_data = {
            "BTC": {
                "symbol": "BTC",
                "price": 50000.0,
                "timestamp": 1640995200000,
                "market_depth": {"bids": [], "asks": []},
                "volume_24h": 1000.0,
                "price_change_24h": 2.5
            }
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        
        with patch.object(self.service.session, 'get', return_value=mock_response) as mock_get:
            result = self.service.fetch_market_data(["BTC"])
            
            # Should only make one call for successful request
            assert mock_get.call_count == 1
            assert "BTC" in result