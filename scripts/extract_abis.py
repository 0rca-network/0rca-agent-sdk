import json
import os

def extract_abi(contract_name, source_json, dest_json):
    if not os.path.exists(source_json):
        print(f"Error: {source_json} not found")
        return
    with open(source_json, 'r') as f:
        data = json.load(f)
        abi = data.get("abi", data)
    
    os.makedirs(os.path.dirname(dest_json), exist_ok=True)
    with open(dest_json, 'w') as f:
        json.dump(abi, f)
    print(f"Extracted ABI for {contract_name} to {dest_json}")

# TaskEscrow
extract_abi(
    "TaskEscrow",
    "contracts-project/artifacts/contracts/TaskEscrow.sol/TaskEscrow.json",
    "orca_agent_sdk/contracts/abis/TaskEscrow.json"
)

# AgentEscrow
extract_abi(
    "AgentEscrow",
    "contracts-project/artifacts/contracts/AgentEscrow.sol/AgentEscrow.json",
    "orca_agent_sdk/contracts/abis/AgentEscrow.json"
)

# OrcaAgentVault
extract_abi(
    "OrcaAgentVault",
    "contracts-project/artifacts/contracts/OrcaAgentVault.sol/OrcaAgentVault.json",
    "orca_agent_sdk/contracts/abis/OrcaAgentVault.json"
)
