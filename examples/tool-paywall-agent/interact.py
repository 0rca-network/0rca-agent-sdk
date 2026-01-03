import requests
import json
import base64
import time
from eth_account import Account
from eth_account.messages import encode_defunct

# --- CONFIG ---
URL = "http://localhost:8001/agent"
MNEMONIC = "dish public milk ramp capable venue poverty grain useless december hedgehog shuffle"
Account.enable_unaudited_hdwallet_features()
user = Account.from_mnemonic(MNEMONIC)

def sign_payment(challenge_b64):
    """Signs a payment for a specific challenge."""
    # Simplified signing for the demo
    msg = encode_defunct(text=challenge_b64)
    signed = user.sign_message(msg)
    
    payment_obj = {
        "challenge": challenge_b64,
        "signature": signed.signature.hex(),
        "address": user.address
    }
    return base64.b64encode(json.dumps(payment_obj).encode()).decode()

def test_flow():
    # 1. Chat for free
    print("\n1. Sending free chat prompt...")
    r1 = requests.post(URL, json={"prompt": "How are you today?"})
    print(f"Status: {r1.status_code}")
    print(f"Response: {r1.json().get('result')}")

    # 2. Try to trigger a tool
    print("\n2. Requesting a premium tool (say_hello)...")
    r2 = requests.post(URL, json={"prompt": "Please use the say_hello tool."})
    print(f"Status: {r2.status_code}")
    
    if r2.status_code == 402:
        challenge = r2.headers.get("PAYMENT-REQUIRED")
        print(f"💰 PAYWALL TRIGGERED for: {r2.json().get('message')}")
        
        # Decode challenge to see details
        challenge_data = json.loads(base64.b64decode(challenge).decode())
        reqs = challenge_data["accepts"][0]
        print(f"Resource: {reqs['resource']}")
        print(f"Amount: {reqs['maxAmountRequired']} USDC.e")
        
        # 3. Pay the tool and resubmit
        print("\n3. Signing payment for tool...")
        payment_token = sign_payment(challenge)
        
        print("Resubmitting with payment...")
        # Note: In real life, we don't need bypass here if using signature verification
        # But for this demo, we use the local signature check in the server
        headers = {"X-PAYMENT": payment_token}
        r3 = requests.post(URL, json={"prompt": "Please use the say_hello tool."}, headers=headers)
        
        print(f"Status: {r3.status_code}")
        print(f"Response: {r3.json().get('result')}")

if __name__ == "__main__":
    test_flow()
