import os
import sys
from dotenv import load_dotenv

# Add SDK to path
sdk_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(sdk_path)

from orca_agent_sdk.contract_agent import ContractAgent

load_dotenv()

def main():
    # Contract Addresses on Cronos Mainnet
    CONTRACTS = {
        "Moonlander": "0xE6F6351fb66f3a35313fEEFF9116698665FBEeC9",
        "MLP": "0xb4c70008528227e0545Db5BA4836d1466727DF13",
        "FM": "0x37888159581ac2CdeA5Fb9C3ed50265a19EDe8Dd",
        "CM": "0x5449239f7F6992D7d13fc4E02829aC90B2bEa6D1",
        "StakedFmTracker": "0x7eC427359d3470128f2A6C3d4c141AF158ed3A04",
        "StakedFmDistributor": "0xB7Fe13C40D9E4cD4b549fD1766e4ef74ef06330d",
        "FeeFmTracker": "0xbF438c48Eff2b47F4e77Ea72dbC6588aB4f849CC",
        "FeeFmDistributor": "0x6F27c8aCeD67424D3E7c7F42997489586b21F2f6",
        "StakedMlpTracker": "0x071788084370497ED1Ac19C6711bd1d4Af0E9034",
        "StakedMlpDistributor": "0x8Dbebe40e6bE35cF1bE07b22Aa5fa11f4768917E"
    }

    system_prompt = f"""
    You are the 0rca Contract Agent, an expert in interacting with DeFi protocols on Cronos.
    You have specialized tools to load contract ABIs, inspect functions, simulate calls, and execute transactions.
    
    The following contracts are available on Cronos Mainnet:
    {chr(10).join([f"- {name}: {addr}" for name, addr in CONTRACTS.items()])}
    
    Your goal is to help users interact with these contracts. Always simulate state-changing calls before executing them.
    Be extremely careful with real transactions.
    """

    agent = ContractAgent(
        name="0rca-contract-agent",
        model="gemini/gemini-2.0-flash",
        system_prompt=system_prompt,
        price="0.0", # Free for demo
    )

    print("0rca Contract Agent initialized.")
    print("Example usage: 'Load the Moonlander contract and show me its functions.'")
    
    # Run the server
    agent.run(port=8001)

if __name__ == "__main__":
    main()
