from web3 import Web3

RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"
USER_ADDRESS = "0xcCED528A5b70e16c8131Cb2de424564dD938fD3B"
AGENT_ADDRESS = "0x975C5b75Ff1141E10c4f28454849894F766B945E"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
ERC20_ABI = [{"constant":True,"inputs":[{"name":"_owner","type":"address"}],"name":"balanceOf","outputs":[{"name":"balance","type":"uint256"}],"type":"function"}]

def check():
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_ADDRESS), abi=ERC20_ABI)
    
    user_bal = usdc.functions.balanceOf(Web3.to_checksum_address(USER_ADDRESS)).call()
    agent_bal = usdc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDRESS)).call()
    
    print(f"\n--- USDC.E BALANCE CHECK ---")
    print(f"User Wallet ({USER_ADDRESS}): {user_bal / 10**6} USDC.E")
    print(f"Agent Wallet ({AGENT_ADDRESS}): {agent_bal / 10**6} USDC.E")

if __name__ == "__main__":
    check()
