import json
import os
from web3 import Web3
from ..constants import IDENTITY_REGISTRY, REPUTATION_REGISTRY, VALIDATION_REGISTRY

class RegistryManager:
    """
    Production-grade manager for on-chain registries (Identity, Reputation, Validation).
    """
    def __init__(self, rpc_url: str = "https://evm-t3.cronos.org"):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.abis = self._load_abis()

    def _load_abis(self):
        base_path = os.path.join(os.path.dirname(__file__), "..", "contracts", "abis")
        abis = {}
        for name in ["IdentityRegistry", "ReputationRegistry", "ValidationRegistry"]:
            path = os.path.join(base_path, f"{name}.json")
            if os.path.exists(path):
                with open(path, "r") as f:
                    abis[name] = json.load(f)
        return abis

    # --- IDENTITY ---
    def get_agent_endpoint(self, agent_id: int) -> str:
        if "IdentityRegistry" not in self.abis: return ""
        contract = self.w3.eth.contract(address=IDENTITY_REGISTRY, abi=self.abis["IdentityRegistry"])
        try:
            # Metadata is stored as bytes
            val = contract.functions.getMetadata(agent_id, "endpoint").call()
            return val.decode("utf-8") if val else ""
        except:
            return ""

    # --- REPUTATION ---
    def get_agent_reputation(self, agent_id: int) -> dict:
        if "ReputationRegistry" not in self.abis: return {"count": 0, "score": 0}
        contract = self.w3.eth.contract(address=REPUTATION_REGISTRY, abi=self.abis["ReputationRegistry"])
        try:
            # getSummary returns (count, averageScore)
            count, score = contract.functions.getSummary(agent_id, [], b"", b"").call()
            return {"count": count, "score": score}
        except Exception as e:
            return {"error": str(e), "count": 0, "score": 0}

    # --- VALIDATION ---
    def get_validation_status(self, agent_id: int) -> dict:
        if "ValidationRegistry" not in self.abis: return {"count": 0, "avg": 0}
        contract = self.w3.eth.contract(address=VALIDATION_REGISTRY, abi=self.abis["ValidationRegistry"])
        try:
            count, avg = contract.functions.getSummary(agent_id, [], b"").call()
            return {"count": count, "avg": avg}
        except:
             return {"count": 0, "avg": 0}
