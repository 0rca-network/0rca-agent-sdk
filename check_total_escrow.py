from web3 import Web3

RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"
ESCROW_ADDRESS = "0x86768D20Ad92d727c987fddD10d08aFA25B85E78"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def check():
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_ADDRESS), abi=ERC20_ABI)
    bal = usdc.functions.balanceOf(Web3.to_checksum_address(ESCROW_ADDRESS)).call()
    print(f"Escrow Contract USDC.E Balance: {bal / 10**6} USDC.E")

if __name__ == "__main__":
    check()
