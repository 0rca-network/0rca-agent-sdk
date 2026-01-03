import requests
import json
import time
import base64
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct

# --- CONFIG ---
AGENT_URL = "http://localhost:8000/agent"
RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"
ESCROW_ADDRESS = "0x86768D20Ad92d727c987fddD10d08aFA25B85E78"
AGENT_ID = 0
MNEMONIC = "dish public milk ramp capable venue poverty grain useless december hedgehog shuffle"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
Account.enable_unaudited_hdwallet_features()
user = Account.from_mnemonic(MNEMONIC) # User is also the Facilitator for this test

# Escrow ABI for creditAgent
ESCROW_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "agentId", "type": "uint256"},
            {"internalType": "uint256", "name": "amount", "type": "uint256"},
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "uint256", "name": "validAfter", "type": "uint256"},
            {"internalType": "uint256", "name": "validBefore", "type": "uint256"},
            {"internalType": "bytes32", "name": "nonce", "type": "bytes32"},
            {"internalType": "uint8", "name": "v", "type": "uint8"},
            {"internalType": "bytes32", "name": "r", "type": "bytes32"},
            {"internalType": "bytes32", "name": "s", "type": "bytes32"}
        ],
        "name": "creditAgent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

def sign_payment(challenge_token):
    domain = {
        "name": "Bridged USDC (Stargate)",
        "version": "1",
        "chainId": 338,
        "verifyingContract": Web3.to_checksum_address(USDC_E_ADDRESS)
    }
    nonce = Web3.to_hex(Web3.keccak(text=str(time.time())))
    valid_before = int(time.time()) + 3600
    value = 1 * 10**6 # 1 USDC.e

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
    message = {
        "from": user.address,
        "to": Web3.to_checksum_address(ESCROW_ADDRESS),
        "value": value,
        "validAfter": 0,
        "validBefore": valid_before,
        "nonce": nonce
    }
    signed_3009 = user.sign_typed_data(domain, types, message)
    
    # Signed identity for SDK check
    msg_defunct = encode_defunct(text=challenge_token)
    signed_identity = user.sign_message(msg_defunct)

    return {
        "challenge": challenge_token,
        "signature": signed_identity.signature.hex(),
        "address": user.address,
        "auth_details": {
            "from": user.address,
            "to": ESCROW_ADDRESS,
            "value": value,
            "validAfter": 0,
            "validBefore": valid_before,
            "nonce": nonce,
            "v": signed_3009.v,
            "r": Web3.to_hex(signed_3009.r),
            "s": Web3.to_hex(signed_3009.s)
        }
    }

def run_settlement(payment_obj):
    print("\n--- SIMULATING FACILITATOR SETTLEMENT ---")
    escrow = w3.eth.contract(address=ESCROW_ADDRESS, abi=ESCROW_ABI)
    auth = payment_obj["auth_details"]
    
    nonce = w3.eth.get_transaction_count(user.address)
    tx = escrow.functions.creditAgent(
        AGENT_ID,
        auth["value"],
        auth["from"],
        auth["validAfter"],
        auth["validBefore"],
        auth["nonce"],
        auth["v"],
        auth["r"],
        auth["s"]
    ).build_transaction({
        'from': user.address,
        'nonce': nonce,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 338
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, user.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Settlement TX Sent: {w3.to_hex(tx_hash)}")
    print("Waiting for on-chain credit...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    if receipt.status == 1:
        print("SUCCESS: Agent credited in Escrow!")
    else:
        print("FAILED: Transaction reverted!")
        # Try to find reason if possible (optional)


def interact():
    # 1. Get Challenge
    print("1. Requesting Challenge...")
    r1 = requests.post(AGENT_URL, json={"prompt": "Explain crypto in 5 words."})
    challenge = r1.headers.get("PAYMENT-REQUIRED")
    
    # 2. Sign Payment
    print("2. Signing Payment...")
    payment_obj = sign_payment(challenge)
    
    # 3. Settlement (Normally done by Facilitator backend, here we do it for demo)
    run_settlement(payment_obj)
    
    # 4. Final Interaction
    print("\n3. Interaction with Verification...")
    signed_b64 = base64.b64encode(json.dumps(payment_obj).encode("utf-8")).decode("utf-8")
    headers = {"X-PAYMENT": signed_b64}
    
    # We use a special bypass so the local server doesn't try calling a real facilitator verify
    # since we just did it manually.
    headers["X-TEST-BYPASS"] = "true" 
    
    r2 = requests.post(AGENT_URL, json={"prompt": "Explain crypto in 5 words."}, headers=headers)
    print("\n--- GEMINI RESPONSE ---")
    print(r2.json().get("result"))

if __name__ == "__main__":
    interact()
