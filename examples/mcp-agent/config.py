"""
Configuration management for MCP Market Data Agent.
Centralizes all configuration settings for MCP API, payment, and CrewAI parameters.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class MCPConfig:
    """Configuration for MCP Market Data API"""
    api_endpoint: str = "https://mcp.crypto.com/market-data/mcp"
    timeout_seconds: int = 30
    retry_attempts: int = 1
    api_key: Optional[str] = None
    
    def __post_init__(self):
        # Load API key from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv("MCP_API_KEY")

@dataclass
class PaymentConfig:
    """Configuration for x402 payment settings"""
    price: str = "0.1"  # Default price in tokens
    token_address: str = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1"  # Cronos Testnet USDC
    chain_caip: str = "eip155:338"  # Cronos Testnet
    facilitator_url: Optional[str] = None
    
    def __post_init__(self):
        # Load facilitator URL from environment if not provided
        if self.facilitator_url is None:
            self.facilitator_url = os.getenv("CRONOS_FACILITATOR_URL")

@dataclass
class CrewAIConfig:
    """Configuration for CrewAI backend parameters"""
    model: str = "gemini-2.0-flash"
    provider: str = "GoogleGenAI"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 1000
    processing_timeout: int = 30
    mcps: list = None
    
    def __post_init__(self):
        if self.mcps is None:
            self.mcps = [
                {
                    "type": "http",
                    "url": "https://mcp.crypto.com/market-data/mcp",
                }
            ]
        # Load API key from environment if not provided
        if self.api_key is None:
            self.api_key = os.getenv("GEMINI_API_KEY")

@dataclass
class A2AConfig:
    """Configuration for Agent-to-Agent communication"""
    agent_id: str = "mcp-market-data-agent"
    registry_endpoint: Optional[str] = None
    message_timeout: int = 10
    
    def __post_init__(self):
        # Load registry endpoint from environment if not provided
        if self.registry_endpoint is None:
            self.registry_endpoint = os.getenv("AGENT_REGISTRY_ENDPOINT")

@dataclass
class ServerConfig:
    """Configuration for FastAPI server"""
    host: str = "0.0.0.0"
    port: int = 8002
    debug: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        # Override with environment variables if available
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.log_level = os.getenv("LOG_LEVEL", self.log_level)
        if os.getenv("PORT"):
            self.port = int(os.getenv("PORT"))

class AgentConfiguration:
    """Main configuration class that combines all component configurations"""
    
    def __init__(self):
        self.mcp = MCPConfig()
        self.payment = PaymentConfig()
        self.crewai = CrewAIConfig()
        self.a2a = A2AConfig()
        self.server = ServerConfig()
        
        # Validate critical configurations
        self._validate_config()
    
    def _validate_config(self):
        """Validate that critical configuration values are present"""
        errors = []
        
        if not self.crewai.api_key:
            errors.append("GEMINI_API_KEY environment variable is required for CrewAI backend")
        
        if not self.payment.token_address:
            errors.append("Token address is required for payment configuration")
        
        if not self.payment.chain_caip:
            errors.append("Chain CAIP identifier is required for payment configuration")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def to_agent_config_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with AgentConfig"""
        return {
            "agent_id": self.a2a.agent_id,
            "price": self.payment.price,
            "token_address": self.payment.token_address,
            "chain_caip": self.payment.chain_caip,
            "ai_backend": "crewai",
            "db_path": f"{self.a2a.agent_id}.db",
            "backend_options": {
                "provider": self.crewai.provider,
                "model": self.crewai.model,
                "api_key": self.crewai.api_key,
                "temperature": self.crewai.temperature,
                "max_tokens": self.crewai.max_tokens,
                "mcps": self.crewai.mcps
            }
        }
    
    def get_mcp_headers(self) -> Dict[str, str]:
        """Get headers for MCP API requests"""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"{self.a2a.agent_id}/1.0"
        }
        
        if self.mcp.api_key:
            headers["Authorization"] = f"Bearer {self.mcp.api_key}"
        
        return headers

# Global configuration instance - initialized lazily
config = None

def get_config() -> AgentConfiguration:
    """Get the global configuration instance, initializing if needed"""
    global config
    if config is None:
        config = AgentConfiguration()
    return config