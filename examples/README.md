
# 0rca Agent SDK Examples

This directory contains examples demonstrating how to build and interact with Sovereign AI Agents using the SDK.

## Contents

- `mcp-server-agent/`: A comprehensive example agent exposing MCP tools with paywalls.
- `client_example.py`: A Python client script demonstrating how to interact with an agent, handle payments (EIP-712), and get results.
- `igno_agent_example.py`: Example using Agno backend.
- `interact_with_gemini.py`: Interaction example using Gemini API.

## Running the Authenticated Client Example

The `client_example.py` script shows the full flow of:
1. Sending a request to the agent.
2. Receiving a 402 Payment Required response.
3. Signing the required payment challenge (EIP-712).
4. Resending the request with the `X-PAYMENT` header.

### Prerequisites
- Python 3.10+
- An Ethereum private key (for signing payments)

### Usage

1. Start your agent (e.g., the MCP agent):
   ```bash
   python examples/mcp-server-agent/run_free_agent.py
   ```

2. run the client:
   ```bash
   # Set your private key as env var or edit the script
   export PRIVATE_KEY="0x..." 
   python examples/client_example.py
   ```
