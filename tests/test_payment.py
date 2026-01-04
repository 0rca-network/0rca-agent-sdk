
import unittest
from unittest.mock import MagicMock, patch
from orca_agent_sdk.core.payment import PaymentManager, ToolPaywallError
from orca_agent_sdk.config import AgentConfig

class TestPaymentManager(unittest.TestCase):
    def setUp(self):
        self.config = AgentConfig(
            agent_id="test_agent",
            price="0.1",
            wallet_address="0x123",
            tool_prices={"premium_tool": "0.5"}
        )
        self.payment_manager = PaymentManager(self.config)

    def test_build_requirements_default(self):
        reqs = self.payment_manager.build_requirements()
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]['maxAmountRequired'], "0.1")
        self.assertEqual(reqs[0]['resource'], "/agent")
        # AGENT_ESCROW constant takes precedence in current implementation
        from orca_agent_sdk.constants import AGENT_ESCROW
        self.assertEqual(reqs[0]['beneficiary'], AGENT_ESCROW)

    def test_build_requirements_tool(self):
        reqs = self.payment_manager.build_requirements(tool_name="premium_tool")
        self.assertEqual(len(reqs), 1)
        self.assertEqual(reqs[0]['maxAmountRequired'], "0.5")
        self.assertEqual(reqs[0]['resource'], "/tool/premium_tool")

    def test_encode_decode_payment(self):
        accepts = self.payment_manager.build_requirements()
        token = self.payment_manager.encode_challenge(accepts)
        decoded = self.payment_manager.decode_payment(token)
        self.assertEqual(decoded['accepts'], accepts)

    @patch('orca_agent_sdk.core.payment.PaymentManager.verify_signature')
    def test_check_tool_payment_valid(self, mock_verify):
        mock_verify.return_value = True
        
        # Create a fake payment token that matches the tool requirement
        accepts = self.payment_manager.build_requirements(tool_name="premium_tool")
        # Challenge needs to be embedded in the payment check?
        # In check_tool_payment:
        # payment_obj = decode(signed_b64)
        # challenge_b64 = payment_obj.get("challenge")
        # decode(challenge_b64) -> verify resource
        
        challenge_token = self.payment_manager.encode_challenge(accepts)
        payment_obj = {
            "challenge": challenge_token,
            "signature": "fake_sig",
            "address": "0xUser"
        }
        signed_b64 = self.payment_manager.x402.encode_payment_required(payment_obj) 
        
        # Should not raise
        self.payment_manager.check_tool_payment("premium_tool", signed_b64)

    @patch('orca_agent_sdk.core.payment.PaymentManager.verify_signature')
    def test_check_tool_payment_invalid_resource(self, mock_verify):
        mock_verify.return_value = True
        
        # Create a payment for the wrong resource (main agent instead of tool)
        accepts = self.payment_manager.build_requirements() # default agent resource
        challenge_token = self.payment_manager.encode_challenge(accepts)
        payment_obj = {
            "challenge": challenge_token,
            "signature": "fake_sig",
            "address": "0xUser"
        }
        # We must use x402 directly because encode_challenge wraps in {"accepts": ...}
        signed_b64 = self.payment_manager.x402.encode_payment_required(payment_obj)
        
        with self.assertRaises(ToolPaywallError):
            self.payment_manager.check_tool_payment("premium_tool", signed_b64)

    def test_check_tool_payment_no_payment(self):
        with self.assertRaises(ToolPaywallError):
            self.payment_manager.check_tool_payment("premium_tool", None)

if __name__ == '__main__':
    unittest.main()
