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

from .registries import RegistryManager

class AgentRegistry:
    def __init__(self):
        self._local_agents: Dict[str, AgentInfo] = {}
        self.on_chain = RegistryManager()

    def register(self, agent_id: str, endpoint: str, capabilities: list[str] = None, name: str = ""):
        self._local_agents[agent_id] = AgentInfo(
            agent_id=agent_id,
            endpoint=endpoint,
            capabilities=capabilities or [],
            name=name
        )

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        # 1. Check local cache
        if agent_id in self._local_agents:
            return self._local_agents[agent_id]
        
        # 2. Check on-chain (assume numeric string is ID)
        if agent_id.isdigit():
            on_chain_id = int(agent_id)
            endpoint = self.on_chain.get_agent_endpoint(on_chain_id)
            if endpoint:
                return AgentInfo(
                    agent_id=agent_id,
                    endpoint=endpoint,
                    capabilities=[],
                    name=f"On-Chain Agent {agent_id}"
                )
        
        return None

class A2AProtocol:
    def __init__(self, agent_id: str, registry: AgentRegistry):
        self.agent_id = agent_id
        self.registry = registry

    def create_message(self, to_agent_id: str, action: str, payload: Dict[str, Any], task_id: Optional[str] = None, sub_task_id: Optional[str] = None, max_budget: Optional[float] = None) -> Dict[str, Any]:
        msg_task = {
            "action": action,
            "payload": payload
        }
        if task_id:
            msg_task["taskId"] = task_id
        if sub_task_id:
            msg_task["subTaskId"] = sub_task_id
        if max_budget is not None:
            msg_task["maxBudget"] = max_budget

        return {
            "header": {
                "message_id": str(uuid.uuid4()),
                "from": self.agent_id,
                "to": to_agent_id,
                "timestamp": int(time.time() * 1000)
            },
            "task": msg_task
        }

    def send_message(self, to_agent_id: str, action: str, payload: Dict[str, Any], task_id: Optional[str] = None, sub_task_id: Optional[str] = None, max_budget: Optional[float] = None) -> Dict[str, Any]:
        target = self.registry.get_agent(to_agent_id)
        if not target:
            raise ValueError(f"Agent {to_agent_id} not found in registry")
        
        msg = self.create_message(to_agent_id, action, payload, task_id, sub_task_id, max_budget)
        
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
