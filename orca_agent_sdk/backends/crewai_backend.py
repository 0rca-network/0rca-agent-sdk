from typing import Callable
from ..config import AgentConfig
from .base import AbstractAgentBackend

class CrewAIBackend(AbstractAgentBackend):
    """
    Default backend. 
    Currently acts as a direct wrapper for the user's simple handler function,
    simulating a single-agent "crew".
    """
    
    def initialize(self, config: AgentConfig, handler: Callable[[str], str]) -> None:
        self.handler = handler

    def handle_prompt(self, prompt: str) -> str:
        # In a full integration, this would spin up a CrewAI Agent -> Task -> Crew
        # For now, we respect the user's passed handler logic strictly.
        return self.handler(prompt)
