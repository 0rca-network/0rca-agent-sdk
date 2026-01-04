import requests
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import json
import time

# --- CONFIGURATION ---
AGENT_URL = "http://localhost:8000/agent"
FACILITATOR_URL = "https://facilitator.cronoslabs.org/v2/x402"
RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"

# USER ACCOUNT (The one you funded)
USER_ADDRESS = "0xcCED528A5b70e16c8131Cb2de424564dD938fD3B"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Minimal ABI for balanceOf
ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def check_balances():
    print(f"\n--- BLOCKCHAIN STATUS (Cronos Testnet) ---")
    try:
        chk_addr = Web3.to_checksum_address(USER_ADDRESS)
        # Check CRO Balance
        cro_balance = w3.eth.get_balance(chk_addr)
        print(f"User CRO Balance: {w3.from_wei(cro_balance, 'ether')} CRO")
        
        # Check USDC.E Balance
        usdc_contract = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_ADDRESS), abi=ERC20_ABI)
        usdc_balance = usdc_contract.functions.balanceOf(chk_addr).call()
        print(f"User USDC.E Balance: {usdc_balance / 10**6} USDC.E")
        return usdc_balance
    except Exception as e:
        print(f"Error checking balances: {e}")
        return 0

def run_test_request():
    print(f"\n--- STEP 1: REQUESTING CHALLENGE ---")
    payload = {"prompt": "What is the current price of CRO?"}
    try:
        r1 = requests.post(AGENT_URL, json=payload)
        if r1.status_code == 402:
            challenge = r1.headers.get("PAYMENT-REQUIRED")
            print(f"SUCCESS: Received 402 Challenge")
            print(f"Challenge (first 50 chars): {challenge[:50]}...")
            return challenge
        else:
            print(f"FAILED: Expected 402, got {r1.status_code}")
            print(f"Body: {r1.text}")
    except Exception as e:
        print(f"Error connecting to agent: {e}")
    return None

if __name__ == "__main__":
    balance = check_balances()
    challenge = run_test_request()
    
    if balance > 0:
        print(f"\nBALANCE VERIFIED: User has {balance/10**6} USDC.E")
    else:
        print("\nWARNING: No USDC.E detected in blockhain call.")
        
    if challenge:
        print("\nAGENT API VERIFIED: 402 Challenge successfully generated.")
    else:
        print("\nERROR: Agent API did not return a challenge.")
