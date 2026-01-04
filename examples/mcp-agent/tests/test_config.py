"""
Property-based tests for configuration validation.
Tests SDK integration consistency and configuration validation.
"""

import pytest
import os
import tempfile
from hypothesis import given, strategies as st, settings, HealthCheck
from unittest.mock import patch

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import from the parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    AgentConfiguration, MCPConfig, PaymentConfig, 
    CrewAIConfig, A2AConfig, ServerConfig
)
from orca_agent_sdk.config import AgentConfig

class TestConfigurationValidation:
    """Test configuration validation and SDK integration"""
    
    @given(
        agent_id=st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=32, max_codepoint=126)).filter(lambda x: x.strip() and x.replace('-', '').replace('_', '').isalnum()),
        price=st.decimals(min_value=0, max_value=100, places=2).map(str),
        token_address=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=32, max_codepoint=126)).filter(lambda x: x.strip()),
        chain_caip=st.text(min_size=5, max_size=20, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=32, max_codepoint=126)).map(lambda x: f"eip155:{x}"),
        api_key=st.text(min_size=10, max_size=50, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'), min_codepoint=32, max_codepoint=126))
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
    def test_sdk_integration_consistency(self, agent_id, price, token_address, chain_caip, api_key):
        """
        **Feature: mcp-market-data-agent, Property 6: SDK integration consistency**
        For any valid configuration parameters, the system should use 0rca-agent-sdk 
        methods for payment verification and data persistence rather than custom implementations.
        **Validates: Requirements 5.2, 5.3**
        """
        # Set up environment variables for the test
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': api_key,
            'MCP_API_KEY': 'test_mcp_key',
            'CRONOS_FACILITATOR_URL': 'https://test-facilitator.com',
            'AGENT_REGISTRY_ENDPOINT': 'https://test-registry.com'
        }):
            # Create configuration with test parameters
            config = AgentConfiguration()
            config.a2a.agent_id = agent_id
            config.payment.price = price
            config.payment.token_address = token_address
            config.payment.chain_caip = chain_caip
            config.crewai.api_key = api_key
            
            # Convert to AgentConfig format
            config_dict = config.to_agent_config_dict()
            
            # Verify SDK integration consistency
            # The configuration should be compatible with AgentConfig
            try:
                agent_config = AgentConfig(**config_dict)
                
                # Verify that essential SDK fields are properly mapped
                assert agent_config.agent_id == agent_id
                assert agent_config.price == price
                assert agent_config.token_address == token_address
                assert agent_config.chain_caip == chain_caip
                assert agent_config.ai_backend == "crewai"
                
                # Verify backend options are properly configured
                assert "provider" in agent_config.backend_options
                assert "model" in agent_config.backend_options
                assert "api_key" in agent_config.backend_options
                assert agent_config.backend_options["api_key"] == api_key
                
                # Verify database path follows SDK conventions
                assert agent_config.db_path == f"{agent_id}.db"
                
            except Exception as e:
                pytest.fail(f"SDK integration failed with valid configuration: {e}")
    
    def test_configuration_validation_with_missing_api_key(self):
        """Test that configuration validation fails when required API key is missing"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                AgentConfiguration()
            
            assert "GEMINI_API_KEY environment variable is required" in str(exc_info.value)
    
    def test_configuration_validation_with_invalid_chain_caip(self):
        """Test that configuration validation handles invalid chain CAIP format"""
        with patch.dict(os.environ, {'GEMINI_API_KEY': 'test_key'}):
            config = AgentConfiguration()
            config.payment.chain_caip = ""  # Invalid empty chain CAIP
            
            with pytest.raises(ValueError):
                config._validate_config()
    
    def test_mcp_headers_generation(self):
        """Test that MCP API headers are properly generated"""
        with patch.dict(os.environ, {
            'GEMINI_API_KEY': 'test_gemini_key',
            'MCP_API_KEY': 'test_mcp_key'
        }):
            config = AgentConfiguration()
            headers = config.get_mcp_headers()
            
            assert "Content-Type" in headers
            assert headers["Content-Type"] == "application/json"
            assert "User-Agent" in headers
            assert config.a2a.agent_id in headers["User-Agent"]
            assert "Authorization" in headers
            assert headers["Authorization"] == "Bearer test_mcp_key"
    
    def test_environment_variable_override(self):
        """Test that environment variables properly override default values"""
        test_env = {
            'GEMINI_API_KEY': 'env_gemini_key',
            'MCP_API_KEY': 'env_mcp_key',
            'CRONOS_FACILITATOR_URL': 'https://env-facilitator.com',
            'AGENT_REGISTRY_ENDPOINT': 'https://env-registry.com',
            'DEBUG': 'true',
            'LOG_LEVEL': 'DEBUG',
            'PORT': '9000'
        }
        
        with patch.dict(os.environ, test_env):
            config = AgentConfiguration()
            
            assert config.crewai.api_key == 'env_gemini_key'
            assert config.mcp.api_key == 'env_mcp_key'
            assert config.payment.facilitator_url == 'https://env-facilitator.com'
            assert config.a2a.registry_endpoint == 'https://env-registry.com'
            assert config.server.debug == True
            assert config.server.log_level == 'DEBUG'
            assert config.server.port == 9000