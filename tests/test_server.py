
import unittest
import json
import os
from unittest.mock import MagicMock, patch
from orca_agent_sdk.server import AgentServer
from orca_agent_sdk.config import AgentConfig

class TestAgentServer(unittest.TestCase):
    def setUp(self):
        self.config = AgentConfig(
            agent_id="test_agent",
            price="0.1",
            wallet_address="0x123",
            db_path="test_agent.db",
            identity_wallet_path="test_identity.json",
            ai_backend="crewai" # Will be mocked
        )
        
        # Mock dependencies
        self.mock_backend = MagicMock()
        self.mock_backend.handle_prompt.return_value = "Mock Response"
        
        # Patching inside setUp to ensure we catch where they are instantiated
        self.patcher1 = patch('orca_agent_sdk.server.AgentServer._load_backend', return_value=self.mock_backend)
        self.patcher2 = patch('orca_agent_sdk.server.init_db')
        self.patcher3 = patch('orca_agent_sdk.server.AgentWalletManager')
        self.patcher4 = patch('orca_agent_sdk.server.PaymentManager')
        self.patcher5 = patch('orca_agent_sdk.server.requests.post') # Mock facilitator checks
        self.patcher6 = patch('orca_agent_sdk.server.AgentRegistry')
        self.patcher7 = patch('orca_agent_sdk.server.log_request')
        self.patcher8 = patch('orca_agent_sdk.server.update_request_success')
        self.patcher9 = patch('orca_agent_sdk.server.update_request_failed')

        self.mock_load_backend = self.patcher1.start()
        self.mock_init_db = self.patcher2.start()
        self.mock_wallet_manager_cls = self.patcher3.start()
        self.mock_payment_manager_cls = self.patcher4.start()
        self.mock_requests_post = self.patcher5.start()
        self.mock_registry_cls = self.patcher6.start()
        self.mock_log_request = self.patcher7.start()
        self.mock_update_success = self.patcher8.start()
        self.mock_update_failed = self.patcher9.start()
        
        self.mock_log_request.return_value = 1 # req_id
        
        # Mock Registry
        self.mock_registry = self.mock_registry_cls.return_value
        self.mock_registry.on_chain = MagicMock()
        self.mock_registry.on_chain.get_agent_reputation.return_value = {"count": 10, "score": 100}
        self.mock_registry.on_chain.get_validation_status.return_value = {"count": 5, "avg": 90}
        
        # Mock wallet manager instance
        
        # Mock wallet manager instance
        self.mock_wallet_manager = self.mock_wallet_manager_cls.return_value
        self.mock_wallet_manager.address = "0xAgent"
        self.mock_wallet_manager._private_key = "key"

        # Mock Payment Manager instance
        self.mock_payment_manager = self.mock_payment_manager_cls.return_value
        self.mock_payment_manager.build_requirements.return_value = [{"mock": "req"}]
        self.mock_payment_manager.encode_challenge.return_value = "mock_challenge_token"
        self.mock_payment_manager.decode_payment.return_value = {"mock": "payment"}
        self.mock_payment_manager.verify_signature.return_value = True

        self.server = AgentServer(self.config, lambda x: x)
        self.app = self.server.app.test_client()

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()
        self.patcher4.stop()
        self.patcher5.stop()
        self.patcher6.stop()
        self.patcher7.stop()
        self.patcher8.stop()
        self.patcher9.stop()

    def test_health(self):
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"0rca Agent SDK", resp.data)

    def test_status(self):
        resp = self.app.get('/status')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['agent_id'], "test_agent")

    def test_agent_no_payment(self):
        # Should return 402 if no payment provided
        resp = self.app.post('/agent', json={"prompt": "hello", "taskId": "0x123"})
        self.assertEqual(resp.status_code, 402)
        self.assertIn("PAYMENT-REQUIRED", resp.headers)

    def test_agent_with_test_bypass(self):
        resp = self.app.post('/agent', json={"prompt": "hello", "taskId": "0x123"}, headers={"X-TEST-BYPASS": "true"})
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['result'], "Mock Response")

    def test_agent_with_valid_payment(self):
        # Mock facilitator verification response
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"valid": True}
        self.mock_requests_post.return_value = mock_resp
        
        resp = self.app.post('/agent', 
                             json={"prompt": "hello", "taskId": "0x123"}, 
                             headers={"X-PAYMENT": "valid_payment_token"})
        if resp.status_code != 200:
             print(f"DEBUG ERROR: {resp.data}")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['result'], "Mock Response")

    # def test_a2a_receive(self):
    #     # A2A receive calls backend
    #     msg = {
    #         "header": {"from": "other", "timestamp": 123},
    #         "task": {"action": "chat", "payload": {"prompt": "foo"}}
    #     }
    #     resp = self.app.post('/a2a/receive', json=msg)
    #     self.assertEqual(resp.status_code, 200)
    #     data = json.loads(resp.data)
    #     self.assertEqual(data['task']['payload']['result'], "Mock Response")

if __name__ == '__main__':
    unittest.main()
