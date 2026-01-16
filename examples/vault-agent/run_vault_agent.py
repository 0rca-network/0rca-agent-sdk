import os
from dotenv import load_dotenv
from orca_agent_sdk.agent import OrcaAgent

# 1. Load configuration (Vault Address, etc.)
load_dotenv()

def main():
    if not os.getenv("GEMINI_API_KEY") and not os.getenv("GOOGLE_API_KEY"):
        print("Error: GEMINI_API_KEY or GOOGLE_API_KEY not found.")
        print("Please set it in your environment: $env:GEMINI_API_KEY='your_key'")
        return

    # 2. Initialize the Sovereign Agent
    agent = OrcaAgent(
        name="SecurityAnalyst-001",
        model="gemini/gemini-2.0-flash",
        system_prompt="You are a sovereign security analyst. You earn USDC into your own private vault.",
        price="0.1", # Each request costs 0.1 USDC from the task budget
    )

    print(f"Agent initialized with Vault: {agent.vault_address}")
    print(f"Current Vault Balance: {agent.get_earnings_balance()} USDC")

    # 3. Start the Server
    # It will automatically handle x402 and Task spending
    agent.run(port=8000)

if __name__ == "__main__":
    main()
