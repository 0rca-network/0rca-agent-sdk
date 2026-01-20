"""
CryptoComAgent - A specialized Orca Agent for Crypto.com AI integration.

This module provides a high-level interface for creating AI agents that:
1. Use the Crypto.com AI Agent SDK for LLM interactions
2. Integrate with the x402 payment protocol for monetization
3. Connect to Sovereign Vaults for on-chain earnings collection
"""

from typing import Dict, Any, Optional, List, Callable
import os
from .agent import OrcaAgent


class CryptoComAgent(OrcaAgent):
    """
    Specialized Orca Agent for the Crypto.com AI ecosystem.
    
    Inherits all x402 payment and vault features from OrcaAgent, but uses the
    Crypto.com AI Agent SDK as the backend for processing prompts.
    
    Example:
        ```python
        from orca_agent_sdk import CryptoComAgent
        
        agent = CryptoComAgent(
            name="My-DeFi-Agent",
            price="0.1",
            provider_api_key="your-gemini-key",
            vault_address="0x..."
        )
        agent.run(port=8000)
        ```
    """

    def __init__(
        self, 
        name: str,
        price: str = "0.0",
        # LLM Configuration
        provider: str = "GoogleGenAI",
        model: str = "gemini-2.0-flash",
        provider_api_key: Optional[str] = None,
        temperature: float = 0.7,
        # CDC Blockchain Configuration (optional - for on-chain tools)
        cdc_api_key: Optional[str] = None,
        cdc_private_key: Optional[str] = None,
        cdc_sso_wallet_url: Optional[str] = None,
        # CDC Advanced Config
        transfer_limit: Optional[float] = None, # -1 for unlimited, 0 for none, >0 for limit
        timeout: Optional[int] = None, # Request timeout in seconds
        # Orca Payment Configuration
        vault_address: Optional[str] = None,
        # Agent Personality & Instructions
        personality: Optional[Dict[str, str]] = None,
        instructions: Optional[str] = None,
        # Custom Tools
        tools: Optional[List[Callable[..., Any]]] = None
    ):
        """
        Initialize a CryptoComAgent.
        
        Args:
            name: Unique identifier for the agent
            price: Price per request in USDC (e.g., "0.1")
            provider: LLM provider name (default: "GoogleGenAI")
            model: LLM model name (default: "gemini-2.0-flash")
            provider_api_key: API key for the LLM provider
            temperature: LLM temperature setting (0.0-1.0)
            cdc_api_key: Crypto.com Developer Platform API key (for blockchain tools)
            cdc_private_key: Private key for blockchain transactions
            cdc_sso_wallet_url: SSO wallet URL (optional)
            vault_address: Address of the OrcaAgentVault for payment settlement
            personality: Agent personality settings (tone, language, verbosity)
            instructions: Custom instructions for the agent
            tools: List of custom tool functions
        """
        # Resolve API keys from environment if not provided
        provider_api_key = provider_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        cdc_api_key = cdc_api_key or os.getenv("CDC_API_KEY")
        cdc_private_key = cdc_private_key or os.getenv("CDC_PRIVATE_KEY")
        cdc_sso_wallet_url = cdc_sso_wallet_url or os.getenv("CDC_SSO_WALLET_URL")
        vault_address = vault_address or os.getenv("AGENT_VAULT")
        
        # Default personality
        if personality is None:
            personality = {
                "tone": "professional",
                "language": "English",
                "verbosity": "medium"
            }
        
        # Default instructions
        if instructions is None:
            instructions = (
                f"You are {name}, a sovereign AI agent on the 0rca Network. "
                "You provide helpful, accurate responses and can assist with various tasks."
            )
        
        # Build backend options for the CDC backend
        backend_options = {
            "provider": provider,
            "model": model,
            "provider_api_key": provider_api_key,
            "temperature": temperature,
            "transfer_limit": transfer_limit,
            "timeout": timeout,
            "plugins": {
                "personality": personality,
                "instructions": instructions,
            }
        }
        
        if tools:
            backend_options["plugins"]["tools"] = tools
        
        # Initialize the base OrcaAgent
        # We pass a minimal system_prompt since CDC backend uses its own instructions
        super().__init__(
            name=name,
            model=model,
            system_prompt=instructions,
            price=price,
            api_key=provider_api_key,
            vault_address=vault_address
        )
        
        # Override configuration for CDC backend
        self.config.ai_backend = "crypto_com"
        self.config.cdc_api_key = cdc_api_key
        self.config.cdc_private_key = cdc_private_key
        self.config.cdc_sso_wallet_url = cdc_sso_wallet_url
        self.config.backend_options = backend_options
        
        print(f"[CryptoComAgent] Initialized: {name}")
        print(f"[CryptoComAgent] Backend: crypto_com ({provider}/{model})")
        print(f"[CryptoComAgent] x402 Price: {price} USDC")
        print(f"[CryptoComAgent] Vault: {vault_address or 'Not configured'}")
