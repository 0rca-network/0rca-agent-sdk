import requests
import json
import base64
from eth_account import Account
from eth_account.messages import encode_defunct

# Setup
AGENT_URL = "http://localhost:8000/agent"
PRIVATE_KEY = "0x..." # SET YOUR TEST PRIVATE KEY HERE
SENDER_ADDRESS = "0x..." # SET YOUR ADDRESS HERE

def run_interaction():
    prompt = "Tell me a joke about crypto."
    
    print(f"1. Sending initial request: '{prompt}'")
    resp = requests.post(AGENT_URL, json={"prompt": prompt})
    
    if resp.status_code == 200:
        print("Success (No payment required?):", resp.json())
        return

    if resp.status_code == 402:
        print("2. Received 402 Payment Required")
        req_headers = resp.headers
        challenge = req_headers.get("PAYMENT-REQUIRED")
        
        if not challenge:
            print("Error: No PAYMENT-REQUIRED header found")
            return
            
        print(f"   Challenge: {challenge[:20]}...")
        
        # In a real app, you would verify the 'accepts' field in resp.json() 
        # to know what you are signing for.
        
        if PRIVATE_KEY == "0x...":
            print("\n[!] Please set PRIVATE_KEY in client_demo.py to sign the payment.")
            return

        # 3. Sign the challenge
        # x402 challenge implies signing the challenge string (or EIP-712/formatted).
        # Standard x402 (Coinbase) usually treats the decoded challenge as a message to sign.
        # But wait, python-x402 protocol details matter here. 
        # The challenge is often a base64 encoded string.
        # Let's decode it to see what we are signing, usually it's used as the message.
        
        # Note: This is an illustrative client. x402 client implementation details 
        # depend on how the server encodes the challenge.
        # Our server uses `x402.encode_payment_required`.
        # The client library `x402` would typically handle `decode_payment_required`,
        # but here we manually do it for demonstration if we don't use the full lib.
        
        # Let's use the x402 lib if available to be cleaner, or manual.
        # Currently we just need to sign it.
        # For simplicity, assuming standard Personal Sign (EIP-191) on the raw challenge bytes?
        # OR usually x402 expects us to construct a specific payload.
        
        # Simplified Client Flow (Manual Signing):
        # 1. Decode base64 challenge
        # 2. Sign it
        # 3. Encode signature and metadata into X-PAYMENT
        
        # BUT, the `x402` library also helps us CREATE the payment token.
        # Since this client demo is Python, let's try to use `x402` lib if user has it, 
        # or mock it.
        
        from x402 import X402
        client_x402 = X402()
        
        # The library might expect a signer callback or we construct the payment manually.
        # Let's verify what `x402` library offers. 
        # Without full docs, I'll assume we construct a signed payload.
        
        # Based on typical flows: 
        # payment_token = client_x402.create_payment_token(challenge, signer_func)
        
        pass

if __name__ == "__main__":
    try:
        run_interaction()
    except Exception as e:
        print(f"Error: {e}")
