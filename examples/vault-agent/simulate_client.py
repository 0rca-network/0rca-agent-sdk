import requests
import os
import json
import secrets
import time
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

# CLIENT SIMULATION
# This simulates an Orchestrator or User interacting with the Sovereign Agent

AGENT_URL = "http://localhost:8000/agent"
RPC_URL = "https://evm-t3.cronos.org"
USDC_TOKEN = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1"

def simulate():
    vault_address = os.getenv("AGENT_VAULT")
    if not vault_address:
        print("Set AGENT_VAULT first.")
        return

    # 1. Setup Wallet
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
    
    with open("agent_identity.json", "r") as f:
        pk = json.load(f)["private_key"]
        account = w3.eth.account.from_key(pk)

    # 1.5. Approve USDC
    usdc_abi = [
        {"inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "name": "approve", "outputs": [{"name": "", "type": "bool"}], "stateMutability": "nonpayable", "type": "function"},
        {"inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}], "name": "allowance", "outputs": [{"name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}
    ]
    usdc = w3.eth.contract(address=USDC_TOKEN, abi=usdc_abi)
    amount = 100000 # 0.1 USDC
    
    allowance = usdc.functions.allowance(account.address, vault_address).call()
    if allowance < amount:
        print(f"Approving USDC for vault {vault_address}...")
        nonce = w3.eth.get_transaction_count(account.address)
        tx = usdc.functions.approve(vault_address, amount * 10).build_transaction({
            'chainId': 338, 'gas': 100000, 'gasPrice': w3.eth.gas_price, 'nonce': nonce
        })
        signed_tx = w3.eth.account.sign_transaction(tx, pk)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print("Approval successful.")

    # 2. Fund the Task in the Vault
    task_id = "0x" + secrets.token_hex(32)
    print(f"Creating Task {task_id} in Vault {vault_address}...")
    
    abi_path = "orca_agent_sdk/contracts/abis/OrcaAgentVault.json"
    with open(abi_path, "r") as f:
        artifact = json.load(f)
        abi = artifact["abi"] if isinstance(artifact, dict) and "abi" in artifact else artifact
    
    vault = w3.eth.contract(address=vault_address, abi=abi)
    
    nonce = w3.eth.get_transaction_count(account.address)
    tx = vault.functions.createTask(
        bytes.fromhex(task_id[2:]),
        amount
    ).build_transaction({
        'chainId': 338,
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, pk)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Task Funded (Tx: {w3.to_hex(tx_hash)})! Waiting for confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Task confirmed in block:", receipt.blockNumber)

    # 3. Call the Agent (Simulate x402)
    # Since we can't easily sign x402 here without the full SDK client, 
    # we'll use the TEST-BYPASS for this debug simulation 
    headers = {
        "X-TEST-BYPASS": "true" 
    }
    
    payload = {
        "prompt": "Analyze the security of my vault contract.",
        "taskId": task_id
    }
    
    print(f"Calling Agent at {AGENT_URL}...")
    resp = requests.post(AGENT_URL, json=payload, headers=headers)
    
    print("Response Status:", resp.status_code)
    print("Response JSON:", json.dumps(resp.json(), indent=2))

if __name__ == "__main__":
    simulate()
