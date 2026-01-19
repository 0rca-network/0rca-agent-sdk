import requests
import json
import time
from web3 import Web3
from eth_account import Account

# --- CONFIGURATION ---
AGENT_URL = "http://localhost:8000/agent"
RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1"
MNEMONIC = "dish public milk ramp capable venue poverty grain useless december hedgehog shuffle"
AGENT_WALLET = "0x975C5b75Ff1141E10c4f28454849894F766B945E"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
Account.enable_unaudited_hdwallet_features()
user = Account.from_mnemonic(MNEMONIC)

# Minimal ABI for USDC.e transfer
USDC_ABI = [
    {"constant": False, "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}], "name": "transfer", "outputs": [{"name": "", "type": "bool"}], "type": "function"},
    {"constant": True, "inputs": [{"name": "_owner", "type": "address"}], "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}], "type": "function"}
]

def real_transfer():
    print(f"--- STARTING REAL ON-CHAIN TRANSFER ---")
    usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_ADDRESS), abi=USDC_ABI)
    
    # 1. Check Initial Balance
    balance = usdc_contract.functions.balanceOf(user.address).call()
    print(f"Current Balance: {balance / 10**6} USDC.E")
    
    if balance < 1_000_000:
        print("Error: Insufficient USDC.E balance.")
        return False

    # 2. Build Transaction
    print(f"Transferring 1.0 USDC.E to Agent {AGENT_WALLET}...")
    nonce = w3.eth.get_transaction_count(user.address)
    tx = usdc_contract.functions.transfer(
        Web3.to_checksum_address(AGENT_WALLET),
        1_000_000  # 1.0 USDC.e (6 decimals)
    ).build_transaction({
        'chainId': 338,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })

    # 3. Sign and Send
    signed_tx = w3.eth.account.sign_transaction(tx, user.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction Sent! Hash: {w3.to_hex(tx_hash)}")
    
    # 4. Wait for Confirmation
    print("Waiting for confirmation on Cronos Testnet...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction Confirmed in block {receipt.blockNumber}")
    
    # 5. Check Final Balance
    new_balance = usdc_contract.functions.balanceOf(user.address).call()
    print(f"New Balance: {new_balance / 10**6} USDC.E")
    return True

def interact_after_paying():
    print(f"\n--- INTERACTING WITH AGENT ---")
    # Using the bypass header since we just paid manually on-chain
    headers = {
        "Content-Type": "application/json",
        "X-TEST-BYPASS": "true"
    }
    payload = {"prompt": "Real money sent! Now tell me, how does it feel to be a paid AI?"}
    
    r = requests.post(AGENT_URL, json=payload, headers=headers)
    if r.status_code == 200:
        print("\nAGENT RESPONSE:")
        print(r.json().get("result"))
    else:
        print(f"Error: {r.status_code} - {r.text}")

if __name__ == "__main__":
    # Before running, enable the bypass again in the server locally so we can test the interaction
    # (The user wants to see the money move)
    if real_transfer():
        interact_after_paying()
