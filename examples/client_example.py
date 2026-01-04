
import os
import json
import base64
import requests
import time
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

# --- CONFIGURATION ---
AGENT_URL = "http://localhost:8000/agent"
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80") # Default Anvil key

# Chain Config
RPC_URL = "https://evm-t3.cronos.org"
USDC_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"

# Minimal ERC20 ABI
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    }
]

def get_usdc_balance(address: str, w3: Web3) -> float:
    contract = w3.eth.contract(address=USDC_ADDRESS, abi=ERC20_ABI)
    balance = contract.functions.balanceOf(address).call()
    decimals = contract.functions.decimals().call()
    return balance / (10 ** decimals)

def get_signatures(challenge_token: str, private_key: str):
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = Account.from_key(private_key)
    
    # 1. Parse Challenge to get price and beneficiary
    challenge_data = json.loads(base64.b64decode(challenge_token).decode("utf-8"))
    accepts = challenge_data.get("accepts", [{}])[0]
    
    # Default to user address if no beneficiary (should not happen in real paid usage)
    beneficiary = accepts.get("beneficiary") or account.address
    to_address = Web3.to_checksum_address(beneficiary)
    
    # Amount needed (parse from string)
    amount_str = accepts.get("maxAmountRequired", "0")
    value = int(float(amount_str) * 10**6) # USDC is 6 decimals
    
    print(f"💳 Authorizing Payment: {amount_str} USDC -> {to_address}...")

    # USDC.e Domain on Cronos Testnet
    domain = {
        "name": "Bridged USDC (Stargate)",
        "version": "1",
        "chainId": 338,
        "verifyingContract": Web3.to_checksum_address(USDC_ADDRESS)
    }
    
    nonce = Web3.to_hex(Web3.keccak(text=str(time.time())))
    valid_before = int(time.time()) + 3600
    
    # 2. SIGN EIP-3009 (For On-Chain Transfer)
    types = {
        "TransferWithAuthorization": [
            {"name": "from", "type": "address"},
            {"name": "to", "type": "address"},
            {"name": "value", "type": "uint256"},
            {"name": "validAfter", "type": "uint256"},
            {"name": "validBefore", "type": "uint256"},
            {"name": "nonce", "type": "bytes32"}
        ]
    }
    msg_3009 = {
        "from": account.address,
        "to": to_address,
        "value": value,
        "validAfter": 0,
        "validBefore": valid_before,
        "nonce": nonce
    }
    signed_3009 = account.sign_typed_data(domain, types, msg_3009)

    # 3. Construct EIP-712 Signature (Concatenate r, s, v) -> 65 bytes
    # sign_typed_data returns separate v, r, s
    
    # EIP-712 signatures for ecrecover usually require v to be 27 or 28.
    # eth_account matches this but let's be explicit and construct the packed hex.
    v = signed_3009.v
    if v < 27:
        v += 27
        
    signature_bytes = signed_3009.r.to_bytes(32, 'big') + \
                      signed_3009.s.to_bytes(32, 'big') + \
                      v.to_bytes(1, 'big')
    signature_hex = "0x" + signature_bytes.hex()

    # Construct Payload Matching Facilitator Spec
    payload = {
         "from": account.address,
         "to": to_address,
         "value": str(value), # String format for large ints
         "validAfter": 0,
         "validBefore": valid_before,
         "nonce": nonce,
         "signature": signature_hex, # The authorization signature (packed r+s+v)
         "asset": USDC_ADDRESS
    }

    # Wrap in X402 Envelope
    return {
        "x402Version": 1,
        "scheme": "exact",
        "network": "cronos-testnet",
        "payload": payload
    }

def main():
    # Setup Web3
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    account = Account.from_key(PRIVATE_KEY)
    print(f"User Address: {account.address}")
    
    # Check Initial Balance
    print("Checking initial balance...")
    try:
        start_balance = get_usdc_balance(account.address, w3)
        print(f"💰 Initial USDC Balance: {start_balance}")
    except Exception as e:
        print(f"⚠️ Could not fetch balance: {e}")
        start_balance = 0

    if start_balance == 0:
        print("⚠️ WARNING: Balance is 0. Payment will fail on-chain, but server might accept for testing if strict mode is off.")

    prompt = "Tell me a joke about blockchain."
    print(f"\nRequesting: {prompt}")
    
    # 1. Initial Request (Expect 402)
    resp = requests.post(AGENT_URL, json={"prompt": prompt})
    
    if resp.status_code == 200:
        print("Success (Free):", resp.json())
        return

    if resp.status_code == 402:
        print("Payment Required (402)")
        challenge = resp.headers.get("PAYMENT-REQUIRED")
        if not challenge:
            print("Error: No challenge header found.")
            return
            
        print(f"Challenge received: {challenge[:20]}...")
        
        # 2. Sign Payment
        print("Signing payment...")
        try:
            payment_obj = get_signatures(challenge, PRIVATE_KEY)
            
            # Encode as base64
            payment_token = base64.b64encode(json.dumps(payment_obj).encode("utf-8")).decode("utf-8")
        except Exception as e:
            print(f"Error signing: {e}")
            return
        
        # 3. Retry with Payment
        print("Retrying with X-PAYMENT header...")
        resp2 = requests.post(
            AGENT_URL, 
            json={"prompt": prompt},
            headers={"X-PAYMENT": payment_token}
        )
        
        if resp2.status_code == 200:
            print("Success (Paid):", resp2.json())
            
            # Check Final Balance
            print("\nChecking final balance...")
            time.sleep(2) 
            
            try:
                end_balance = get_usdc_balance(account.address, w3)
                print(f"💰 Final USDC Balance: {end_balance}")
                diff = start_balance - end_balance
                if diff > 0:
                    print(f"📉 Cost incurred: {diff} USDC")
                else:
                    print("⚠️ No balance change detected. Settlement might be pending or facilitator failed silently.")
            except Exception as e:
                print(f"⚠️ Could not fetch balance: {e}")

        else:
            print(f"Failed ({resp2.status_code}):", resp2.text)
    else:
        print(f"Error ({resp.status_code}):", resp.text)

if __name__ == "__main__":
    main()
