from typing import Callable
from ..config import AgentConfig
from .base import AbstractAgentBackend
import logging

class CryptoComBackend(AbstractAgentBackend):
    """
    Backend adapter for Crypto.com AI Agent SDK.
    """
    
    def initialize(self, config: AgentConfig, handler: Callable[[str], str]) -> None:
        self.config = config
        self.agent = None

        # Try to import optional dependency
        try:
            from crypto_com_agent_client import Agent
        except ImportError:
            logging.warning("crypto_com_agent_client not installed. CDC Backend will fail if utilized.")
            return

        # Initialize the CDC Agent if config is present
        llm_provider = self.config.backend_options.get("provider", "GoogleGenAI")
        llm_model = self.config.backend_options.get("model", "gemini-2.0-flash")
        
        # Use provided key or fallback to environment variable
        provider_key = self.config.backend_options.get("provider_api_key") or self.config.cdc_api_key

        print(f"Initializing CDC Agent with provider {llm_provider}...")
        self.agent = Agent.init(
            llm_config={
                "provider": llm_provider,
                "model": llm_model,
                "provider-api-key": provider_key,
                "temperature": self.config.backend_options.get("temperature", 0.7),
            },
            blockchain_config={
                "api-key": self.config.cdc_api_key or "placeholder",
                "private-key": self.config.cdc_private_key or "",
                "sso-wallet-url": self.config.cdc_sso_wallet_url or "",
                "timeout": 30
            },
            plugins=self.config.backend_options.get("plugins", {
                "crypto_com_exchange": {
                    "instructions": "You are a professional financial assistant. Use exchange tools to fetch real-time data."
                }
            })
        )
        print("CDC Agent initialized with plugins.")

    def handle_prompt(self, prompt: str) -> str:
        if self.agent:
            try:
                # Trying interact() based on search results
                response = self.agent.interact(prompt)
                return str(response)
            except Exception as e:
                return f"Error from CDC Agent: {str(e)}"
        
        return f"[Crypto.com Backend Fallback] Received: {prompt}"
