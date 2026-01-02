import os
from orca_agent_sdk import AgentConfig, AgentServer

def main():
    # 1. Setup Configuration for Cronos Testnet
    config = AgentConfig(
        agent_id="cronos-gemini-agent",
        # This is where your agent receives payments (USDC/CRO)
        wallet_address="0x975C5b75Ff1141E10c4f28454849894F766B945E", 
        price="1.0",
        token_address="0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0",
        
        # Cronos Testnet CAIP
        chain_caip="eip155:338",
        
        # Use Crypto.com Backend with Gemini
        ai_backend="crypto_com",
        
        # Gemini Configuration (Powered by CDC SDK)
        backend_options={
            "provider": "GoogleGenAI",
            "model": "gemini-2.0-flash",
            "provider_api_key": "AIzaSyBGPX7TYDBwXskzsmhWuAz2VP8MvuLhxiY",
            "temperature": 0.7,
            "plugins": {
                "instructions": "You are a professional financial assistant on the Cronos network."
            }
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
