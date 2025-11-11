from dataclasses import dataclass
from typing import Optional


@dataclass
class AgentConfig:
    """
    Opinionated configuration for an Orca agent.

    Agent dev MUST provide:
    - agent_id: unique identifier used by your marketplace
    - receiver_address: Algorand address where this agent earns
    - price_microalgos: price per job in microAlgos

    The rest can be defaulted / controlled by your infra.
    """

    agent_id: str
    receiver_address: str
    price_microalgos: int
    agent_token: Optional[str] = None

    # Network / protocol settings (you / marketplace can standardize)
    network: str = "testnet"
    algod_url: str = "https://testnet-api.algonode.cloud"
    algod_token: str = ""
    indexer_url: str = "https://testnet-idx.algonode.cloud"
    indexer_token: str = ""

    # On-chain app that encodes your marketplace / verification logic
    app_id: int = 749378614

    # Local persistence
    db_path: str = "agent_local.db"

    # Internal tuning (can be adjusted later, not exposed to most users)
    flat_fee: int = 2000  # microAlgos
    timeout_seconds: int = 30
    
    # Remote server settings
    remote_server_url: str = "http://localhost:3000/api/agent/access"

    def validate(self) -> None:
        if not self.agent_id:
            raise ValueError("agent_id is required")
        if not self.receiver_address:
            raise ValueError("receiver_address is required")
        if not isinstance(self.price_microalgos, int) or self.price_microalgos <= 0:
            raise ValueError("price_microalgos must be a positive integer")
        if not isinstance(self.app_id, int) or self.app_id <= 0:
            raise ValueError("app_id must be a positive integer")