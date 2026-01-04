"""
Property-based tests for CrewAI backend functionality.
Tests the natural language processing and response generation capabilities.
"""

import pytest
from hypothesis import given, strategies as st, settings
from hypothesis import assume
import re
from typing import Dict

# Import the modules to test
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crewai_backend import MCPCrewAIBackend
from market_data import MarketDataResponse
from config import CrewAIConfig


class TestCrewAIResponseGeneration:
    """Property-based tests for CrewAI response generation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        # Create config without API key to use fallback implementation
        self.config = CrewAIConfig()
        self.config.api_key = None  # Force fallback mode for consistent testing
        self.backend = MCPCrewAIBackend(self.config)
    
    @given(
        symbols=st.lists(
            st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
                min_size=3,
                max_size=6
            ).filter(lambda x: x.isalnum()),
            min_size=1,
            max_size=5,
            unique=True
        ),
        prices=st.lists(
            st.floats(min_value=0.01, max_value=1000000.0, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        ),
        price_changes=st.lists(
            st.floats(min_value=-99.99, max_value=999.99, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        ),
        volumes=st.lists(
            st.floats(min_value=0.0, max_value=1e12, allow_nan=False, allow_infinity=False),
            min_size=1,
            max_size=5
        ),
        user_queries=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100, deadline=5000)
    def test_crewai_response_generation_property(self, symbols, prices, price_changes, volumes, user_queries):
        """
        **Feature: mcp-market-data-agent, Property 4: CrewAI response generation**
        
        For any valid market data input, the CrewAI backend should generate a natural language 
        response that includes relevant market metrics and organizes multi-asset information 
        clearly by asset.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        # Ensure we have matching lengths for all data
        min_length = min(len(symbols), len(prices), len(price_changes), len(volumes))
        assume(min_length > 0)
        
        symbols = symbols[:min_length]
        prices = prices[:min_length]
        price_changes = price_changes[:min_length]
        volumes = volumes[:min_length]
        
        # Create market data responses
        market_data = {}
        for i in range(min_length):
            market_data[symbols[i]] = MarketDataResponse(
                symbol=symbols[i],
                price=prices[i],
                timestamp=1704067200000,  # Fixed timestamp for consistency
                market_depth={"bids": [], "asks": []},
                volume_24h=volumes[i],
                price_change_24h=price_changes[i]
            )
        
        # Generate response using CrewAI backend
        response = self.backend.process_market_data(market_data, user_queries)
        
        # Property 1: Response should be a non-empty string
        assert isinstance(response, str), "Response must be a string"
        assert len(response.strip()) > 0, "Response must not be empty"
        
        # Property 2: Response should include relevant market metrics
        # For single asset, should include price and change information
        if len(symbols) == 1:
            symbol = symbols[0]
            price = prices[0]
            change = price_changes[0]
            
            # Should contain the symbol name
            assert symbol in response, f"Response should contain symbol {symbol}"
            
            # Should contain price information (formatted price or raw price)
            price_found = (
                f"${price:,.2f}" in response or 
                f"{price:,.2f}" in response or
                str(int(price)) in response
            )
            assert price_found, f"Response should contain price information for {symbol}"
            
            # Should contain change information (percentage or direction)
            change_found = (
                f"{change:+.2f}%" in response or
                f"{abs(change):.2f}%" in response or
                ("up" in response.lower() and change >= 0) or
                ("down" in response.lower() and change < 0) or
                "📈" in response or "📉" in response
            )
            assert change_found, f"Response should contain change information for {symbol}"
        
        # Property 3: For multi-asset data, should organize information clearly by asset
        if len(symbols) > 1:
            # Should mention multiple symbols or indicate multi-asset nature
            symbols_mentioned = sum(1 for symbol in symbols if symbol in response)
            multi_asset_indicators = [
                "assets" in response.lower(),
                "symbols" in response.lower(),
                "summary" in response.lower(),
                len(symbols) > 1 and symbols_mentioned >= 2
            ]
            
            assert any(multi_asset_indicators), "Multi-asset response should organize information by asset"
            
            # Should contain at least some of the symbols
            assert symbols_mentioned > 0, "Multi-asset response should mention at least one symbol"
        
        # Property 4: Response should be structured and readable
        # Should not be just raw data dump
        assert not response.startswith("{"), "Response should be natural language, not raw JSON"
        assert not response.startswith("["), "Response should be natural language, not raw array"
        
        # Should contain some natural language elements
        natural_language_indicators = [
            any(word in response.lower() for word in ["price", "trading", "market", "current"]),
            any(char in response for char in [".", "!", "?"]),  # Sentence punctuation
            len(response.split()) > 3  # More than just raw data
        ]
        assert any(natural_language_indicators), "Response should contain natural language elements"
    
    @given(
        raw_data=st.dictionaries(
            keys=st.text(
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
                min_size=3,
                max_size=6
            ).filter(lambda x: x.isalnum()),
            values=st.fixed_dictionaries({
                "symbol": st.text(min_size=3, max_size=6),
                "price": st.floats(min_value=0.01, max_value=1000000.0, allow_nan=False, allow_infinity=False),
                "price_change_24h": st.floats(min_value=-99.99, max_value=999.99, allow_nan=False, allow_infinity=False)
            }),
            min_size=1,
            max_size=3
        ),
        context=st.text(min_size=0, max_size=100)
    )
    @settings(max_examples=50, deadline=3000)
    def test_summary_generation_property(self, raw_data, context):
        """
        Property test for summary generation functionality.
        
        For any raw market data, the system should generate a structured summary
        that includes market analysis and key insights.
        """
        # Generate summary
        summary = self.backend.generate_summary(raw_data, context)
        
        # Property 1: Summary should be a non-empty string
        assert isinstance(summary, str), "Summary must be a string"
        assert len(summary.strip()) > 0, "Summary must not be empty"
        
        # Property 2: Summary should contain market-related content
        market_keywords = ["market", "summary", "price", "change", "asset", "symbol"]
        has_market_content = any(keyword in summary.lower() for keyword in market_keywords)
        assert has_market_content, "Summary should contain market-related content"
        
        # Property 3: If context is provided, it should be relevant to the summary
        if context and len(context.strip()) > 0:
            # Context should either be mentioned or the summary should be contextually relevant
            context_relevant = (
                context.lower() in summary.lower() or
                "context" in summary.lower() or
                len(summary) > len(context)  # Summary should add value beyond just context
            )
            assert context_relevant, "Summary should be relevant to provided context"
        
        # Property 4: Summary should be structured (not just raw data)
        assert not summary.startswith("{"), "Summary should be formatted text, not raw JSON"
        assert not summary.startswith("["), "Summary should be formatted text, not raw array"
    
    def test_error_handling_consistency(self):
        """
        Test that error handling provides consistent and helpful responses.
        """
        # Test with various error types
        test_errors = [
            Exception("Network timeout"),
            ValueError("Invalid data format"),
            KeyError("Missing required field"),
            RuntimeError("Processing failed")
        ]
        
        sample_market_data = {
            "BTC": MarketDataResponse(
                symbol="BTC",
                price=45000.0,
                timestamp=1704067200000,
                market_depth={},
                volume_24h=1000000.0,
                price_change_24h=2.5
            )
        }
        
        for error in test_errors:
            error_response = self.backend.handle_processing_errors(error, sample_market_data)
            
            # Error response should be informative
            assert isinstance(error_response, str), "Error response must be a string"
            assert len(error_response) > 0, "Error response must not be empty"
            
            # Should indicate that AI processing is unavailable
            assert "unavailable" in error_response.lower(), "Should indicate AI processing unavailable"
            
            # Should include fallback market data when provided
            assert "BTC" in error_response, "Should include fallback market data"
            assert "45000" in error_response or "45,000" in error_response, "Should include price data"
    
    def test_empty_data_handling(self):
        """
        Test handling of empty or minimal data inputs.
        """
        # Test with empty market data
        empty_response = self.backend.process_market_data({}, "test query")
        assert isinstance(empty_response, str)
        assert len(empty_response) > 0
        assert "no market data" in empty_response.lower() or "unavailable" in empty_response.lower()
        
        # Test with empty raw data for summary
        empty_summary = self.backend.generate_summary({}, "test context")
        assert isinstance(empty_summary, str)
        assert len(empty_summary) > 0