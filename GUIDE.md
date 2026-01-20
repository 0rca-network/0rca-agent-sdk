# 0rca Agent SDK Developer Guide

This guide explains the architecture and usage of the 0rca Agent SDK, including the x402 payment protocol, the on-chain Escrow system, and Agent-to-Agent (A2A) communication.

## 🚀 Overview

The 0rca Agent SDK enables developers to build AI agents that:
1. **Gate access** via x402 (EVM-based) payments.
2. **Collect earnings** on-chain via a non-custodial Escrow contract.
3. **Communicate** with other agents using a standard A2A protocol.

---

## 1. Configuration (`AgentConfig`)

Agents are configured using the `AgentConfig` class. You must provide an EVM wallet address for payouts and the price per request.

```python
from orca_agent_sdk.config import AgentConfig

config = AgentConfig(
    agent_id="my-agent",
    wallet_address="0x...",      # Payout destination
    price="0.25",                # Price in USDC
    token_address="devUSDC.e",   # Token identifier
    chain_caip="eip155:84531"    # Cronos Testnet
)
```

---

## 2. x402 Payment Protocol

The SDK follows the **x402 Payment Protocol** (Standard HTTP-based gating).

### The Flow:
1. **Request**: A client calls the `/agent` endpoint.
2. **Challenge**: If no payment is detected, the server returns `402 Payment Required` with an `X-PAYMENT` challenge header.
3. **Sign**: The client signs the challenge (EIP-3009 transfer authorization).
4. **Verify**: The server verifies the signature via the Cronos Facilitator.
5. **Execute**: On success, the agent logic runs and returns the result.

---

## 3. Payment & Settlement Contracts

The SDK supports two ways to collect payments:

### 3.1 Sovereign Vault (`OrcaAgentVault`)
A dedicated contract for a single agent. This is the **standard for independent agents**.
- **Agent Role**: After completing a task, the agent calls `vault.spend(taskId, amount)` to move funds from task budget to earnings.
- **Withdrawal**: The agent owner can call `vault.withdraw()` to get the USDC.

### 3.2 Marketplace Hub (`TaskEscrow`)
A shared contract for multiple agents.
- **Role**: Used by platforms to manage payments across many agents.
- **Auto-Discovery**: The SDK automatically detects which contract type is being used at the `AGENT_VAULT` address provided in `.env`.

### 3.3 Security
- Only the **Agent Owner** or the **Agent Instance** (authorized in the contract) can trigger payouts.
- Only the **Facilitator** (or user via `createTask`) can credit funds.

---

## 4. Agent-to-Agent (A2A) Protocol

Inspired by Google's Agent2Agent concept, the SDK includes a modular A2A layer.

### Endpoints:
- `POST /a2a/send`: Internal endpoint to trigger a message to another agent.
- `POST /a2a/receive`: Endpoint that receives messages from other agents.

### Message Schema:
```json
{
  "header": {
    "message_id": "uuid",
    "from": "agent-a",
    "to": "agent-b",
    "timestamp": 123456789
  },
  "task": {
    "action": "chat",
    "payload": { "prompt": "..." }
  }
}
```

---

## 5. Running the Examples

### Setup Environment
Ensure your dependencies are installed:
```bash
pip install flask requests x402 web3 eth-account
```

### Start Local Network
Inside `contracts-project/`:
```bash
npx hardhat node
npx hardhat run scripts/deploy.js --network localhost
```

### Run an Agent
```bash
python examples/basic_agent.py
```

### Test the Flow
```bash
# Check x402 Handshake
python examples/client_demo.py

# Check Escrow Balance
python examples/escrow_reader.py
```

---

## 📂 Project Structure

- `orca_agent_sdk/`: Core logic (Server, Registry, A2A).
- `contracts-project/`: Hardhat workspace (Escrow Solidity code).
- `examples/`: Ready-to-use demo scripts.
