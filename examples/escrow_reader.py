from web3 import Web3

# 1. Connect to Localnet
w3 = Web3(Web3.HTTPProvider("http://127.0.0.1:8545"))

if not w3.is_connected():
    print("Error: Could not connect to Ganache")
    exit(1)

# 2. Configuration (Paste from deployment output)
# Note: In a real app, these would come from config or env vars
ESCROW_ADDRESS = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"
REGISTRY_ADDRESS = "0xe7f1725E7734CE288F8367e1Bb143E90bb3F0512"

# Minimal ABI for AgentEscrow
ESCROW_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "name": "balances",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "facilitator",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def check_agent_balance(agent_id: int):
    contract = w3.eth.contract(address=ESCROW_ADDRESS, abi=ESCROW_ABI)
    
    # Read balance
    balance = contract.functions.balances(agent_id).call()
    print(f"Agent {agent_id} Balance: {balance} USDC (atomic units)")
    
    # Read facilitator
    facilitator = contract.functions.facilitator().call()
    print(f"Facilitator Address: {facilitator}")

if __name__ == "__main__":
    # Test with Agent ID 1 (which we surely don't have funds for yet, but let's check)
    check_agent_balance(1)
