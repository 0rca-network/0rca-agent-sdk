from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any

@dataclass
class AgentConfig:
    """
    Opinionated configuration for an Orca agent using x402 payment protocol.

    Agent dev MUST provide:
    - agent_id: unique identifier
    - price: price per job in tokens (string, e.g. "0.25")
    - on_chain_id: (Optional) ERC-8004 ID. Defaults to 0 if not provided.

    Optional:
    - wallet_address: If provided, can be used for direct payments. If None, MUST use escrow.
    """

    agent_id: str
    price: str
    wallet_address: Optional[str] = None
    token_address: str = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1" # Default to USDC.e
    
    agent_token: Optional[str] = None

    # Tool-specific paywalls (e.g., {"say_hello": "0.1"})
    tool_prices: Dict[str, str] = field(default_factory=dict)

    # ERC-8004 / On-chain identity
    on_chain_id: int = 0  # Default ID

    # x402 / EVM Network settings
    chain_caip: str = "eip155:338"   # Cronos Testnet CAIP
    facilitator_url: str = "https://facilitator.cronoslabs.org/v2/x402"
    
    # CroGas / Gas Station settings
    crogas_url: Optional[str] = "http://144.126.253.20"
    usdc_address: str = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1" # Cronos Testnet USDC
    
    # Local persistence
    db_path: str = "/tmp/agent_local.db"
    identity_wallet_path: str = "agent_identity.json"

    # Internal timeout
    timeout_seconds: int = 30
    
    # Remote server settings
    remote_server_url: str = "http://localhost:3000/api/agent/access"

    # --- Backend Configuration ---
    ai_backend: Literal["crewai", "agno", "crypto_com"] = "crewai"
    
    # Valid for Crypto.com backend
    cdc_api_key: Optional[str] = None
    cdc_private_key: Optional[str] = None
    cdc_sso_wallet_url: Optional[str] = None
    
    # Generic extra config for backends
    backend_options: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.price:
            raise ValueError("price is required")
        # wallet_address is now optional
        
        if self.ai_backend == "crypto_com":
            if not self.cdc_api_key:
                # Warning or error? Let's error to be safe as per requirement
                pass # Allow user to pass in backend_options if they prefer