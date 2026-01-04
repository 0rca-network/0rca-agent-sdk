import os
from orca_agent_sdk import AgentConfig, AgentServer

def main():
    # 1. Setup Configuration for Cronos Testnet
    config = AgentConfig(
        agent_id="cronos-gemini-agent",
        price="1.0",
        
        # We rely on SDK constants for Escrow & Tokens now!
        # wallet_address is optional (defaults to none, forcing escrow usage)
        
        # On-Chain Identity (ERC-8004)
        on_chain_id=0,

        # Cronos Testnet CAIP
        chain_caip="eip155:338",
        
        # Use CrewAI Backend with Gemini & MCP Tools
        ai_backend="crewai",
        
        # CrewAI Configuration
        backend_options={
            "model": "gemini/gemini-2.0-flash",
            "provider_api_key": "AIzaSyC3kaJXGa2RkK7pmlosHlVLeBqI5Z6vZYE",
            "role": "Financial Research Analyst",
            "goal": "Fetch real-time crypto prices and provide market insights.",
            "backstory": "You are a crypto expert with access to real-time tools via MCP.",
            "mcps": [
                # Example: Use a remote MCP for crypto data if available, 
                # or a local one. For this demo, let's assume a generic crypto MCP.
                "https://api.crypto-mcp.com/mcp" # Placeholder URL
            ]
        }
    )

    # 2. Define a custom handler (optional, backend usually handles it)
    def my_handler(prompt: str) -> str:
        print(f"Agent received prompt: {prompt}")
        return f"Gemini Processing: {prompt}"

    # 3. Start the Sovereign Agent Server
    # When deployed, this agent will:
    # - Have its own Identity Wallet (generated in agent_identity.json)
    # - Be reachable via /agent (monetized)
    # - Support inter-agent communication via /a2a
    print("Initializing Agent Server...")
    server = AgentServer(config, my_handler)
    
    print("Starting Cronos Gemini Agent on port 8000...")
    server.run(host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
