import os
import sys
from dotenv import load_dotenv

# Add parent directory to path to reach orca_agent_sdk
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from orca_agent_sdk import AgentConfig, AgentServer, tool_paywall

load_dotenv()

# --- 1. Define Premium Tools ---

@tool_paywall
def say_hello():
    """
    Returns a friendly greeting. 
    This is a premium tool that requires a paywall.
    """
    return "Hello! You have successfully paid for this premium greeting. Welcome to the sovereign future!"

@tool_paywall
def generate_secret_code():
    """
    Generates a cryptographically secure secret code.
    This is a high-value tool that requires a paywall.
    """
    import secrets
    code = secrets.token_hex(4).upper()
    return f"Your premium secret code is: {code}"

def handle_direct(prompt):
    # This won't be called for CDC backend as it handles it internally
    return f"Echo: {prompt}"

# --- 2. Setup Configuration ---

def run_agent():
    # We set general price to "0.0" so users can chat with the agent for free.
    # But specific tools have paywalls.
    config = AgentConfig(
        agent_id="tool-paywall-agent",
        price="0.0", 
        
        # Define Tool Paywalls
        # Note: Tool names must match function names exactly
        tool_prices={
            "say_hello": "0.1",
            "generate_secret_code": "0.5"
        },
        
        # Crypto.com Backend Settings
        ai_backend="crypto_com",
        cdc_api_key=os.getenv("GEMINI_API_KEY"), # Using the Gemini key for provider
        
        # On-Chain Configuration
        on_chain_id=0,
        chain_caip="eip155:338", # Cronos Testnet
    )

    # Register the tools in backend_options
    config.backend_options["tools"] = [say_hello, generate_secret_code]
    
    # Configure Gemini provider for CDC
    config.backend_options["provider"] = "GoogleGenAI"
    config.backend_options["model"] = "gemini-2.0-flash"

    # Start the server
    print("\n🚀 Starting Tool Paywall Agent...")
    print(f"💰 Paywalls configured: {config.tool_prices}")
    print("--------------------------------------------------")
    
    server = AgentServer(config, handle_direct)
    server.run(port=8001)

if __name__ == "__main__":
    run_agent()
