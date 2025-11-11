from orca_agent_sdk import AgentConfig, AgentServer

def handle_task(job_input: str) -> str:
    # Your agent's core logic here
    return f"Processed: {job_input}"

if __name__ == "__main__":
    config = AgentConfig(
        agent_id="my-agent-id",
        receiver_address="YOUR_ALGO_ADDRESS",
        price_microalgos=1_000_000,
        agent_token="28419644f65d92acffbc663a46de10ae41caf8bafd58e686c6f5461ab4256b37",
        remote_server_url="http://localhost:3000/api/agent/access"
    )

    AgentServer(config=config, handler=handle_task).run()