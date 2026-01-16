import os
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

RPC_URL = "https://evm-t3.cronos.org"
VAULT_ADDRESS = "0x84b5f6E6cd9470979907Aff4872eFF7f8A6CB219"

def debug_vault():
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    with open("orca_agent_sdk/contracts/abis/OrcaAgentVault.json", "r") as f:
        abi = json.load(f)
        
    vault = w3.eth.contract(address=VAULT_ADDRESS, abi=abi)
    
    earnings = vault.functions.accumulatedEarnings().call()
    print(f"Accumulated Earnings: {earnings / 10**6} USDC")
    
    # Check the last taskId from the simulation
    # (I'll need to manually check a taskId or list events)
    print("Checking TaskCreated events...")
    events = vault.events.TaskCreated().get_logs(from_block=0)
    for e in events:
        t_id = e['args']['taskId']
        task = vault.functions.tasks(t_id).call()
        print(f"Task {w3.to_hex(t_id)}:")
        print(f"  Budget: {task[0] / 10**6} USDC")
        print(f"  Remaining: {task[1] / 10**6} USDC")
        print(f"  Exists: {task[3]}, Closed: {task[4]}")

if __name__ == "__main__":
    debug_vault()
