from abc import ABC, abstractmethod
from typing import Callable, Any
from ..config import AgentConfig

class AbstractAgentBackend(ABC):
    """
    Interface for AI backends (CrewAI, Agno, Crypto.com, etc).
    """
    
    @abstractmethod
    def initialize(self, config: AgentConfig, handler: Callable[[str], str]) -> None:
        """
        Initialize the backend with config and the user's default handler.
        """
        pass

    @abstractmethod
    def handle_prompt(self, prompt: str) -> str:
        """
        Process a prompt and return the text response.
        """
        pass

    def shutdown(self) -> None:
        """
        Cleanup resources if needed.
        """
        pass
