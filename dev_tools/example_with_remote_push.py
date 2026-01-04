import os
from orca_agent_sdk import AgentConfig, AgentServer
from agno.agent import Agent
from agno.models.openrouter import OpenRouter

# Initialize Agno agent
agno_agent = Agent(
    model=OpenRouter(id="gpt-4o-mini"),
    markdown=True
)

def handle_task(job_input: str) -> str:
    """Use Agno agent to process the job input"""
    try:
        response = agno_agent.run(job_input)
        return response.content if hasattr(response, 'content') else str(response)
    except Exception as e:
        return f"Error processing request: {str(e)}"

if __name__ == "__main__":
    config = AgentConfig(
        agent_id="my-agent-id",
        receiver_address="YOUR_ALGO_ADDRESS",
        price_microalgos=1_000_000,
        agent_token="28419644f65d92acffbc663a46de10ae41caf8bafd58e686c6f5461ab4256b37",
        remote_server_url="http://localhost:3000/api/agent/access"
    )

    AgentServer(config=config, handler=handle_task).run()