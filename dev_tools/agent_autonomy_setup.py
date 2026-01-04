import os
import json
from web3 import Web3
from eth_account import Account
# Import from the SDK constants
from orca_agent_sdk.constants import IDENTITY_REGISTRY, CHAIN_CAIP

# --- CONFIG ---
RPC_URL = "https://evm-t3.cronos.org"
AGENT_ID = 0
# User Mnemonic (Owner)
MNEMONIC = "dish public milk ramp capable venue poverty grain useless december hedgehog shuffle"
# Agent Identity Address
AGENT_IDENTITY_ADDRESS = "0x975C5b75Ff1141E10c4f28454849894F766B945E"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
Account.enable_unaudited_hdwallet_features()
owner = Account.from_mnemonic(MNEMONIC)

# Minimal ERC721 ABI for transfer
ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "from", "type": "address"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "tokenId", "type": "uint256"}
        ],
        "name": "safeTransferFrom",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "tokenId", "type": "uint256"}],
        "name": "ownerOf",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def setup_autonomy():
    registry = w3.eth.contract(address=IDENTITY_REGISTRY, abi=ABI)
    
    # 1. Check current owner
    current_owner = registry.functions.ownerOf(AGENT_ID).call()
    print(f"Current Owner of Agent {AGENT_ID}: {current_owner} on registry {IDENTITY_REGISTRY}")
    
    if current_owner.lower() == AGENT_IDENTITY_ADDRESS.lower():
        print("Agent already owns itself! Autonomy active.")
        return

    # 2. Transfer to Agent
    print(f"Transferring Agent NFT {AGENT_ID} to Agent Identity {AGENT_IDENTITY_ADDRESS}...")
    nonce = w3.eth.get_transaction_count(owner.address)
    tx = registry.functions.safeTransferFrom(
        owner.address,
        AGENT_IDENTITY_ADDRESS,
        AGENT_ID
    ).build_transaction({
        'from': owner.address,
        'nonce': nonce,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 338
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, owner.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transfer transaction sent: {w3.to_hex(tx_hash)}")
    
    print("Waiting for confirmation...")
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("SUCCESS! Agent now owns itself on the PRODUCTION registry.")

if __name__ == "__main__":
    setup_autonomy()
