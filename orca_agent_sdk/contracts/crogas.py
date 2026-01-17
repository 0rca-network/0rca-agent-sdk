import requests
import json
import time
import base64
import os
from eth_account import Account
from eth_account.messages import encode_typed_data

class CroGasClient:
    def __init__(self, api_url: str, private_key: str, chain_id: int, usdc_address: str):
        self.api_url = api_url.rstrip('/')
        self.private_key = private_key
        self.account = Account.from_key(private_key)
        self.chain_id = chain_id
        self.usdc_address = usdc_address
        self.domain = None
        self.types = None

    def _get_meta_domain(self):
        if not self.domain:
            response = requests.get(f"{self.api_url}/meta/domain")
            response.raise_for_status()
            data = response.json()
            self.domain = data['domain']
            self.types = data['types']
        return self.domain, self.types

    def _get_nonce(self):
        response = requests.get(f"{self.api_url}/meta/nonce/{self.account.address}")
        response.raise_for_status()
        return response.json()['nonce']

    def execute(self, to: str, data: str = "0x", value: int = 0, gas_limit: int = 200000):
        """
        Executes a transaction via the CroGas relayer.
        Uses 2-step process (handshake for 402, then payment).
        """
        nonce = self._get_nonce()
        deadline = int(time.time()) + 3600
        
        request = {
            "from": self.account.address,
            "to": to,
            "value": int(value),
            "gas": int(gas_limit),
            "nonce": int(nonce),
            "deadline": int(deadline),
            "data": bytes.fromhex(data[2:]) if data.startswith("0x") else bytes.fromhex(data)
        }

        domain, types = self._get_meta_domain()
        
        # EIP-712 formatted request
        signable_data = {
            "types": {
                "EIP712Domain": [
                    {"name": "name", "type": "string"},
                    {"name": "version", "type": "string"},
                    {"name": "chainId", "type": "uint256"},
                    {"name": "verifyingContract", "type": "address"}
                ],
                "ForwardRequest": types["ForwardRequest"]
            },
            "primaryType": "ForwardRequest",
            "domain": domain,
            "message": request
        }
        
        signature = Account.sign_typed_data(self.private_key, full_message=signable_data).signature.hex()

        # Initial relay to get 402
        relay_payload = {
            "request": {
                "from": request["from"],
                "to": request["to"],
                "value": str(request["value"]),
                "gas": str(request["gas"]),
                "nonce": str(request["nonce"]),
                "deadline": str(request["deadline"]),
                "data": "0x" + request["data"].hex()
            },
            "signature": "0x" + signature if not signature.startswith("0x") else signature
        }
        
        print(f"[CroGas] Requesting relay for {to} (from={self.account.address})...", flush=True)
        response = requests.post(f"{self.api_url}/meta/relay", json=relay_payload)
        
        if response.status_code == 402:
            print(f"[CroGas] 402 Payment Required. Handshaking...", flush=True)
            x402_data = response.json()
            print(f"[CroGas] Relayer accepts: {json.dumps(x402_data['x402']['accepts'], indent=2)}", flush=True)
            payment_info = x402_data['x402']['accepts'][0]
            
            # The asset relayer actually wants
            requested_asset = payment_info['asset']
            
            # Sign USDC Auth (TransferWithAuthorization)
            usdc_nonce = os.urandom(32)
            usdc_auth = {
                "from": self.account.address,
                "to": payment_info['payTo'],
                "value": int(payment_info['maxAmountRequired']),
                "validAfter": int(time.time()) - 60,
                "validBefore": int(time.time()) + 3600,
                "nonce": usdc_nonce
            }
            
            # Dynamic token name detection (fallback to common names)
            token_name = "Test USDC"
            if requested_asset.lower() == "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0".lower():
                token_name = "Bridged USDC (Stargate)"
            
            usdc_domain = {
                "name": token_name,
                "version": "1",
                "chainId": self.chain_id,
                "verifyingContract": requested_asset
            }
            
            usdc_signable = {
                "types": {
                    "EIP712Domain": [
                        {"name": "name", "type": "string"},
                        {"name": "version", "type": "string"},
                        {"name": "chainId", "type": "uint256"},
                        {"name": "verifyingContract", "type": "address"}
                    ],
                    "TransferWithAuthorization": [
                        {"name": "from", "type": "address"},
                        {"name": "to", "type": "address"},
                        {"name": "value", "type": "uint256"},
                        {"name": "validAfter", "type": "uint256"},
                        {"name": "validBefore", "type": "uint256"},
                        {"name": "nonce", "type": "bytes32"}
                    ]
                },
                "primaryType": "TransferWithAuthorization",
                "domain": usdc_domain,
                "message": usdc_auth
            }
            
            usdc_sig = Account.sign_typed_data(self.private_key, full_message=usdc_signable).signature.hex()
            if not usdc_sig.startswith("0x"): usdc_sig = "0x" + usdc_sig
            
            # Prepare clean JSON for header (no bytes)
            payment_header_data = {
                "version": 1,
                "scheme": "exact",
                "network": payment_info['network'],
                "payload": {
                    "signature": usdc_sig, 
                    "authorization": {
                        "from": usdc_auth["from"],
                        "to": usdc_auth["to"],
                        "value": str(usdc_auth["value"]),
                        "validAfter": str(usdc_auth["validAfter"]),
                        "validBefore": str(usdc_auth["validBefore"]),
                        "nonce": "0x" + usdc_auth["nonce"].hex()
                    }
                }
            }
            
            payment_header = base64.b64encode(json.dumps(payment_header_data).encode()).decode()
            
            print(f"[CroGas] Submitting with USDC. Payload asset={requested_asset}, amount={usdc_auth['value']}", flush=True)
            response = requests.post(
                f"{self.api_url}/meta/relay", 
                json=relay_payload,
                headers={"X-Payment": payment_header}
            )

        if not response.ok:
            print(f"[CroGas] Relay error {response.status_code}: {response.text}", flush=True)
        response.raise_for_status()
        return response.json()
