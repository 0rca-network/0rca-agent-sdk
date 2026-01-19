import requests
import json
import time
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
import base64

# --- CONFIGURATION ---
AGENT_URL = "http://localhost:8000/agent"
RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1"
MNEMONIC = "dish public milk ramp capable venue poverty grain useless december hedgehog shuffle"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
Account.enable_unaudited_hdwallet_features()
user = Account.from_mnemonic(MNEMONIC)

def get_signatures(challenge_token):
    # USDC.e Domain on Cronos Testnet
    domain = {
        "name": "USD Coin",
        "version": "1",
        "chainId": 338,
        "verifyingContract": Web3.to_checksum_address(USDC_E_ADDRESS)
    }
    
    challenge_data = json.loads(base64.b64decode(challenge_token).decode("utf-8"))
    accepts = challenge_data.get("accepts", [{}])[0]
    to_address = Web3.to_checksum_address(accepts.get("beneficiary", user.address))
    value = int(float(accepts.get("maxAmountRequired", "1.0")) * 10**6)
    
    nonce = Web3.to_hex(Web3.keccak(text=str(time.time())))
    valid_before = int(time.time()) + 3600
    
    # 1. SIGN EIP-3009 (For On-Chain Transfer)
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
        "from": user.address,
        "to": to_address,
        "value": value,
        "validAfter": 0,
        "validBefore": valid_before,
        "nonce": nonce
    }
    signed_3009 = user.sign_typed_data(domain, types, msg_3009)

    # 2. SIGN CHALLENGE STRING (For SDK Identity Check)
    msg_defunct = encode_defunct(text=challenge_token)
    signed_identity = user.sign_message(msg_defunct)
    
    return {
        "challenge": challenge_token,
        "signature": signed_identity.signature.hex(),
        "address": user.address,
        "auth_details": {
            "from": user.address,
            "to": to_address,
            "value": value,
            "validAfter": 0,
            "validBefore": valid_before,
            "nonce": nonce,
            "v": signed_3009.v,
            "r": Web3.to_hex(signed_3009.r),
            "s": Web3.to_hex(signed_3009.s)
        }
    }

def interact():
    print(f"Connecting to Agent as {user.address}...")
    
    r1 = requests.post(AGENT_URL, json={"prompt": "Explain Cronos in 10 words."})
    if r1.status_code != 402: return

    challenge_token = r1.headers.get("PAYMENT-REQUIRED")
    print("SUCCESS: Challenge Received.")
    
    print("Generating Dual Signatures (Identity + Payment Authorization)...")
    payment_obj = get_signatures(challenge_token)
    
    signed_b64 = base64.b64encode(json.dumps(payment_obj).encode("utf-8")).decode("utf-8")
    headers = {"X-PAYMENT": signed_b64}
    
    print("Submitting to Agent...")
    r2 = requests.post(AGENT_URL, json={"prompt": "Explain Cronos in 10 words."}, headers=headers)
    
    if r2.status_code == 200:
        print("\n--- RESPONSE FROM GEMINI ---")
        print(r2.json().get("result"))
        print("\n🎉 TRANSACTION SIGNED & SENT TO FACILITATOR!")
    else:
        print(f"Error {r2.status_code}: {r2.text}")

if __name__ == "__main__":
    interact()
