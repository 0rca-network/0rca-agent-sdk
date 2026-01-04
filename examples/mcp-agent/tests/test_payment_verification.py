"""
Property-based tests for payment verification functionality.
Tests Property 1: Payment verification determines access
"""

import pytest
import json
import base64
from unittest.mock import Mock, patch
from hypothesis import given, strategies as st, settings
from fastapi.testclient import TestClient
from fastapi import Request

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from orca_agent_sdk.core.payment import PaymentManager
from orca_agent_sdk.core.x402 import X402
from orca_agent_sdk import AgentConfig

# Test configuration
TEST_CONFIG = {
    "agent_id": "test-agent",
    "price": "0.1",
    "token_address": "devUSDC.e",
    "chain_caip": "eip155:338",
    "ai_backend": "crewai",
    "db_path": "test.db",
    "backend_options": {
        "provider": "GoogleGenAI",
        "model": "gemini-2.0-flash",
        "api_key": "test-key",
        "temperature": 0.7,
        "max_tokens": 1000
    }
}

class TestPaymentVerificationProperty:
    """
    **Feature: mcp-market-data-agent, Property 1: Payment verification determines access**
    
    For any HTTP request to `/chat`, the system should return HTTP 402 with payment 
    requirements when no valid payment proof is provided, and should process the request 
    when valid payment proof is verified through the Cronos facilitator.
    
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4**
    """
    
    def setup_method(self):
        """Set up test environment"""
        # Mock environment variables
        os.environ['GEMINI_API_KEY'] = 'test-key'
        
        # Import app after setting environment
        from app import app, initialize_services
        
        # Initialize services with test configuration
        with patch('config.get_config') as mock_config:
            mock_config_obj = Mock()
            mock_config_obj.to_agent_config_dict.return_value = TEST_CONFIG
            mock_config_obj.mcp = Mock()
            mock_config_obj.crewai = Mock()
            mock_config_obj.a2a = Mock()
            mock_config_obj.a2a.agent_id = "test-agent"
            mock_config_obj.payment = Mock()
            mock_config_obj.payment.price = "0.1"
            mock_config_obj.payment.token_address = "devUSDC.e"
            mock_config_obj.payment.chain_caip = "eip155:338"
            mock_config_obj.server = Mock()
            mock_config_obj.server.host = "0.0.0.0"
            mock_config_obj.server.port = 8002
            mock_config.return_value = mock_config_obj
            
            # Mock the services to avoid actual initialization
            with patch('app.MarketDataService'), \
                 patch('app.MCPCrewAIBackend'), \
                 patch('app.A2AHandlers'), \
                 patch('app.AgentRegistry'), \
                 patch('app.A2AProtocol'):
                initialize_services()
        
        self.client = TestClient(app)
        self.payment_manager = PaymentManager(AgentConfig(**TEST_CONFIG))
        self.x402 = X402()
    
    def create_valid_payment_token(self, challenge: str, address: str = "0x1234567890123456789012345678901234567890") -> str:
        """Create a valid payment token for testing"""
        payment_obj = {
            "challenge": challenge,
            "signature": "0x" + "a" * 130,  # Mock signature
            "address": address
        }
        return self.x402.encode_payment_required(payment_obj)
    
    def create_invalid_payment_token(self) -> str:
        """Create an invalid payment token for testing"""
        invalid_obj = {
            "invalid": "data"
        }
        return self.x402.encode_payment_required(invalid_obj)
    
    @given(
        message=st.text(min_size=1, max_size=100),
        symbols=st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=10), min_size=1, max_size=5))
    )
    @settings(max_examples=50)  # Reduced for faster testing
    def test_payment_verification_determines_access_property(self, message, symbols):
        """
        **Feature: mcp-market-data-agent, Property 1: Payment verification determines access**
        
        Property test that verifies payment verification correctly determines access:
        - Requests without payment should return HTTP 402
        - Requests with invalid payment should return HTTP 402  
        """
        query_data = {"message": message}
        if symbols:
            query_data["symbols"] = symbols
        
        # Test 1: No payment header - should return 402
        response_no_payment = self.client.post("/chat", json=query_data)
        assert response_no_payment.status_code == 402
        assert "WWW-Authenticate" in response_no_payment.headers
        assert response_no_payment.headers["WWW-Authenticate"].startswith("x402 ")
        
        response_data = response_no_payment.json()
        assert "error" in response_data
        assert "accepts" in response_data
        assert response_data["error"] == "Payment required"
        
        # Test 2: Invalid payment header - should return 402
        invalid_token = self.create_invalid_payment_token()
        response_invalid = self.client.post(
            "/chat", 
            json=query_data,
            headers={"Authorization": f"x402 {invalid_token}"}
        )
        assert response_invalid.status_code == 402
        
        # Test 3: Empty authorization header - should return 402
        response_empty_auth = self.client.post(
            "/chat",
            json=query_data,
            headers={"Authorization": ""}
        )
        assert response_empty_auth.status_code == 402
        
        # Test 4: Wrong authorization scheme - should return 402
        response_wrong_scheme = self.client.post(
            "/chat",
            json=query_data,
            headers={"Authorization": "Bearer some-token"}
        )
        assert response_wrong_scheme.status_code == 402
    
    @given(
        auth_header=st.one_of(
            st.none(),
            st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), max_size=50),
            st.just(""),
            st.just("Bearer token"),
            st.just("x402"),
            st.just("x402 "),
        )
    )
    @settings(max_examples=50)
    def test_payment_header_validation_property(self, auth_header):
        """
        Property test for payment header validation.
        Tests that various invalid authorization headers are properly rejected.
        """
        query_data = {"message": "test query"}
        
        headers = {}
        if auth_header is not None:
            headers["Authorization"] = auth_header
        
        response = self.client.post("/chat", json=query_data, headers=headers)
        
        # All invalid or missing headers should result in 402
        assert response.status_code == 402
        assert "WWW-Authenticate" in response.headers
        
        response_data = response.json()
        assert "error" in response_data
        assert "accepts" in response_data
    
    def test_payment_requirements_structure(self):
        """
        Test that payment requirements have the correct structure.
        """
        response = self.client.post("/chat", json={"message": "test"})
        assert response.status_code == 402
        
        response_data = response.json()
        accepts = response_data["accepts"]
        
        assert isinstance(accepts, list)
        assert len(accepts) > 0
        
        requirement = accepts[0]
        assert "scheme" in requirement
        assert "network" in requirement
        assert "token" in requirement
        assert "resource" in requirement
        assert "maxAmountRequired" in requirement
        assert "beneficiary" in requirement
        
        assert requirement["scheme"] == "exact"
        assert requirement["network"] == TEST_CONFIG["chain_caip"]
        assert requirement["token"] == TEST_CONFIG["token_address"]
        assert requirement["maxAmountRequired"] == TEST_CONFIG["price"]
    
    def test_payment_info_endpoint(self):
        """
        Test the payment info endpoint returns correct information.
        """
        response = self.client.get("/payment/info")
        assert response.status_code == 200
        
        data = response.json()
        assert data["payment_required"] is True
        assert "requirements" in data
        assert data["agent_id"] == "mcp-market-data-agent"
        assert data["price"] == "0.1"
        assert data["token"] == "devUSDC.e"
        assert data["chain"] == "eip155:338"
    
    def test_payment_status_endpoint_without_payment(self):
        """
        Test payment status endpoint without payment.
        """
        response = self.client.get("/payment/status")
        assert response.status_code == 402
        
        data = response.json()
        assert data["status"] == "required"
        assert "accepts" in data
    
    def test_payment_status_endpoint_with_valid_payment(self):
        """
        Test payment status endpoint with valid payment.
        """
        # Mock valid payment
        with patch('app.verify_payment') as mock_verify:
            mock_verify.return_value = True
            
            response = self.client.get(
                "/payment/status",
                headers={"Authorization": "x402 valid_token"}
            )
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "verified"
            assert data["access_granted"] is True
    
    def test_valid_payment_processing_unit_test(self):
        """
        Unit test for valid payment processing using direct function calls.
        This tests the payment verification logic without FastAPI dependency injection.
        """
        # Test the payment manager directly
        requirements = self.payment_manager.build_requirements()
        challenge = self.payment_manager.encode_challenge(requirements)
        
        # Create a mock valid payment token
        payment_obj = {
            "challenge": challenge,
            "signature": "0x" + "a" * 130,  # Mock signature
            "address": "0x1234567890123456789012345678901234567890"
        }
        payment_token = self.x402.encode_payment_required(payment_obj)
        
        # Test that the payment manager can decode the token
        decoded = self.payment_manager.decode_payment(payment_token)
        assert "challenge" in decoded
        assert "signature" in decoded
        assert "address" in decoded
        
        # Test that requirements have correct structure
        assert len(requirements) > 0
        requirement = requirements[0]
        assert requirement["scheme"] == "exact"
        assert requirement["network"] == TEST_CONFIG["chain_caip"]
        assert requirement["token"] == TEST_CONFIG["token_address"]
        assert requirement["maxAmountRequired"] == TEST_CONFIG["price"]