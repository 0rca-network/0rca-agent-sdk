from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class AgentInfo:
    agent_id: str
    endpoint: str
    capabilities: list[str]
    name: str

class AgentRegistry:
    """
    Simple in-memory registry for A2A. 
    In production, this would be backed by a database or on-chain registry.
    """
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

    def list_agents(self) -> list[AgentInfo]:
        return list(self._agents.values())
