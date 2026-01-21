from typing import Callable, List, Optional, Dict, Any
import os
import logging
from ..config import AgentConfig
from .base import AbstractAgentBackend

try:
    from crewai import Agent, Task, Crew, Process, LLM
    from crewai.mcp import MCPServerStdio, MCPServerHTTP, MCPServerSSE
    HAS_CREWAI = True
except ImportError:
    HAS_CREWAI = False

class CrewAIBackend(AbstractAgentBackend):
    """
    Backend adapter for CrewAI with MCP tool support.
    """
    
    def initialize(self, config: AgentConfig, handler: Optional[Callable[[str], str]] = None) -> None:
        self.config = config
        if not HAS_CREWAI:
            logging.error("crewai not installed. Please install it with 'pip install crewai'")
            return

        # LLM Configuration
        provider_key = self.config.backend_options.get("provider_api_key")
        if provider_key:
            # Traditional env var setup for LiteLLM
            os.environ["GOOGLE_API_KEY"] = provider_key
        
        model_name = self.config.backend_options.get("model", "gemini/gemini-2.0-flash")
        
        # Create LLM object
        self.llm = LLM(
            model=model_name,
            api_key=provider_key,
            temperature=self.config.backend_options.get("temperature", 0.7)
        )
        
        # Parse MCPs from backend_options
        self.mcps_config = self.config.backend_options.get("mcps", [])
        self.mcps = []
        for m in self.mcps_config:
            if isinstance(m, str):
                self.mcps.append(m)
            elif isinstance(m, dict):
                m_type = m.get("type", "http").lower()
                if m_type == "stdio":
                    self.mcps.append(MCPServerStdio(
                        command=m.get("command"),
                        args=m.get("args", []),
                        env=m.get("env", {})
                    ))
                elif m_type == "http":
                    self.mcps.append(MCPServerHTTP(
                        url=m.get("url"),
                        headers=m.get("headers", {})
                    ))
                elif m_type == "sse":
                    self.mcps.append(MCPServerSSE(
                        url=m.get("url"),
                        headers=m.get("headers", {})
                    ))

        # Resolve native tools (support instances or string names)
        raw_native_tools = self.config.backend_options.get("native_tools", [])
        self.native_tools = []
        for t in raw_native_tools:
            if isinstance(t, str):
                resolved = self._resolve_tool_by_name(t)
                if resolved:
                    self.native_tools.append(resolved)
            else:
                # Assume it's already a tool instance
                self.native_tools.append(t)

        # Create the CrewAI Agent
        self.crew_agent = Agent(
            role=self.config.backend_options.get("role", "Sovereign AI Agent"),
            goal=self.config.backend_options.get("goal", "Execute tasks autonomously and monetarily."),
            backstory=self.config.backend_options.get("backstory", "An expert agent operating on the Cronos network with access to specialized tools."),
            llm=self.llm,
            tools=self.native_tools,
            mcps=self.mcps,
            verbose=True,
            allow_delegation=False
        )

    def _resolve_tool_by_name(self, name: str) -> Any:
        """
        Dynamically resolve and instantiate CrewAI tools by name.
        """
        try:
            # Import on demand to avoid requiring crewai_tools if not used
            import crewai_tools
            
            # Map of common tool names to their classes in crewai_tools
            tools_map = {
                "DirectoryReadTool": "DirectoryReadTool",
                "FileReadTool": "FileReadTool",
                "SerperDevTool": "SerperDevTool",
                "WebsiteSearchTool": "WebsiteSearchTool",
                "CodeInterpreterTool": "CodeInterpreterTool",
                "GithubSearchTool": "GithubSearchTool",
                "TXTSearchTool": "TXTSearchTool",
                "JSONSearchTool": "JSONSearchTool",
                "PDFSearchTool": "PDFSearchTool",
                "ScrapeWebsiteTool": "ScrapeWebsiteTool",
                "BrowserbaseLoadTool": "BrowserbaseLoadTool",
                "CodeDocsSearchTool": "CodeDocsSearchTool",
                "CSVSearchTool": "CSVSearchTool",
                "DirectorySearchTool": "DirectorySearchTool",
                "DOCXSearchTool": "DOCXSearchTool",
                "EXASearchTool": "EXASearchTool",
                "FirecrawlSearchTool": "FirecrawlSearchTool",
                "MDXSearchTool": "MDXSearchTool",
                "PGSearchTool": "PGSearchTool",
                "XMLSearchTool": "XMLSearchTool",
                "YoutubeChannelSearchTool": "YoutubeChannelSearchTool",
                "ApifyActorsTool": "ApifyActorsTool",
                "VisionTool": "VisionTool",
                "RagTool": "RagTool",
                "YoutubeVideoSearchTool": "YoutubeVideoSearchTool"
            }
            
            if name in tools_map:
                class_name = tools_map[name]
                tool_class = getattr(crewai_tools, class_name)
                # Instantiate with default settings
                return tool_class()
            
            return None
        except Exception as e:
            logging.warning(f"Could not resolve tool '{name}': {e}")
            return None

    def list_tools(self) -> List[str]:
        """
        List available tools from the initialized agent.
        Since CrewAI wraps MCP tools, we try to inspect the agent's tools.
        """
        if not self.crew_agent or not self.crew_agent.tools:
            return []
        
        return [tool.name for tool in self.crew_agent.tools]

    def handle_prompt(self, prompt: str) -> str:
        if not HAS_CREWAI:
            return "Error: crewai not installed."

        # Create a single task for the prompt
        task = Task(
            description=prompt,
            agent=self.crew_agent,
            expected_output="A detailed response to the user's request based on tool usage and reasoning."
        )

        # Create a crew and execute
        crew = Crew(
            agents=[self.crew_agent],
            tasks=[task],
            process=Process.sequential
        )
        result = crew.kickoff()
        return str(result)
