# Moving the logic previously in orca_agent_sdk/a2a to core/a2a.py 
# for checking implementation requirements (single file requested in prompt vs existing folder),
# but sticking to cleaner architecture: Re-exporting or moving classes here.

import time
import uuid
import requests
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentInfo:
    agent_id: str
    endpoint: str
    capabilities: list[str]
    name: str

class AgentRegistry:
    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}

    def register(self, agent_id: str, endpoint: str, capabilities: list[str] = None, name: str = ""):
        self._agents[agent_id] = AgentInfo(
            agent_id=agent_id,
            endpoint=endpoint,
            capabilities=capabilities or [],
            name=name
        )

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        return self._agents.get(agent_id)

class A2AProtocol:
    def __init__(self, agent_id: str, registry: AgentRegistry):
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
        target = self.registry.get_agent(to_agent_id)
        if not target:
            raise ValueError(f"Agent {to_agent_id} not found in registry")
        
        msg = self.create_message(to_agent_id, action, payload)
        
        try:
            url = f"{target.endpoint.rstrip('/')}/a2a/receive"
            resp = requests.post(url, json=msg, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise RuntimeError(f"Failed to send A2A message to {to_agent_id}: {e}")

    def receive_message(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        header = request_body.get("header")
        task = request_body.get("task")
        if not header or not task:
            raise ValueError("Invalid A2A message")
        return request_body
