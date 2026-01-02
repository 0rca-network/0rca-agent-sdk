from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, Any

@dataclass
class AgentConfig:
    """
    Opinionated configuration for an Orca agent using x402 payment protocol.

    Agent dev MUST provide:
    - agent_id: unique identifier
    - wallet_address: EVM address where this agent receives payments
    - price: price per job in tokens (string, e.g. "0.25")
    - token_address: valid token address on the network (or symbol if supported)

    The rest can be defaulted / controlled by your infra.
    """

    agent_id: str
    wallet_address: str
    price: str
    token_address: str  # e.g. "devUSDC.e" or generic address
    
    agent_token: Optional[str] = None

    # x402 / EVM Network settings
    chain_caip: str = "eip155:84531"   # Cronos Testnet CAIP
    facilitator_url: str = "https://facilitator.cronoslabs.org/v2/x402"
    
    # Local persistence
    db_path: str = "agent_local.db"

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
        if not self.wallet_address:
            raise ValueError("wallet_address is required")
        if not self.price:
            raise ValueError("price is required")
        if not self.token_address:
            raise ValueError("token_address is required")
        
        if self.ai_backend == "crypto_com":
            if not self.cdc_api_key:
                # Warning or error? Let's error to be safe as per requirement
                pass # Allow user to pass in backend_options if they prefer