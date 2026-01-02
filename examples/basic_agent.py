from orca_agent_sdk.config import AgentConfig
from orca_agent_sdk.server import AgentServer

# 1. Configure the Agent
config = AgentConfig(
    agent_id="my-first-agent",
    wallet_address="0xYourWalletAddressHere...",  # Replace with real address
    price="0.25",           # 0.25 tokens
    token_address="devUSDC.e", # Cronos Testnet USDC (or address)
    chain_caip="eip155:84531", # Cronos Testnet
    db_path="my_agent.db"
)

# 2. Define the Agent Logic
def my_agent_handler(prompt: str) -> str:
    print(f"Received prompt: {prompt}")
    # In a real agent, you would call an LLM here
    return f"I processed your request: '{prompt}'. That will be 0.25 USDC, thanks!"

# 3. Run the Server
if __name__ == "__main__":
    print("Starting Agent Server on port 8000...")
    server = AgentServer(config, my_agent_handler)
    server.run(port=8000)
