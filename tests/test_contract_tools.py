import sys
import os
import json
from web3 import Web3

# Add SDK to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orca_agent_sdk.contract_agent import ContractAgent

def test_contract_tools():
    # Setup
    agent = ContractAgent(
        name="test-agent",
        model="gemini/gemini-2.0-flash",
        system_prompt="Test",
        price="0.0"
    )

    # 1. Verify Tools Registration
    print("\n--- Verifying Tool Registration ---")
    tool_names = [t.name for t in agent.native_tools]
    print(f"Registered tools: {tool_names}")
    expected_tools = ["load_contract", "describe_function", "simulate_contract_call", "execute_contract_call", "read_contract"]
    for et in expected_tools:
        if et in tool_names:
            print(f"✅ Tool {et} found")
        else:
            print(f"❌ Tool {et} MISSING")

    # 2. Test Load Contract (with fallback for Moonlander)
    print("\n--- Testing Load Contract (Moonlander Fallback) ---")
    load_contract_tool = next(t for t in agent.native_tools if t.name == "load_contract")
    moonlander_address = "0xE6F6351fb66f3a35313fEEFF9116698665FBEeC9"
    chain = "cronos"
    
    print(f"Calling load_contract for Moonlander...")
    result_json = load_contract_tool.func(chain=chain, address=moonlander_address)
    result = json.loads(result_json)
    
    if "error" in result:
        print(f"FAILED: {result['error']}")
        return
    else:
        print(f"SUCCESS: Loaded {result.get('contractId')} with {len(result.get('functions', []))} functions")
        print(f"Functions: {[f['name'] for f in result.get('functions', [])]}")

if __name__ == "__main__":
    test_contract_tools()
