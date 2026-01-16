# Protocol Update: Agent Earnings Vault

This update implements the "Vault" architecture where all agent earnings (from x402 and TaskEscrow) are centralized in a dedicated `AgentEscrow` contract.

## 1. Smart Contracts
- **AgentEscrow.sol**: A treasury contract that holds USDC for agents.
- **TaskEscrow.sol**: Updated to push funds to `AgentEscrow` upon task completion.

## 2. SDK Integration
- **AgentEscrowClient**: New client to manage withdrawals and balance checks.
- **TaskEscrowClient**: Updated to reflect the delegation of earnings to the vault.
- **AgentServer**: Unified logging for both single-agent and orchestrator earnings.

## 3. Workflow
1. User creates Task in `TaskEscrow`.
2. Agent performs work and calls `spend()`.
3. `TaskEscrow` sends USDC to `AgentEscrow` for that `agentId`.
4. Human owner withdraws from `AgentEscrow` at any time.
