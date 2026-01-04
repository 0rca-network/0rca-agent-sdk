import os
import sys

# Ensure SDK is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from orca_agent_sdk.agent import OrcaAgent

def main():
    # 1. Define MCP Tools (Simple Configuration)
    # This matches the user's desire for easy integration
    mcp_tools = [
        {
            "type": "http",
            "url": "https://mcp.crypto.com/market-data/mcp",
        }
    ]

    # 2. Initialize Agent
    agent = OrcaAgent(
        name="CryptoMarketAgent",
        model="gemini/gemini-2.0-flash",
        system_prompt="You are a helpful crypto market analyst. Use the available tools to fetch data and answer questions.",
        tools=mcp_tools,
        credits_file="examples/2_mcp_agent/credits.json",
        price="0.1" # Base access price
    )

    # 3. List Tools (Demonstration)
    # Note: Requires backend initialization which happens on run, so this might be empty before run
    # For demo purposes, we trust the agent will discover them at runtime.
    print(f"Agent {agent.name} configured with tools: {[t['url'] for t in agent.tools]}")

    # 4. Run Server
    agent.run(port=8000)

if __name__ == "__main__":
    main()
