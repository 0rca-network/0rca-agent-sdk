import time
import uuid
import requests
from typing import Dict, Any, Optional

class A2AProtocol:
    """
    Implements the Agent-to-Agent communication protocol.
    Schema:
     {
       "header": { "message_id", "from", "to", "timestamp" },
       "task": { "action", "payload" }
     }
    """
    
    def __init__(self, agent_id: str, registry):
        self.agent_id = agent_id
        self.registry = registry

    def create_message(self, to_agent_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "header": {
                "message_id": str(uuid.uuid4()),
                "from": self.agent_id,
                "to": to_agent_id,
                "timestamp": int(time.time() * 1000)
            },
            "task": {
                "action": action,
                "payload": payload
            }
        }

    def send_message(self, to_agent_id: str, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends a message to another agent via HTTP.
        """
        target = self.registry.get_agent(to_agent_id)
        if not target:
            raise ValueError(f"Agent {to_agent_id} not found in registry")
        
        msg = self.create_message(to_agent_id, action, payload)
        
        try:
            # Assuming endpoint accepts POST with the message schema
            # We look for /a2a/receive or just the root endpoint depending on convention.
            # Here we append /a2a/receive if not explicit? Let's assume endpoint is base URL.
            url = f"{target.endpoint.rstrip('/')}/a2a/receive"
            
            resp = requests.post(url, json=msg, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise RuntimeError(f"Failed to send A2A message to {to_agent_id}: {e}")

    def receive_message(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses and validates an incoming A2A message.
        Returns the parsed message if valid.
        """
        header = request_body.get("header")
        task = request_body.get("task")
        
        if not header or not task:
            raise ValueError("Invalid A2A message format: missing header or task")
        
        if header.get("to") != self.agent_id:
            # Maybe okay if broadcasting, but generally check destination
            pass 
            
        # Return logical structure for handler
        return request_body
