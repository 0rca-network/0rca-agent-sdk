from web3 import Web3
from eth_account import Account

# --- CONFIG ---
RPC_URL = "https://evm-t3.cronos.org"
MNEMONIC = "dish public milk ramp capable venue poverty grain useless december hedgehog shuffle"
AGENT_IDENTITY_ADDRESS = "0x975C5b75Ff1141E10c4f28454849894F766B945E"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
Account.enable_unaudited_hdwallet_features()
owner = Account.from_mnemonic(MNEMONIC)

def fund_agent():
    print(f"Funding Agent {AGENT_IDENTITY_ADDRESS} with 1 CRO...")
    
    nonce = w3.eth.get_transaction_count(owner.address)
    tx = {
        'nonce': nonce,
        'to': Web3.to_checksum_address(AGENT_IDENTITY_ADDRESS),
        'value': w3.to_wei(1, 'ether'),
        'gas': 21000,
        'gasPrice': w3.eth.gas_price,
        'chainId': 338
    }
    
    signed_tx = w3.eth.account.sign_transaction(tx, owner.key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Funding TX Sent: {w3.to_hex(tx_hash)}")
    
    print("Waiting for confirmation...")
    w3.eth.wait_for_transaction_receipt(tx_hash)
    print("Agent wallet funded!")

if __name__ == "__main__":
    fund_agent()
