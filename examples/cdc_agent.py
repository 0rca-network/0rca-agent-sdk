from orca_agent_sdk.config import AgentConfig
from orca_agent_sdk.server import AgentServer

# Configuration for Crypto.com AI Backend
config = AgentConfig(
    agent_id="cdc-defi-agent",
    wallet_address="0x1234567890123456789012345678901234567890", # Your Payout Address
    price="0.5", 
    token_address="devUSDC.e",
    chain_caip="eip155:84531", # Cronos Testnet
    
    # Enable Crypto.com Backend
    ai_backend="crypto_com",
    
    # CDC Specific Credentials (placeholder logic)
    cdc_api_key="your-cdc-platform-key",
    cdc_private_key="your-wallet-private-key",
    cdc_sso_wallet_url="https://sso-wallet.crypto.com",
    
    # Extra options (e.g. LLM provider keys if needed by the backend adapter)
    backend_options={
        "openai_key": "sk-proj-xyz..."
    }
)

def dummy_handler(prompt: str) -> str:
    """
    This handler is ignored by the CDC backend in the current implementation,
    as the CDC SDK manages its own execution flow.
    """
    return "Ignored"

if __name__ == "__main__":
    server = AgentServer(config, dummy_handler)
    print("Running 0rca Agent with Crypto.com Backend...")
    server.run(port=8002)
