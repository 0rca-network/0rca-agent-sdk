import requests
import json
import os
import sys
import time
import base64
from eth_account import Account
from eth_account.messages import encode_defunct
from web3 import Web3

# Ensure we're in the right directory or have dependencies
try:
    from eth_account import Account
except ImportError:
    print("Please install eth_account: pip install eth-account")
    sys.exit(1)

URL = "http://localhost:8000/agent"
# Default Anvil Key or User Provided
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80")

# Cronos Testnet configuration
RPC_URL = "https://evm-t3.cronos.org"
USDC_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"

def get_eip3009_payload(challenge_token: str, private_key: str):
    """
    Constructs a full EIP-3009 payment payload that matches the Facilitator spec.
    """
    account = Account.from_key(private_key)
    
    # 1. Parse Challenge
    try:
        challenge_data = json.loads(base64.b64decode(challenge_token).decode("utf-8"))
        accepts = challenge_data.get("accepts", [{}])[0]
        
        beneficiary = accepts.get("beneficiary") or account.address
        to_address = Web3.to_checksum_address(beneficiary)
        amount_str = accepts.get("maxAmountRequired", "0")
        value = int(float(amount_str) * 10**6) # USDC 6 decimals
        
        token_address = accepts.get("token") or USDC_ADDRESS
        
    except Exception as e:
        print(f"Error parsing challenge: {e}")
        return None

    # 2. EIP-712 Domain
    domain = {
        "name": "Bridged USDC (Stargate)",
        "version": "1",
        "chainId": 338,
        "verifyingContract": Web3.to_checksum_address(token_address)
    }
    
    nonce = Web3.to_hex(Web3.keccak(text=str(time.time())))
    valid_before = int(time.time()) + 3600
    
    # 3. EIP-3009 Typed Data
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
    msg = {
        "from": account.address,
        "to": to_address,
        "value": value,
        "validAfter": 0,
        "validBefore": valid_before,
        "nonce": nonce
    }
    
    # 4. Sign
    signed = account.sign_typed_data(domain, types, msg)
    
    # 5. Pack Signature (v, r, s)
    v = signed.v
    if v < 27: v += 27
    signature_bytes = signed.r.to_bytes(32, 'big') + signed.s.to_bytes(32, 'big') + v.to_bytes(1, 'big')
    signature_hex = "0x" + signature_bytes.hex()
    
    # 6. Construct Facilitator-Compatible Payload
    payload = {
         "from": account.address,
         "to": to_address,
         "value": str(value), # String format required
         "validAfter": 0,
         "validBefore": valid_before,
         "nonce": nonce,
         "signature": signature_hex,
         "asset": token_address
    }
    
    # 7. Wrap in X402 Envelope
    envelope = {
        "x402Version": 1,
        "scheme": "exact",
        "network": "cronos-testnet",
        "payload": payload
    }
    
    return envelope

def main():
    account = Account.from_key(PRIVATE_KEY)
    print(f"User Address: {account.address}")
    
    query = "What is the price of Bitcoin?"
    print(f"Requesting: {query}")
    
    try:
        # 1. First Request
        response = requests.post(URL, json={"prompt": query})
        
        if response.status_code == 402:
            print("Payment Required (402)")
            
            # Extract challenge
            auth_header = response.headers.get("WWW-Authenticate") or response.headers.get("PAYMENT-REQUIRED")
            if not auth_header:
                print("Error: No challenge header found")
                return

            challenge = auth_header.replace("x402 ", "")
            print(f"Challenge received: {challenge[:20]}...")
            
            # 2. Sign Payment
            print("Signing EIP-3009 Payment...")
            payment_envelope = get_eip3009_payload(challenge, PRIVATE_KEY)
            
            if not payment_envelope:
                print("Failed to construct payment payload")
                return
                
            # Base64 encode the JSON envelope
            payment_token = base64.b64encode(json.dumps(payment_envelope).encode("utf-8")).decode("utf-8")
            
            # 3. Retry with Payment
            print(f"Retrying with x402 token...")
            headers = {
                "Authorization": f"x402 {payment_token}",
                "X-PAYMENT": payment_token 
            }
            
            paid_response = requests.post(URL, json={"prompt": query}, headers=headers)
            
            if paid_response.status_code == 200:
                print("\nSuccess!")
                print("Response:", paid_response.json())
            else:
                print(f"Failed ({paid_response.status_code}): {paid_response.text}")
                
        elif response.status_code == 200:
            print("Success (No payment required?):", response.json())
        else:
            print(f"Error ({response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"Connection error: {e}")

if __name__ == "__main__":
    main()
