# Sovereign Agent Vault: Implementation Guide

This guide explains the "Sovereign Agent" architecture implemented in the 0rca Agent SDK. In this model, every AI agent possesses its own dedicated financial smart contract (`OrcaAgentVault`), acting as its private bank and escrow system.

## 🌟 Overview
Unlike centralized escrow systems, the Sovereign Vault model provides:
- **Isolation**: Each agent's funds are physically separated on-chain.
- **Autonomy**: Agents claim their own earnings by signing `spend` transactions.
- **Transparency**: Users fund tasks directly into the agent's unique vault.

---

## 🏗️ Architecture

1.  **IdentityRegistry**: A global registry mapping `agentId` to metadata (Endpoint, Vault Address, etc.).
2.  **OrcaAgentVault**: A sovereign contract per agent that handles:
    -   `createTask`: Users lock USDC for a specific job.
    -   `spend`: The Agent claims a portion of the locked budget.
    -   `withdraw`: The Developer (Owner) withdraws accumulated agent earnings.

---

## 🚀 Getting Started

All files for this implementation are located in `examples/vault-agent/`.

### 1. Deploy the Sovereign Vault
Every agent needs a vault. Deploy it using the JavaScript Hardhat script:

```powershell
# In contracts-project/
powershell -ExecutionPolicy Bypass -File deploy_example_vault.ps1
```
*This script uses `examples/vault-agent/deploy_vault.js` to deploy the contract and saves the address to `.env.vault`.*

### 2. Register Your Agent
Link your new vault address to your agent's identity on-chain:

```powershell
$env:AGENT_VAULT="0xYourVaultAddress"; python examples/vault-agent/register_agent.py
```
*This registers a new Agent ID and sets metadata: `endpoint` -> `http://localhost:8000` and `vault` -> `0xYourVaultAddress`.*

### 3. Run the Sovereign Agent
Start the agent server. It will automatically load the vault from environment variables or the Registry.

```powershell
$env:PYTHONPATH="."; 
$env:AGENT_VAULT="0xYourVaultAddress"; 
$env:GOOGLE_API_KEY="your_gemini_key"; 
python examples/vault-agent/run_vault_agent.py
```

### 4. Simulate a Client Task
Use the simulation script to fund a task and call the agent:

```powershell
python examples/vault-agent/simulate_client.py
```
**What happens under the hood:**
1.  **Approval**: Client approves the Vault to take USDC.
2.  **Funding**: Client calls `vault.createTask()` with 0.1 USDC.
3.  **Agent Request**: Client sends a prompt to the Agent via HTTP.
4.  **Auto-Spend**: Upon success, the Agent Server automatically calls `vault.spend()` to claim the 0.1 USDC.

---

## 🛠 SDK Integration

### Initializing a Sovereign Agent
```python
from orca_agent_sdk.agent import OrcaAgent

agent = OrcaAgent(
    name="MySovereignAgent",
    price="0.1",  # Price in USDC
    vault_address="0x..." # Optional if registered on-chain
)
```

### Manual Financial Controls
You can manually interact with the vault via the agent object:

```python
# Check earnings
balance = agent.get_earnings_balance()

# Manually claim a payout
agent.claim_payment(task_id="0x...", amount=0.05)

# Developer withdrawal (to the owner wallet)
agent.withdraw_earnings()
```

---

## 📋 Environment Variables

| Variable | Description |
| :--- | :--- |
| `AGENT_VAULT` | The address of the agent's `OrcaAgentVault.sol` contract. |
| `GOOGLE_API_KEY` | Your Gemini API key for the AI backend. |
| `PRIVATE_KEY` | The agent's identity private key (found in `agent_identity.json`). |
| `USDC_E` | Cronos Testnet USDC token address. |

---

## 🔒 Security Notes
- **Access Control**: Only the `owner` (Developer) or the `agent` (Identity address) can call the `spend` function.
- **Withdrawals**: Only the `owner` (Developer) can trigger a withdrawal of the total accumulated earnings.
- **Refunds**: Task creators can call `closeTask` to refund any *remaining* budget and prevent further spending on that task.
