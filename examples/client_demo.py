import requests
import json
import base64
from eth_account import Account
from eth_account.messages import encode_defunct

# Setup
AGENT_URL = "http://localhost:8000/agent"
PRIVATE_KEY = "0xfe9e93888f39b8ce56ef7f3027789a7b58d2494d195217e4c272614ea4e3bb46" 
SENDER_ADDRESS = "0xdF27Bde82EfD8c7C29C93b663dB464AdfD53cd80"

def run_interaction():
    prompt = "Tell me a joke about crypto."
    
    print(f"1. Sending initial request: '{prompt}'")
    resp = requests.post(AGENT_URL, json={"prompt": prompt})
    
    if resp.status_code == 200:
        print("Success (No payment required?):", resp.json())
        return

    if resp.status_code == 402:
        print("2. Received 402 Payment Required")
        challenge = resp.headers.get("PAYMENT-REQUIRED")
        
        if not challenge:
            print("Error: No PAYMENT-REQUIRED header found")
            return
            
        print(f"   Challenge: {challenge[:20]}...")
        
        # 3. Sign the challenge (EIP-191 Personal Sign)
        account = Account.from_key(PRIVATE_KEY)
        message = encode_defunct(text=challenge)
        signed_message = account.sign_message(message)
        
        # 4. Construct x402 Payment Token
        # Our mock server expects a base64-encoded JSON
        payment_data = {
            "challenge": challenge,
            "signature": signed_message.signature.hex(),
            "address": SENDER_ADDRESS
        }
        payment_token = base64.b64encode(json.dumps(payment_data).encode()).decode()
        
        print("3. Retrying with X-PAYMENT header...")
        headers = {"X-PAYMENT": payment_token}
        resp_retry = requests.post(AGENT_URL, json={"prompt": prompt}, headers=headers)
        
        if resp_retry.status_code == 200:
            print("\nResult from Agent:")
            print(resp_retry.json())
        else:
            print(f"\nFailed: {resp_retry.status_code}")
            print(resp_retry.text)

if __name__ == "__main__":
    try:
        run_interaction()
    except Exception as e:
        print(f"Error: {e}")
