
import unittest
from unittest.mock import MagicMock, patch
from orca_agent_sdk.core.a2a import A2AProtocol, AgentRegistry, AgentInfo

class TestA2AProtocol(unittest.TestCase):
    def setUp(self):
        self.registry = AgentRegistry()
        # Mock local agent registration
        self.registry.register("agent2", "http://agent2.com", ["chat"], "Agent Two")
        self.a2a = A2AProtocol("agent1", self.registry)

    def test_create_message(self):
        msg = self.a2a.create_message("agent2", "chat", {"text": "hello"})
        self.assertEqual(msg['header']['from'], "agent1")
        self.assertEqual(msg['header']['to'], "agent2")
        self.assertEqual(msg['task']['action'], "chat")
        self.assertEqual(msg['task']['payload']['text'], "hello")

    @patch('requests.post')
    def test_send_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_post.return_value = mock_response

        resp = self.a2a.send_message("agent2", "chat", {"text": "hi"})
        self.assertEqual(resp, {"status": "ok"})
        
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "http://agent2.com/a2a/receive")
        self.assertIn("task", str(kwargs['json']) if 'task' in kwargs['json'] else "")
        self.assertEqual(kwargs['json']['header']['to'], "agent2")

    def test_send_message_unknown_agent(self):
        with self.assertRaises(ValueError):
            self.a2a.send_message("unknown_agent", "chat", {})

    def test_receive_message_valid(self):
        msg = {
            "header": {"from": "agent2", "to": "agent1"},
            "task": {"action": "chat", "payload": {}}
        }
        received = self.a2a.receive_message(msg)
        self.assertEqual(received, msg)

    def test_receive_message_invalid(self):
        with self.assertRaises(ValueError):
            self.a2a.receive_message({})

if __name__ == '__main__':
    unittest.main()
