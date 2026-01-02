import argparse
from .server import AgentServer
from .config import AgentConfig

def main():
    parser = argparse.ArgumentParser(description="0rca Agent SDK Server")
    parser.add_argument("--port", type=int, default=8000, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to run the server on")
    parser.add_argument("--backend", type=str, default="crewai", help="AI backend to use (crewai, agno, crypto_com)")
    
    args = parser.parse_args()
    
    # Simple default config for CLI usage
    # In a real scenario, users would likely use a config file or environment variables
    config = AgentConfig(
        agent_id="cli-agent",
        ai_backend=args.backend,
        # Other values would come from environment variables or defaults
    )
    
    def dummy_handler(prompt: str) -> str:
        return f"CLI Default Handler: Received '{prompt}'"
    
    server = AgentServer(config, dummy_handler)
    server.run(host=args.host, port=args.port)

if __name__ == "__main__":
    main()
