from web3 import Web3

RPC_URL = "https://evm-t3.cronos.org"
USDC_E_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"

w3 = Web3(Web3.HTTPProvider(RPC_URL))

ABI = [
    {"constant":True,"inputs":[],"name":"name","outputs":[{"name":"","type":"string"}],"type":"function"},
    {"constant":True,"inputs":[],"name":"version","outputs":[{"name":"","type":"string"}],"type":"function"},
]

def introspect():
    usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_E_ADDRESS), abi=ABI)
    try:
        print(f"Name: {usdc.functions.name().call()}")
    except:
        print("Could not get name")
    
    try:
        print(f"Version: {usdc.functions.version().call()}")
    except:
        print("Could not get version")

if __name__ == "__main__":
    introspect()
