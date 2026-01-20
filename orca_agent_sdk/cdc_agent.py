from typing import Dict, Any, Optional, List
import os
from .agent import OrcaAgent

class CryptoComAgent(OrcaAgent):
    """
    Specialized Orca Agent for the Crypto.com AI ecosystem.
    Inherits all x402 payment and vault features from OrcaAgent.
    """

    def __init__(
        self, 
        name: str,
        price: str = "0.0",
        cdc_api_key: Optional[str] = None,
        cdc_private_key: Optional[str] = None,
        cdc_sso_wallet_url: Optional[str] = None,
        vault_address: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        provider: str = "GoogleGenAI",
        provider_api_key: Optional[str] = None,
        temperature: float = 0.7,
        plugins: Optional[Dict[str, Any]] = None
    ):
        # Default plugins if none provided
        if plugins is None:
            plugins = {
                "crypto_com_exchange": {
                    "instructions": "You are a professional financial assistant. Use exchange tools to fetch real-time data."
                }
            }

        # Use provided keys or fall back to environment variables
        api_key = provider_api_key or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        # Initialize the base OrcaAgent with specific CDC configurations
        super().__init__(
            name=name,
            model=model,
            system_prompt="CDC Sovereign Agent", # Placeholder, CDC backend handles its own prompts/plugins
            price=price,
            api_key=api_key,
            vault_address=vault_address
        )

        # Re-configure for Crypto.com Backend
        self.config.ai_backend = "crypto_com"
        self.config.cdc_api_key = cdc_api_key or os.getenv("CDC_API_KEY")
        self.config.cdc_private_key = cdc_private_key or os.getenv("CDC_PRIVATE_KEY")
        self.config.cdc_sso_wallet_url = cdc_sso_wallet_url or os.getenv("CDC_SSO_WALLET_URL")

        # Update backend options specifically for CDC
        self.config.backend_options.update({
            "provider": provider,
            "model": model,
            "provider_api_key": api_key,
            "temperature": temperature,
            "plugins": plugins
        })

        # Re-initialize the backend since it was likely initialized as 'crewai' in super().__init__
        from .server import AgentServer # Avoid circular import if needed, though OrcaAgent already uses it
        # Actually server.py does the backend loading. 
        # When OrcaAgent.run() is called, it creates AgentServer which calls _load_backend.
        # So setting self.config.ai_backend here is sufficient.
