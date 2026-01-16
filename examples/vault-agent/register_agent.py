import os
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# This script registers a new Agent ID and links it to your Vault
RPC_URL = "https://evm-t3.cronos.org"
IDENTITY_REGISTRY = "0x58e67dEEEcde20f10eD90B5191f08f39e81B6658"

def register():
    # 1. Setup Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    # Load private key from root agent_identity.json
    try:
        with open("agent_identity.json", "r") as f:
            identity = json.load(f)
            private_key = identity["private_key"]
            account = w3.eth.account.from_key(private_key)
    except FileNotFoundError:
        print("Error: agent_identity.json not found in root.")
        return None

    # 2. Get Registry Contract
    abi_path = "orca_agent_sdk/contracts/abis/IdentityRegistry.json"
    with open(abi_path, "r") as f:
        artifact = json.load(f)
        # Handle both raw ABI list and Hardhat artifact object
        abi = artifact.get("abi", artifact)
        
    registry = w3.eth.contract(address=IDENTITY_REGISTRY, abi=abi)

    # 3. Register
    print(f"Registering new Agent ID for {account.address}...")
    nonce = w3.eth.get_transaction_count(account.address)
    
    tx = registry.functions.register().build_transaction({
        'chainId': 338,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Registration Tx Sent: {w3.to_hex(tx_hash)}")
    
    # Wait for receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    # The agentId is in the Registered event
    logs = registry.events.Registered().process_receipt(receipt)
    agent_id = logs[0]['args']['agentId']
    
    print(f"SUCCESS! Your new Agent ID is: {agent_id}")
    return agent_id, account, registry, private_key, w3

def set_metadata(agent_id, vault_address, account, registry, private_key, w3):
    print(f"Setting metadata for Agent {agent_id}...")
    
    keys = ["endpoint", "vault"]
    values = ["http://localhost:8000", vault_address]
    
    for key, val in zip(keys, values):
        nonce = w3.eth.get_transaction_count(account.address)
        tx = registry.functions.setMetadata(
            agent_id, 
            key, 
            val.encode('utf-8')
        ).build_transaction({
            'chainId': 338,
            'gas': 200000,
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
        })
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        print(f"Set {key} -> {val} (Tx: {w3.to_hex(tx_hash)})")
        w3.eth.wait_for_transaction_receipt(tx_hash)

if __name__ == "__main__":
    # In a real run, you'd get the vault address from the deployment
    # For now, let's assume one is provided in env or just print what to do
    vault_addr = os.getenv("AGENT_VAULT")
    if not vault_addr:
        print("Please set AGENT_VAULT environment variable first.")
    else:
        id, acc, reg, pk, w3 = register()
        set_metadata(id, vault_addr, acc, reg, pk, w3)
