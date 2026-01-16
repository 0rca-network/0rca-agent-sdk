import os
from dotenv import load_dotenv
from orca_agent_sdk import OrcaAgent

load_dotenv()

def main():
    # Production-ready agent configuration
    # Environment variables (GEMINI_API_KEY, TASK_ESCROW, etc.) should be set in .env
    agent = OrcaAgent( 
        name="TaskMaster-001",
        model="gemini/gemini-2.0-flash",
        system_prompt="You are a helpful assistant that performs orchestrated tasks.",
        price="0.1" 
    )

    print(f"Starting {agent.name}...")
    agent.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
