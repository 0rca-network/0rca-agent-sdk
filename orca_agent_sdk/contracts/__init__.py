import os
import json

def load_abi(contract_name: str) -> dict:
    """
    Loads the ABI for a given contract name from the package resources.
    """
    if not contract_name.endswith(".json"):
        contract_name += ".json"
    
    abi_path = os.path.join(os.path.dirname(__file__), "abis", contract_name)
    
    if not os.path.exists(abi_path):
        raise FileNotFoundError(f"ABI for {contract_name} not found at {abi_path}")
        
    with open(abi_path, "r") as f:
        artifact = json.load(f)
        return artifact.get("abi", artifact)
