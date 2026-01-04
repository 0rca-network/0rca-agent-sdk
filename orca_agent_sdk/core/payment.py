from typing import List, Dict, Any, Optional
from ..config import AgentConfig
from ..constants import AGENT_ESCROW
from .x402 import X402

class ToolPaywallError(Exception):
    """Raised when a specific tool requires payment."""
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        super().__init__(f"Tool {tool_name} requires payment")

class PaymentManager:
    def __init__(self, config: AgentConfig):
        self.config = config
        self.x402 = X402()

    def build_requirements(self, tool_name: Optional[str] = None) -> List[Dict[str, Any]]:
        # Use Escrow Constant OR fallback to wallet_address if configured (but typically Escrow)
        beneficiary = AGENT_ESCROW
        if not beneficiary and self.config.wallet_address:
             beneficiary = self.config.wallet_address
        
        resource = "/agent"
        price = self.config.price
        
        if tool_name and tool_name in self.config.tool_prices:
            resource = f"/tool/{tool_name}"
            price = self.config.tool_prices[tool_name]
             
        return [{
            "scheme": "exact",
            "network": self.config.chain_caip,
            "token": self.config.token_address,
            "resource": resource,
            "maxAmountRequired": price,
            "beneficiary": beneficiary
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

    def check_tool_payment(self, tool_name: str, signed_b64: Optional[str]):
        """
        Validates if the provided payment token covers the specified tool.
        Raises ToolPaywallError if payment is missing or invalid for this tool.
        """
        if tool_name not in self.config.tool_prices:
            return  # Not paywalled
        
        if not signed_b64:
            raise ToolPaywallError(tool_name)
            
        try:
            payment_obj = self.decode_payment(signed_b64)
            # 1. Verify general signature
            if not self.verify_signature(payment_obj):
                raise ToolPaywallError(tool_name)
            
            # 2. Verify resource matching
            challenge_b64 = payment_obj.get("challenge")
            if challenge_b64:
                challenge_data = self.x402.decode_payment(challenge_b64)
                accepts = challenge_data.get("accepts", [])
                if accepts:
                    resource = accepts[0].get("resource")
                    # If this is a tool-specific paywall, we expect the specific resource
                    if resource != f"/tool/{tool_name}":
                         raise ToolPaywallError(tool_name)
        except ToolPaywallError:
            raise
        except Exception:
            raise ToolPaywallError(tool_name)

