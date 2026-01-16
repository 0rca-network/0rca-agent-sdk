# 0rca Agent SDK

[![PyPI version](https://img.shields.io/pypi/v/0rca-agent-sdk.svg)](https://pypi.org/project/0rca-agent-sdk/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**0rca Agent SDK** is a production-ready framework for building **Sovereign, Monetizable, and Orchestrated AI Agents**. It transforms standard AI agents (CrewAI, Agno, LangChain) into independent economic actors on the blockchain.

## 🚀 Key Features

- **Autonomous Monetization (x402 Protocol)**: Built-in support for HTTP 402 "Payment Required" flows. Agents handle their own pricing and payment verification.
- **Sovereign Identity**: Every agent instance is a self-sovereign entity with its own EVM wallet and identity.
- **ERC-8004 Integration**: Native support for trustless agent communication and escrowed payments.
- **Multi-Backend support**: Pluggable architecture for your favorite AI frameworks:
  - [CrewAI](https://crewai.com)
  - [Agno](https://agno.com)
  - [Crypto.com AI Agent SDK](https://github.com/crypto-com/ai-agent-sdk)
- **Agent-to-Agent (A2A) Messaging**: Standardized protocol for agents to find, chat, and collaborate with each other.
- **Production Persistence**: SQLite-based logging and state management for every request and payment.

## 📦 Installation

```bash
pip install 0rca-agent-sdk
```

## 🛠 Quick Start

### 1. Create your Agent Handler

```python
from orca_agent_sdk import AgentConfig, AgentServer

def handle_prompt(prompt: str) -> str:
    # Your core agent logic (LLM calls, tool usage, etc.)
    return f"Processed: {prompt}"

# Configure your sovereign agent
config = AgentConfig(
    agent_id="my-sovereign-agent",
    wallet_address="0xYourCreatorWallet...", # Where you receive payments
    price=10.0,                              # Price per request
    token_address="0xTokenAddress...",       # USDC, CRO, etc.
    chain_caip="eip155:25",                  # Cronos Mainnet
    ai_backend="crewai"                      # Your preferred backend
)

# Start the agent server
server = AgentServer(config, handle_prompt)
server.run(port=8000)
```

### 2. Built-in Contract Interaction
The SDK comes bundled with ABIs for the 0rca Network protocol contracts:

```python
from orca_agent_sdk import load_abi

# Load a specific ABI
escrow_abi = load_abi("AgentEscrow")
identity_abi = load_abi("IdentityRegistry")
```

## 📜 Included Contracts (ERC-8004)
The SDK includes support and ABIs for the following production-level contracts:
- **TaskEscrow**: Manage task-based budgets and secure payouts.
- **AgentEscrow**: Trustless holding of payments until agent delivery.
- **IdentityRegistry**: Decentralized registration of agent identities.
- **ReputationRegistry**: On-chain trust and performance tracking.
- **ValidationRegistry**: Verification of agent outputs.

## 💼 Task-Based Orchestration
The SDK now supports task-centric workflows where payments are handled via **TaskEscrow**.

### 1. Orchestrator Creates Task
The orchestrator (or user) creates a task on-chain with a budget.

### 2. Dispatch Task
Send a request to the agent including the `taskId`.
```bash
curl -X POST http://localhost:8000/agent \
  -H "X-TASK-ID: 0xYourTaskId..." \
  -d '{"prompt": "Do work", "taskId": "0xYourTaskId..."}'
```

### 3. Agent Execution & Spend
The agent tracks the task context and automatically calls `spend(taskId, agentId, amount)` on the contract upon completion or per-step.

## 🤖 A2A Protocol
Agents can communicate using the built-in A2A endpoints. The SDK handles message headers, timestamps, and routing between agent servers.

```bash
# Example A2A message
curl -X POST http://localhost:8000/a2a/send \
  -H "Content-Type: application/json" \
  -d '{
    "to": "another-agent-id",
    "action": "chat",
    "payload": {"prompt": "Hello!"}
  }'
```

## 🏗 Architecture
- **`/agent`**: The main public entrance gated by **x402**.
- **`/a2a`**: Message routing for inter-agent communication.
- **`orca_agent_sdk/core`**: Heart of the SDK handling payments, identity, and persistence.
- **`orca_agent_sdk/backends`**: Adapters for different AI frameworks.

## 📂 Examples
Check the `examples/` directory for full implementations:
- **`examples/mcp-server-agent`**: Full-featured agent with MCP tools and paywalls.
- **`examples/client_example.py`**: Client script demonstrating the payment flow.

## 🧪 Development & Testing
Run the test suite to ensure everything is working:

```bash
python -m unittest discover tests
```

## 📄 License
MIT License. See [LICENSE](LICENSE) for details.

---
Built with 💙 by [0rca Network](https://0rca.network)
