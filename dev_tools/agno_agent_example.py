import os
from orca_agent_sdk import AgentConfig, AgentServer
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

# Ensure OpenRouter API key is set
if not os.getenv("OPENROUTER_API_KEY"):
    raise ValueError("OPENROUTER_API_KEY environment variable must be set")

# Initialize Agno agent with OpenRouter
agno_agent = Agent(
    model=OpenRouter(id="gpt-4o-mini"),
    markdown=True
)

def handle_task(job_input: str) -> str:
    """Process job input using Agno agent"""
    try:
        response = agno_agent.run(job_input)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        return f"Agent processing failed: {str(e)}"

if __name__ == "__main__":
    config = AgentConfig(
        agent_id="agno-powered-agent",
        receiver_address="YOUR_ALGO_ADDRESS",
        price_microalgos=1_000_000,
        agent_token="28419644f65d92acffbc663a46de10ae41caf8bafd58e686c6f5461ab4256b37",
        remote_server_url="http://localhost:3000/api/agent/access"
    )

    print("Starting Agno-powered Agent Server...")
    AgentServer(config=config, handler=handle_task).run()