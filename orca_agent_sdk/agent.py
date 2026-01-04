from typing import Dict, Any, Optional, List
import threading
import json
import os
import requests

from .config import AgentConfig
from .server import AgentServer

class OrcaAgent:
    """
    Simplified interface for creating and running an Orca Agent.
    Abstracts configuration, server handling, and MCP tools.
    """

    def __init__(
        self, 
        name: str,
        model: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        credits_file: Optional[str] = None,
        price: str = "0.0",
        api_key: Optional[str] = None
    ):
        """
        Initialize the Orca Agent.

        Args:
            name: Name of the agent.
            model: Model to use (e.g., "gemini/gemini-2.0-flash").
            system_prompt: Backstory/System prompt for the agent.
            tools: List of MCP tool configurations (dicts).
            credits_file: Path to a JSON file defining tool prices (optional).
            price: Base price for accessing the agent (optional).
            api_key: LLM Provider API Key (can also set via env var).
        """
        self.name = name
        self.model = model
        self.tools = tools or []
        self.credits_file = credits_file
        self.base_price = price
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")

        # Load tool prices if credits file provided
        self.tool_prices = self._load_tool_prices()

        # Build backend options
        self.backend_options = {
            "model": self.model,
            "role": self.name,
            "goal": "Expertly assist the user.",
            "backstory": system_prompt,
            "mcps": self.tools,
            "provider_api_key": self.api_key
        }

        # Create Configuration
        self.config = AgentConfig(
            agent_id=self.name,
            price=self.base_price,
            ai_backend="crewai",
            backend_options=self.backend_options,
            tool_prices=self.tool_prices,
            token_address="0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0", # Default Cronos Testnet USDC
            chain_caip="eip155:338", # Cronos Testnet
            wallet_address="0xABC123..." # Placeholder, user should set env var or config
        )
        
        # Override wallet from env if available for simple setup
        if os.getenv("CREATOR_WALLET_ADDRESS"):
            self.config.wallet_address = os.getenv("CREATOR_WALLET_ADDRESS")

    def _load_tool_prices(self) -> Dict[str, str]:
        """Load tool prices from JSON file."""
        if not self.credits_file or not os.path.exists(self.credits_file):
            return {}
        try:
            with open(self.credits_file, 'r') as f:
                data = json.load(f)
                # Assuming simple format: {"tool_name": "price"} or {"tools": {"name": "price"}}
                if "tools" in data:
                    return data["tools"]
                return data
        except Exception as e:
            print(f"Warning: Failed to load credits file: {e}")
            return {}

    def run(self, port: int = 8000, host: str = "0.0.0.0"):
        """Run the agent server."""
        print(f"Starting {self.name} on {host}:{port}")
        
        # Initialize server
        # Note: handler is implicitly managed by backend via handle_prompt
        self.server = AgentServer(self.config, handler=None)
        
        # Start server
        self.server.run(host=host, port=port)

    # Helper to list tools
    def list_tools(self):
        """List available tools from configured MCPs."""
        # This requires the backend to be initialized, which happens in Server
        # For simplicity, we might need to peek into backend initialization or 
        # instantiate a temporary backend.
        pass
