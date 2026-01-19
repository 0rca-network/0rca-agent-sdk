import json
from web3 import Web3
from eth_account import Account

# --- CONFIG ---
RPC_URL = "https://evm-t3.cronos.org"
ESCROW_ADDRESS = "0x86768D20Ad92d727c987fddD10d08aFA25B85E78"
USDC_E_ADDRESS = "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1"
AGENT_ID = 0
# Agent Identity Private Key (from agent_identity.json)
AGENT_PRIVATE_KEY = "63918bb7d149f6cc03b40aeff33aff6da1736a1fe1f479f0da95e694698f69dc"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
agent_acc = Account.from_key(AGENT_PRIVATE_KEY)

ESCROW_ABI = [
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "withdraw",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}],
        "name": "balances",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

ERC20_ABI = [
    {"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}
]

def withdraw():
    escrow = w3.eth.contract(address=ESCROW_ADDRESS, abi=ESCROW_ABI)
    usdc = w3.eth.contract(address=USDC_E_ADDRESS, abi=ERC20_ABI)
    
    # 1. Check Escrow Balance
    escrow_bal = escrow.functions.balances(AGENT_ID).call()
    print(f"Agent {AGENT_ID} Escrow Balance: {escrow_bal / 10**6} USDC.E")
    
    if escrow_bal == 0:
        print("Nothing to withdraw.")
        return

    # 2. Check Agent Wallet Balance before
    before_bal = usdc.functions.balanceOf(agent_acc.address).call()
    print(f"Agent Wallet Balance Before: {before_bal / 10**6} USDC.E")

    # 3. Withdraw
    print(f"Agent {agent_acc.address} withdrawing funds...")
    nonce = w3.eth.get_transaction_count(agent_acc.address)
    tx = escrow.functions.withdraw(AGENT_ID).build_transaction({
        'from': agent_acc.address,
        'nonce': nonce,
        'gas': 150000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 338
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, agent_acc.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Withdraw TX Sent: {w3.to_hex(tx_hash)}")
    
    print("Waiting for confirmation...")
    w3.eth.wait_for_transaction_receipt(tx_hash)
    
    # 4. Check Final Balance
    after_bal = usdc.functions.balanceOf(agent_acc.address).call()
    print(f"Agent Wallet Balance After: {after_bal / 10**6} USDC.E")
    print(f"SUCCESS: Agent retrieved {escrow_bal / 10**6} USDC.E!")

if __name__ == "__main__":
    withdraw()
