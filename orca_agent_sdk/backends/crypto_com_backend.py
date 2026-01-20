"""
Crypto.com Backend Adapter for Orca Agent SDK.

This module provides a production-ready integration with the Crypto.com AI Agent SDK,
wrapping it with x402 payment protocol support from the Orca Agent SDK.
"""

from typing import Callable, Optional
from ..config import AgentConfig
from .base import AbstractAgentBackend
import logging
import traceback

logger = logging.getLogger(__name__)


class CryptoComBackend(AbstractAgentBackend):
    """
    Production backend adapter for Crypto.com AI Agent SDK.
    
    This backend wraps the Crypto.com Agent SDK and integrates it with the 
    Orca x402 payment layer. Prompts are handled by the CDC Agent's interact() method.
    """
    
    def __init__(self):
        self.agent = None
        self.config = None
        self._initialized = False
    
    def initialize(self, config: AgentConfig, handler: Callable[[str], str]) -> None:
        """
        Initialize the Crypto.com Agent with the provided configuration.
        
        Args:
            config: AgentConfig containing CDC credentials and LLM settings
            handler: The parent OrcaAgent/CryptoComAgent handler (not used in CDC mode)
        """
        self.config = config

        # Import the CDC SDK
        try:
            from crypto_com_agent_client import Agent
            from crypto_com_agent_client.lib.types.llm_config import LLMConfig
            from crypto_com_agent_client.lib.types.blockchain_config import BlockchainConfig
            from crypto_com_agent_client.lib.types.plugins_config import PluginsConfig
        except ImportError as e:
            logger.error(f"crypto_com_agent_client not installed: {e}")
            print(f"[CDC Backend] ERROR: crypto_com_agent_client not installed. Install with: pip install cryptocom-agent-client")
            return

        # Extract configuration
        backend_opts = self.config.backend_options or {}
        
        # LLM Configuration
        llm_provider = backend_opts.get("provider", "GoogleGenAI")
        llm_model = backend_opts.get("model", "gemini-2.0-flash")
        provider_api_key = backend_opts.get("provider_api_key")
        temperature = backend_opts.get("temperature", 0.7)
        
        if not provider_api_key:
            logger.error("No LLM provider API key configured")
            print("[CDC Backend] ERROR: provider_api_key is required in backend_options")
            return
        
        # Blockchain Configuration (optional for basic LLM usage)
        cdc_api_key = self.config.cdc_api_key
        cdc_private_key = self.config.cdc_private_key
        cdc_sso_url = self.config.cdc_sso_wallet_url
        
        # Plugin Configuration
        plugins_opts = backend_opts.get("plugins", {})
        personality = plugins_opts.get("personality", {
            "tone": "professional",
            "language": "English", 
            "verbosity": "medium"
        })
        instructions = plugins_opts.get("instructions", 
            "You are a sovereign AI agent on the 0rca Network. "
            "You can help users with queries and perform tasks."
        )
        
        print(f"[CDC Backend] Initializing...")
        print(f"[CDC Backend] LLM Provider: {llm_provider}")
        print(f"[CDC Backend] Model: {llm_model}")
        print(f"[CDC Backend] API Key: {'*' * 4 + provider_api_key[-4:] if provider_api_key else 'NOT SET'}")
        
        try:
            # Build configuration dictionaries
            # Extract extended config
            transfer_limit = backend_opts.get("transfer_limit")
            blockchain_timeout = backend_opts.get("timeout")
            
            # 1. LLM Config
            llm_config = {
                "provider": llm_provider,
                "model": llm_model,
                "temperature": temperature,
                "provider-api-key": provider_api_key
            }
            if transfer_limit is not None:
                llm_config["transfer-limit"] = transfer_limit

            # 2. Blockchain Config
            # If API key is missing, Agent.init fails on None or empty dict.
            # We must provide a config with at least a dummy key to initialize the LLM part.
            effective_api_key = cdc_api_key or "missing-api-key-placeholder"
            effective_private_key = cdc_private_key or "missing-private-key"
            
            blockchain_config = {
                "api-key": effective_api_key,
                "private-key": effective_private_key,
                "sso-wallet-url": cdc_sso_url or ""
            }
            if blockchain_timeout:
                blockchain_config["timeout"] = blockchain_timeout
            
            if not cdc_api_key:
                logger.warning("CDC_API_KEY not found. Using placeholder to allow initialization.")
                print(f"[CDC Backend] WARNING: CDC_API_KEY not found. Blockchain features may fail.")
            else:
                 print(f"[CDC Backend] Blockchain config: Enabled")
            
            # 3. Plugins Config
            plugins_config = {
                "personality": personality,
                "instructions": instructions
            }
            
            # Initialize the CDC Agent
            print(f"[CDC Backend] Calling Agent.init()...")
            try:
                self.agent = Agent.init(
                    llm_config=llm_config,
                    blockchain_config=blockchain_config,
                    plugins=plugins_config
                )
                print(f"[CDC Backend] Agent.init() returned: {type(self.agent)}")
            except BaseException as agent_err:
                 print(f"[CDC Backend] Agent.init() CRASHED: {type(agent_err)}: {agent_err}")
                 logger.critical(f"Agent.init() crashed: {agent_err}", exc_info=True)
                 raise agent_err
            
            self._initialized = True
            print(f"[CDC Backend] Agent initialized successfully!")
            logger.info("Crypto.com Agent initialized successfully")
            
        except BaseException as e:
            logger.error(f"Failed to initialize CDC Agent: {e}", exc_info=True)
            print(f"[CDC Backend] FAILED to initialize: {e}")
            traceback.print_exc()
            self.agent = None
            self._initialized = False

    def handle_prompt(self, prompt: str) -> str:
        """
        Handle an incoming prompt using the CDC Agent.
        
        Args:
            prompt: The user's input prompt
            
        Returns:
            The agent's response as a string
        """
        if not self._initialized or self.agent is None:
            logger.warning("CDC Agent not initialized, returning error")
            return "[Error] Crypto.com Agent not initialized. Check your configuration and API keys."
        
        try:
            logger.info(f"Processing prompt: {prompt[:50]}...")
            response = self.agent.interact(prompt)
            logger.info(f"Response received: {str(response)[:100]}...")
            return str(response)
        except Exception as e:
            logger.error(f"Error during interact(): {e}")
            traceback.print_exc()
            return f"[Error] Agent interaction failed: {str(e)}"
