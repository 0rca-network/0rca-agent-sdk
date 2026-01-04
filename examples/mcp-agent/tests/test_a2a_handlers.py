"""
Tests for A2A (Agent-to-Agent) communication handlers.
Tests message validation, sending, receiving, and error handling.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from a2a_handlers import A2AHandlers
from config import A2AConfig
from orca_agent_sdk.core.a2a import A2AProtocol, AgentRegistry, AgentInfo


class TestA2AHandlers:
    """Test suite for A2A communication handlers"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = A2AConfig(
            agent_id="test-agent",
            registry_endpoint="http://test-registry",
            message_timeout=10
        )
        
        self.registry = AgentRegistry()
        self.protocol = A2AProtocol("test-agent", self.registry)
        self.handlers = A2AHandlers(self.protocol, self.config)
        
        # Register a test target agent
        self.registry.register(
            agent_id="target-agent",
            endpoint="http://target-agent:8000",
            capabilities=["test"],
            name="Test Target Agent"
        )
    
    def test_message_schema_validation_valid_message(self):
        """Test that valid A2A messages pass schema validation"""
        valid_message = {
            "header": {
                "message_id": "test-123",
                "from": "sender-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "ping",
                "payload": {"message": "hello"}
            }
        }
        
        assert self.handlers.validate_message_schema(valid_message) is True
    
    def test_message_schema_validation_missing_header(self):
        """Test that messages missing header fail validation"""
        invalid_message = {
            "task": {
                "action": "ping",
                "payload": {"message": "hello"}
            }
        }
        
        assert self.handlers.validate_message_schema(invalid_message) is False
    
    def test_message_schema_validation_missing_task(self):
        """Test that messages missing task fail validation"""
        invalid_message = {
            "header": {
                "message_id": "test-123",
                "from": "sender-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            }
        }
        
        assert self.handlers.validate_message_schema(invalid_message) is False
    
    def test_message_schema_validation_empty_action(self):
        """Test that messages with empty action fail validation"""
        invalid_message = {
            "header": {
                "message_id": "test-123",
                "from": "sender-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "",
                "payload": {"message": "hello"}
            }
        }
        
        assert self.handlers.validate_message_schema(invalid_message) is False
    
    def test_message_schema_validation_invalid_timestamp(self):
        """Test that messages with invalid timestamp fail validation"""
        invalid_message = {
            "header": {
                "message_id": "test-123",
                "from": "sender-agent",
                "to": "test-agent",
                "timestamp": "not-a-number"
            },
            "task": {
                "action": "ping",
                "payload": {"message": "hello"}
            }
        }
        
        assert self.handlers.validate_message_schema(invalid_message) is False
    
    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        """Test successful message sending"""
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.json.return_value = {"status": "received", "message_id": "response-123"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.handlers.send_message(
            to_agent_id="target-agent",
            action="ping",
            payload={"message": "test"}
        )
        
        assert result["status"] == "success"
        assert result["target_agent"] == "target-agent"
        assert result["action"] == "ping"
        assert "duration_ms" in result
        
        # Verify HTTP call was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "http://target-agent:8000/a2a/receive" in call_args[0][0]  # First positional argument is the URL
    
    def test_send_message_agent_not_found(self):
        """Test sending message to non-existent agent"""
        with pytest.raises(HTTPException) as exc_info:
            self.handlers.send_message(
                to_agent_id="nonexistent-agent",
                action="ping",
                payload={"message": "test"}
            )
        
        assert exc_info.value.status_code == 404
        assert "not found in registry" in str(exc_info.value.detail)
    
    @patch('requests.post')
    def test_send_message_network_error(self, mock_post):
        """Test handling of network errors during message sending"""
        # Mock network error
        mock_post.side_effect = Exception("Network error")
        
        with pytest.raises(HTTPException) as exc_info:
            self.handlers.send_message(
                to_agent_id="target-agent",
                action="ping",
                payload={"message": "test"}
            )
        
        assert exc_info.value.status_code == 503
        assert "Network communication failure" in str(exc_info.value.detail)
    
    def test_receive_message_valid_ping(self):
        """Test receiving a valid ping message"""
        message = {
            "header": {
                "message_id": "ping-123",
                "from": "sender-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "ping",
                "payload": {"message": "hello"}
            }
        }
        
        result = self.handlers.receive_message(message)
        
        assert result["status"] == "success"
        assert result["message_id"] == "ping-123"
        assert result["from_agent"] == "sender-agent"
        assert result["action"] == "ping"
        assert result["result"]["status"] == "pong"
    
    def test_receive_message_invalid_schema(self):
        """Test receiving message with invalid schema"""
        invalid_message = {
            "header": {
                "message_id": "test-123"
                # Missing required fields
            },
            "task": {
                "action": "ping"
                # Missing payload
            }
        }
        
        with pytest.raises(HTTPException) as exc_info:
            self.handlers.receive_message(invalid_message)
        
        assert exc_info.value.status_code == 400
        assert "Invalid A2A message schema" in str(exc_info.value.detail)
    
    def test_receive_message_market_data_query(self):
        """Test receiving a market data query message"""
        message = {
            "header": {
                "message_id": "query-123",
                "from": "client-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "query_market_data",
                "payload": {"symbols": ["BTC", "ETH"]}
            }
        }
        
        result = self.handlers.receive_message(message)
        
        assert result["status"] == "success"
        assert result["result"]["status"] == "market_data_available"
        assert result["result"]["payment_required"] is True
    
    def test_receive_message_notification(self):
        """Test receiving a notification message"""
        message = {
            "header": {
                "message_id": "notify-123",
                "from": "notifier-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "notify",
                "payload": {
                    "type": "alert",
                    "message": "System maintenance scheduled"
                }
            }
        }
        
        result = self.handlers.receive_message(message)
        
        assert result["status"] == "success"
        assert result["result"]["status"] == "notification_received"
        assert result["result"]["type"] == "alert"
        assert result["result"]["acknowledged"] is True
    
    def test_receive_message_status_request(self):
        """Test receiving a status request message"""
        message = {
            "header": {
                "message_id": "status-123",
                "from": "monitor-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "status",
                "payload": {}
            }
        }
        
        result = self.handlers.receive_message(message)
        
        assert result["status"] == "success"
        assert result["result"]["status"] == "online"
        assert result["result"]["agent_id"] == "test-agent"
        assert "capabilities" in result["result"]
        assert "version" in result["result"]
    
    def test_receive_message_unknown_action(self):
        """Test receiving message with unknown action"""
        message = {
            "header": {
                "message_id": "unknown-123",
                "from": "sender-agent",
                "to": "test-agent",
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": "unknown_action",
                "payload": {}
            }
        }
        
        result = self.handlers.receive_message(message)
        
        assert result["status"] == "success"
        assert result["result"]["status"] == "unknown_action"
        assert "supported_actions" in result["result"]
    
    def test_register_agent_success(self):
        """Test successful agent registration"""
        result = self.handlers.register_agent(
            agent_id="new-agent",
            endpoint="http://new-agent:8000",
            capabilities=["market_data", "notifications"],
            name="New Test Agent"
        )
        
        assert result["status"] == "registered"
        assert result["agent_id"] == "new-agent"
        assert result["endpoint"] == "http://new-agent:8000"
        assert result["capabilities"] == ["market_data", "notifications"]
        
        # Verify agent was actually registered
        registered_agent = self.registry.get_agent("new-agent")
        assert registered_agent is not None
        assert registered_agent.agent_id == "new-agent"
    
    def test_get_registered_agents(self):
        """Test getting list of registered agents"""
        # Register additional agent for testing
        self.handlers.register_agent(
            agent_id="another-agent",
            endpoint="http://another-agent:8000",
            capabilities=["test"],
            name="Another Agent"
        )
        
        result = self.handlers.get_registered_agents()
        
        assert result["status"] == "success"
        assert result["count"] >= 2  # target-agent + another-agent
        assert "agents" in result
        assert "target-agent" in result["agents"]
        assert "another-agent" in result["agents"]
        
        # Check agent details
        target_info = result["agents"]["target-agent"]
        assert target_info["endpoint"] == "http://target-agent:8000"
        assert target_info["capabilities"] == ["test"]


# Property-based tests using hypothesis
from hypothesis import given, strategies as st

class TestA2AMessageValidationProperty:
    """Property-based tests for A2A message validation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.config = A2AConfig(agent_id="test-agent")
        self.registry = AgentRegistry()
        self.protocol = A2AProtocol("test-agent", self.registry)
        self.handlers = A2AHandlers(self.protocol, self.config)
    
    @given(
        message_id=st.text(min_size=1),
        from_agent=st.text(min_size=1),
        to_agent=st.text(min_size=1),
        timestamp=st.integers(min_value=1),
        action=st.text(min_size=1),
        payload=st.dictionaries(st.text(), st.text())
    )
    def test_a2a_message_validation_and_processing_property(
        self, message_id, from_agent, to_agent, timestamp, action, payload
    ):
        """
        **Feature: mcp-market-data-agent, Property 5: A2A message validation and processing**
        **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**
        
        For any A2A message sent to /a2a/send or /a2a/receive, the system should validate 
        the JSON schema before processing and return appropriate HTTP status codes 
        (200 for success, 400 for validation errors)
        """
        # Create a properly structured message
        message = {
            "header": {
                "message_id": message_id,
                "from": from_agent,
                "to": to_agent,
                "timestamp": timestamp
            },
            "task": {
                "action": action,
                "payload": payload
            }
        }
        
        # Test schema validation
        is_valid = self.handlers.validate_message_schema(message)
        
        # If message is valid, receiving should succeed
        if is_valid:
            try:
                result = self.handlers.receive_message(message)
                # Should return success status
                assert result["status"] == "success"
                assert "message_id" in result
                assert "from_agent" in result
                assert "action" in result
            except HTTPException as e:
                # Should not raise validation errors for valid messages
                assert e.status_code != 400, f"Valid message should not cause validation error: {message}"
        else:
            # Invalid messages should raise validation errors
            with pytest.raises(HTTPException) as exc_info:
                self.handlers.receive_message(message)
            assert exc_info.value.status_code == 400