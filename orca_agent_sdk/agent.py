from typing import Dict, Any, Optional, List
import json
import os

from .config import AgentConfig
from .server import AgentServer
from .core.wallet import AgentWalletManager

from .contracts.agent_vault import OrcaAgentVaultClient
from .core.registries import RegistryManager

class OrcaAgent:
    """
    Simplified interface for creating and running an Orca Agent using the Sovereign Vault.
    """

    def __init__(
        self, 
        name: str,
        model: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        credits_file: Optional[str] = None,
        price: str = "0.0",
        api_key: Optional[str] = None,
        vault_address: Optional[str] = None
    ):
        self.name = name
        self.model = model
        self.tools = tools or []
        self.credits_file = credits_file
        self.base_price = price
        self.api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

        if not self.api_key:
            print("Warning: No API key found. Please set GEMINI_API_KEY or GOOGLE_API_KEY environment variable.")

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
            token_address="0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0", 
            chain_caip="eip155:338", 
            wallet_address="0xABC123..."
        )
        
        # Override from env
        if os.getenv("CREATOR_WALLET_ADDRESS"):
            self.config.wallet_address = os.getenv("CREATOR_WALLET_ADDRESS")

        # Load Identity Private Key
        wallet_manager = AgentWalletManager(self.config.identity_wallet_path)
        self._private_key = wallet_manager._private_key
        
        # Resolve Vault Address
        self.vault_address = vault_address or os.getenv("AGENT_VAULT")
        if not self.vault_address:
            # Try looking up in registry
            try:
                registry = RegistryManager()
                self.vault_address = registry.get_agent_vault(self.config.on_chain_id)
            except: pass
            
        # Initialize Vault Client if address found
        if self.vault_address:
            self.vault_client = OrcaAgentVaultClient(self.config, self.vault_address, self._private_key)
        else:
            print(f"Warning: No vault address found for {self.name}. Payment features may be disabled.")
            self.vault_client = None

        self.server = None

    def _load_tool_prices(self) -> Dict[str, str]:
        if not self.credits_file or not os.path.exists(self.credits_file):
            return {}
        try:
            with open(self.credits_file, 'r') as f:
                data = json.load(f)
                if "tools" in data:
                    return data["tools"]
                return data
        except Exception as e:
            print(f"Warning: Failed to load credits file: {e}")
            return {}

    def run(self, port: int = 8000, host: str = "0.0.0.0"):
        """Starts the Agent Server."""
        print(f"Starting {self.name} on {host}:{port}")
        self.server = AgentServer(self.config, handler=self)
        self.server.run(host=host, port=port)

    def claim_payment(self, task_id: str, amount: float) -> str:
        """Manually trigger a spend() call on the sovereign vault."""
        if not self.vault_client: raise ValueError("Vault not configured")
        amount_units = int(amount * 10**6)
        print(f"[{self.name}] Claiming {amount} USDC from vault for task {task_id}...")
        return self.vault_client.spend(task_id, amount_units)

    def withdraw_earnings(self) -> str:
        """Withdraws all earnings from the sovereign vault."""
        if not self.vault_client: raise ValueError("Vault not configured")
        print(f"[{self.name}] Withdrawing all earnings from vault...")
        return self.vault_client.withdraw()

    def get_earnings_balance(self) -> float:
        """Returns the current balance in the vault (in USDC)."""
        if not self.vault_client: return 0.0
        balance_units = self.vault_client.get_balance()
        return balance_units / 10**6
