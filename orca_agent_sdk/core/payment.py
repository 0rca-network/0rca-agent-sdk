from typing import List, Dict, Any
from ..config import AgentConfig
from .x402 import X402

class PaymentManager:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.x402 = X402()

    def build_requirements(self) -> List[Dict[str, Any]]:
        return [{
            "scheme": "exact",
            "network": self.config.chain_caip,
            "token": self.config.token_address,
            "resource": "/agent",
            "maxAmountRequired": self.config.price,
            "beneficiary": self.config.wallet_address
        }]

    def encode_challenge(self, accepts: List[Dict[str, Any]]) -> str:
        return self.x402.encode_payment_required({"accepts": accepts})

    def decode_payment(self, token: str):
        return self.x402.decode_payment(token)

    def verify_signature(self, payment_obj: Dict[str, Any]) -> bool:
        """
        Locally verify the signature of the x402 challenge.
        Used for local development when facilitator is not available.
        """
        try:
            from eth_account import Account
            from eth_account.messages import encode_defunct
            
            challenge = payment_obj.get("challenge")
            signature = payment_obj.get("signature")
            address = payment_obj.get("address")
            
            if not challenge or not signature or not address:
                return False
                
            message = encode_defunct(text=challenge)
            recovered_addr = Account.recover_message(message, signature=signature)
            
            return recovered_addr.lower() == address.lower()
        except Exception:
            return False
