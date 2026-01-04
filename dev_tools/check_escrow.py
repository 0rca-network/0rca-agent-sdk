from web3 import Web3

RPC_URL = "https://evm-t3.cronos.org"
ESCROW_ADDRESS = "0x86768D20Ad92d727c987fddD10d08aFA25B85E78"
AGENT_ID = 0

w3 = Web3(Web3.HTTPProvider(RPC_URL))
ESCROW_ABI = [{"inputs": [{"internalType": "uint256", "name": "agentId", "type": "uint256"}], "name": "balances", "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}], "stateMutability": "view", "type": "function"}]

def check_escrow():
    escrow = w3.eth.contract(address=ESCROW_ADDRESS, abi=ESCROW_ABI)
    bal = escrow.functions.balances(AGENT_ID).call()
    print(f"Agent {AGENT_ID} Escrow Balance: {bal / 10**6} USDC.E")

if __name__ == "__main__":
    check_escrow()
