"""
Property-based tests for comprehensive error logging functionality.
Tests Property 7: Comprehensive error logging
"""

import pytest
import json
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from requests.exceptions import Timeout, RequestException

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from logging_config import get_logger, MCPLogger
from market_data import MCPAPIError, MarketDataService
from crewai_backend import MCPCrewAIBackend
from a2a_handlers import A2AHandlers

class TestErrorLoggingProperty:
    """
    **Feature: mcp-market-data-agent, Property 7: Comprehensive error logging**
    
    For any system error (payment failures, API failures, A2A failures), the system 
    should log the error with appropriate severity level and relevant context details.
    
    **Validates: Requirements 6.1, 6.2, 6.3, 6.4**
    """
    
    def setup_method(self):
        """Set up test environment with temporary log file"""
        self.temp_log_file = tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.log')
        self.temp_log_file.close()
        self.log_file_path = self.temp_log_file.name
        
        # Create logger instance for testing
        self.logger = get_logger("test_logger", "DEBUG", self.log_file_path)
        
        # Mock configurations
        self.mock_mcp_config = Mock()
        self.mock_mcp_config.api_endpoint = "https://test-api.example.com"
        self.mock_mcp_config.timeout_seconds = 5
        self.mock_mcp_config.retry_attempts = 1
        self.mock_mcp_config.api_key = "test-key"
        
        self.mock_crewai_config = Mock()
        self.mock_crewai_config.model = "test-model"
        self.mock_crewai_config.temperature = 0.7
        self.mock_crewai_config.api_key = "test-key"
        self.mock_crewai_config.processing_timeout = 30
        
        self.mock_a2a_config = Mock()
        self.mock_a2a_config.agent_id = "test-agent"
    
    def teardown_method(self):
        """Clean up temporary log file"""
        try:
            os.unlink(self.log_file_path)
        except:
            pass
    
    def read_log_entries(self):
        """Read and parse log entries from the log file"""
        log_entries = []
        try:
            with open(self.log_file_path, 'r') as f:
                for line in f:
                    if line.strip():
                        try:
                            log_entries.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except FileNotFoundError:
            pass
        return log_entries
    
    @given(
        error_message=st.text(min_size=1, max_size=100),
        error_type=st.sampled_from(['ValueError', 'RuntimeError', 'ConnectionError', 'TimeoutError']),
        context_data=st.dictionaries(
            st.text(min_size=1, max_size=20), 
            st.one_of(st.text(max_size=50), st.integers(), st.booleans()),
            min_size=0, max_size=5
        )
    )
    @settings(max_examples=20)
    def test_error_logging_with_context_property(self, error_message, error_type, context_data):
        """
        **Feature: mcp-market-data-agent, Property 7: Comprehensive error logging**
        
        Property test that verifies all errors are logged with appropriate context.
        For any error with context, the log should contain:
        - Error message and type
        - Context information
        - Appropriate severity level
        - Timestamp
        """
        # Create an exception of the specified type
        try:
            exception_class = getattr(__builtins__, error_type)
        except (AttributeError, TypeError):
            exception_class = Exception
        
        test_error = exception_class(error_message)
        
        # Log the error with context
        self.logger.log_error(test_error, context_data, "ERROR")
        
        # Read log entries
        log_entries = self.read_log_entries()
        
        # Verify at least one log entry was created
        assert len(log_entries) > 0
        
        # Find the error log entry
        error_entry = None
        for entry in log_entries:
            if entry.get("level") == "ERROR" and error_message in entry.get("message", ""):
                error_entry = entry
                break
        
        assert error_entry is not None, f"Error log entry not found for message: {error_message}"
        
        # Verify required fields are present
        assert "timestamp" in error_entry
        assert "level" in error_entry
        assert "message" in error_entry
        assert "context" in error_entry
        
        # Verify error details in context
        context = error_entry["context"]
        assert context["event_type"] == "error"
        # Use the actual error type from the exception
        assert context["error_type"] == type(test_error).__name__
        assert context["error_message"] == error_message
        
        # Verify provided context is included
        if context_data:
            assert "context" in context
            for key, value in context_data.items():
                assert key in context["context"]
                assert context["context"][key] == value
    
    @given(
        payment_success=st.booleans(),
        token_present=st.booleans(),
        error_reason=st.one_of(
            st.none(),
            st.sampled_from([
                "missing_authorization_header",
                "empty_payment_token", 
                "signature_verification_failed",
                "token_decode_error"
            ])
        )
    )
    @settings(max_examples=20)
    def test_payment_verification_logging_property(self, payment_success, token_present, error_reason):
        """
        Property test for payment verification logging.
        Verifies that payment verification attempts are logged with appropriate context.
        """
        payment_details = {
            "token_present": token_present,
            "method": "local_signature"
        }
        
        error_details = None
        if not payment_success and error_reason:
            error_details = {
                "reason": error_reason,
                "verification_time_ms": 100
            }
        
        # Log payment verification
        self.logger.log_payment_verification(payment_success, payment_details, error_details)
        
        # Read log entries
        log_entries = self.read_log_entries()
        assert len(log_entries) > 0
        
        # Find the payment log entry
        payment_entry = None
        for entry in log_entries:
            if "payment_context" in entry and entry["payment_context"]["event_type"] == "payment_verification":
                payment_entry = entry
                break
        
        assert payment_entry is not None
        
        # Verify payment context
        payment_context = payment_entry["payment_context"]
        assert payment_context["success"] == payment_success
        assert payment_context["payment_token_present"] == token_present
        assert payment_context["verification_method"] == "local_signature"
        
        if error_details:
            assert "error_details" in payment_context
            assert payment_context["error_details"]["reason"] == error_reason
    
    @given(
        api_success=st.booleans(),
        endpoint=st.text(min_size=10, max_size=50),
        symbols=st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=3)),
        status_code=st.one_of(st.none(), st.integers(min_value=200, max_value=599)),
        error_type=st.sampled_from(['Timeout', 'MCPAPIError', 'RequestException', 'UnexpectedError'])
    )
    @settings(max_examples=20)
    def test_api_request_logging_property(self, api_success, endpoint, symbols, status_code, error_type):
        """
        Property test for API request logging.
        Verifies that API requests are logged with comprehensive context.
        """
        request_details = {
            "endpoint": endpoint,
            "method": "GET",
            "symbols": symbols,
            "attempt": 1
        }
        
        response_details = None
        error_details = None
        
        if api_success:
            response_details = {
                "status_code": status_code or 200,
                "response_time_ms": 150,
                "data_count": len(symbols) if symbols else 1
            }
        else:
            error_details = {
                "type": error_type,
                "message": f"Test {error_type} error",
                "status_code": status_code
            }
        
        # Log API request
        self.logger.log_api_request(api_success, request_details, response_details, error_details)
        
        # Read log entries
        log_entries = self.read_log_entries()
        assert len(log_entries) > 0
        
        # Find the API log entry
        api_entry = None
        for entry in log_entries:
            if "api_context" in entry and entry["api_context"]["event_type"] == "api_request":
                api_entry = entry
                break
        
        assert api_entry is not None
        
        # Verify API context
        api_context = api_entry["api_context"]
        assert api_context["success"] == api_success
        assert api_context["endpoint"] == endpoint
        assert api_context["method"] == "GET"
        assert api_context["symbols"] == symbols
        
        if response_details:
            assert "response" in api_context
            assert api_context["response"]["status_code"] == response_details["status_code"]
        
        if error_details:
            assert "error" in api_context
            assert api_context["error"]["type"] == error_type
    
    @given(
        a2a_success=st.booleans(),
        direction=st.sampled_from(['send', 'receive']),
        action=st.sampled_from(['ping', 'query_market_data', 'notify', 'status']),
        from_agent=st.text(min_size=5, max_size=20),
        to_agent=st.text(min_size=5, max_size=20),
        error_type=st.sampled_from(['validation_error', 'communication_error', 'processing_error'])
    )
    @settings(max_examples=20)
    def test_a2a_communication_logging_property(self, a2a_success, direction, action, from_agent, to_agent, error_type):
        """
        Property test for A2A communication logging.
        Verifies that A2A communication events are logged with message context.
        """
        message_details = {
            "direction": direction,
            "action": action,
            "from_agent": from_agent,
            "to_agent": to_agent,
            "message_id": f"msg_{int(time.time())}"
        }
        
        error_details = None
        if not a2a_success:
            error_details = {
                "type": error_type,
                "message": f"Test {error_type}",
                "validation_errors": ["test_error"] if error_type == "validation_error" else None
            }
        
        # Log A2A communication
        self.logger.log_a2a_communication(a2a_success, message_details, error_details)
        
        # Read log entries
        log_entries = self.read_log_entries()
        assert len(log_entries) > 0
        
        # Find the A2A log entry
        a2a_entry = None
        for entry in log_entries:
            if "a2a_context" in entry and entry["a2a_context"]["event_type"] == "a2a_communication":
                a2a_entry = entry
                break
        
        assert a2a_entry is not None
        
        # Verify A2A context
        a2a_context = a2a_entry["a2a_context"]
        assert a2a_context["success"] == a2a_success
        assert a2a_context["direction"] == direction
        assert a2a_context["action"] == action
        assert a2a_context["from_agent"] == from_agent
        assert a2a_context["to_agent"] == to_agent
        
        if error_details:
            assert "error" in a2a_context
            assert a2a_context["error"]["type"] == error_type
    
    @given(
        service_name=st.text(min_size=5, max_size=30),
        success=st.booleans(),
        details=st.one_of(
            st.none(),
            st.dictionaries(
                st.text(min_size=1, max_size=15),
                st.one_of(st.text(max_size=30), st.integers(), st.booleans()),
                min_size=1, max_size=3
            )
        )
    )
    @settings(max_examples=20)
    def test_service_initialization_logging_property(self, service_name, success, details):
        """
        Property test for service initialization logging.
        Verifies that service initialization events are properly logged.
        """
        error = None if success else Exception("Test initialization error")
        
        # Log service initialization
        self.logger.log_service_initialization(service_name, success, details, error)
        
        # Read log entries
        log_entries = self.read_log_entries()
        assert len(log_entries) > 0
        
        # Find the service initialization log entry
        init_entry = None
        for entry in log_entries:
            if ("context" in entry and 
                entry["context"].get("event_type") == "service_initialization" and
                entry["context"].get("service") == service_name):
                init_entry = entry
                break
        
        assert init_entry is not None
        
        # Verify initialization context
        context = init_entry["context"]
        assert context["service"] == service_name
        assert context["success"] == success
        
        if details:
            assert "details" in context
            for key, value in details.items():
                assert context["details"][key] == value
        
        if not success:
            assert "error" in context
    
    def test_market_data_service_error_logging_integration(self):
        """
        Integration test for MarketDataService error logging.
        Tests that the service properly logs errors through the logging system.
        """
        # Create MarketDataService with mocked logger
        with patch('market_data.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            service = MarketDataService(self.mock_mcp_config)
            
            # Test API error logging
            with patch.object(service.session, 'get') as mock_get:
                mock_response = Mock()
                mock_response.status_code = 500
                mock_response.json.return_value = {"error": "Server error"}
                mock_response.text = "Internal server error"
                mock_response.url = "https://test-api.example.com"
                mock_response.headers = {"Content-Type": "application/json"}
                mock_get.return_value = mock_response
                
                # This should trigger error logging
                with pytest.raises(MCPAPIError):
                    service.fetch_market_data(["BTC"])
                
                # Verify error logging was called
                mock_logger.log_error.assert_called()
    
    def test_crewai_backend_error_logging_integration(self):
        """
        Integration test for CrewAI backend error logging.
        Tests that the backend properly logs processing errors.
        """
        with patch('crewai_backend.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Create backend without AI model (will use fallback)
            with patch('crewai_backend.GENAI_AVAILABLE', False):
                backend = MCPCrewAIBackend(self.mock_crewai_config)
            
            # Test error handling
            test_error = Exception("Test processing error")
            result = backend.handle_processing_errors(test_error, None)
            
            # Verify error was logged
            mock_logger.log_error.assert_called_once()
            args, kwargs = mock_logger.log_error.call_args
            assert args[0] == test_error
            assert "operation" in args[1]
    
    def test_a2a_handlers_error_logging_integration(self):
        """
        Integration test for A2A handlers error logging.
        Tests that handlers properly log communication errors.
        """
        with patch('a2a_handlers.get_logger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            
            # Create mock protocol and registry
            mock_protocol = Mock()
            mock_registry = Mock()
            mock_protocol.registry = mock_registry
            
            handlers = A2AHandlers(mock_protocol, self.mock_a2a_config)
            
            # Test validation error logging
            invalid_message = {"invalid": "message"}
            
            with pytest.raises(Exception):  # Should raise HTTPException
                handlers.receive_message(invalid_message)
            
            # Verify error logging was called
            mock_logger.log_a2a_communication.assert_called()
            args, kwargs = mock_logger.log_a2a_communication.call_args
            assert args[0] == False  # success = False
            assert "error_details" in kwargs or len(args) > 2
    
    @given(
        operation=st.text(min_size=5, max_size=30),
        duration_ms=st.integers(min_value=1, max_value=10000)
    )
    @settings(max_examples=10)
    def test_performance_logging_property(self, operation, duration_ms):
        """
        Property test for performance logging.
        Verifies that performance metrics are logged with appropriate severity.
        """
        details = {"test_detail": "value"}
        
        # Log performance metric
        self.logger.log_processing_performance(operation, duration_ms, details)
        
        # Read log entries
        log_entries = self.read_log_entries()
        assert len(log_entries) > 0
        
        # Find the performance log entry
        perf_entry = None
        for entry in log_entries:
            if ("context" in entry and 
                entry["context"].get("event_type") == "performance_metric" and
                entry["context"].get("operation") == operation):
                perf_entry = entry
                break
        
        assert perf_entry is not None
        
        # Verify performance context
        context = perf_entry["context"]
        assert context["operation"] == operation
        assert context["duration_ms"] == duration_ms
        assert "details" in context
        
        # Verify appropriate log level based on duration
        if duration_ms > 5000:
            assert perf_entry["level"] == "WARNING"
        else:
            assert perf_entry["level"] == "INFO"