# 0rca Agent SDK Architecture

The SDK is designed to be a thin wrapper around various AI backends, providing unified Payment (x402), Identity (A2A), and Persistence layers.

## Structure

```
orca_agent_sdk/
├── backends/
│   ├── base.py                 # Abstract Interface
│   ├── crewai_backend.py       # Default (Handler Wrapper)
│   ├── agno_backend.py         # Agno Adapter
│   └── crypto_com_backend.py   # CDC AI Agent Adapter
├── core/
│   ├── a2a.py                  # Agent-to-Agent Protocol
│   ├── payment.py              # x402 Verifier
│   ├── persistence.py          # SQLite Logger
│   └── x402.py                 # internal x402 utils
├── config.py                   # Configuration
├── server.py                   # Flask Server (Lifecycle Manager)
└── __init__.py                 # Public API (AgentConfig, AgentServer)
```

## Supported Backends

### 1. CrewAI (Default)
- **Config**: `ai_backend="crewai"`
- **Behavior**: synchronous wrapper around the user-provided handler function.

### 2. Agno
- **Config**: `ai_backend="agno"`
- **Behavior**: Initial integration for Agno agent runtime.

### 3. Crypto.com AI SDK
- **Config**: `ai_backend="crypto_com"`
- **Behavior**: Integrates `crypto_com_agent_client`.
- **Requires**: `cdc_api_key` in config.

## Payment & Settlement Layer

The SDK handles monetization via the **x402 Protocol**. Earnings are settled on-chain into a **Vault** or **Escrow** contract.

### 1. OrcaAgentVault (Sovereign)
- **Scope**: One contract per agent.
- **Ownership**: The agent developer owns the contract.
- **Logic**: Each task stores funds in the vault until the agent completes it and "spends" (claims) the reward.

### 2. TaskEscrow (Platform)
- **Scope**: One contract for multiple agents.
- **Ownership**: Platform or Registry owner.
- **Logic**: Centralized management of task budgets with automated payouts to individual agent owners.

## Development

To run from source:
```bash
pip install -e .
```
