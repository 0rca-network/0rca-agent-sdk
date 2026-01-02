import json
import base64
from typing import Dict, Any

class X402:
    """
    Minimal implementation of x402 utilities for encoding/decoding payment tokens.
    """
    
    def encode_payment_required(self, data: Dict[str, Any]) -> str:
        """
        Encodes payment requirements into a base64 token string.
        """
        json_str = json.dumps(data)
        return base64.b64encode(json_str.encode("utf-8")).decode("utf-8")

    def decode_payment(self, token: str) -> Dict[str, Any]:
        """
        Decodes a base64 payment token into a dictionary.
        """
        try:
            json_str = base64.b64decode(token).decode("utf-8")
            return json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Invalid x402 token: {e}")
