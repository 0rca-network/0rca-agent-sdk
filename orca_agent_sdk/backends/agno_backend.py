from typing import Callable
from ..config import AgentConfig
from .base import AbstractAgentBackend

class AgnoBackend(AbstractAgentBackend):
    """
    Backend for Agno agent runtime.
    """
    
    def initialize(self, config: AgentConfig, handler: Callable[[str], str]) -> None:
        self.handler = handler
        # Initialize Agno runtime here if needed
        # self.agent = Agent(...) 

    def handle_prompt(self, prompt: str) -> str:
        # Pass to Agno agent
        # response = self.agent.run(prompt)
        # return response.content
        
        # Fallback to user handler for SDK wrapper compliance
        return self.handler(prompt)
