import requests
import json
import time
import os
import base64
from web3 import Web3

AGENT_URL = "http://localhost:8000"
RPC_URL = "https://evm-t3.cronos.org"
USDC_ADDRESS = "0xc01efAaF7C5C61bEbFAeb358E1161b537b8bC0e0"
ESCROW_ADDRESS = "0x482C45A341e6BE4D171136daba45E87ACaAc22a0"

# Using the agent wallet as mock orchestrator for the test
AGENT_ID = 0 

def create_onchain_task(task_id_hex: str):
    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    
    # Load private key from agent_identity.json
    with open("agent_identity.json", "r") as f:
        creds = json.load(f)
        pk = creds["private_key"]
        
    account = w3.eth.account.from_key(pk)
    print(f"[Orchestrator] Using wallet: {account.address}")
    
    # Task ID must be bytes32
    task_id_bytes = bytes.fromhex(task_id_hex[2:])
    
    # Minimial ABIs
    usdc_abi = [{"inputs":[{"name":"spender","type":"address"},{"name":"amount","type":"uint256"}],"name":"approve","outputs":[{"name":"","type":"bool"}],"type":"function"}]
    escrow_abi = [{"inputs":[{"name":"taskId","type":"bytes32"},{"name":"budget","type":"uint256"},{"name":"user","type":"address"}],"name":"createTask","outputs":[],"type":"function"}]
    
    usdc = w3.eth.contract(address=USDC_ADDRESS, abi=usdc_abi)
    escrow = w3.eth.contract(address=ESCROW_ADDRESS, abi=escrow_abi)
    
    budget = 100000 # 0.1 USDC
    
    print(f"[Orchestrator] Creating task {task_id_hex} with budget 0.1 USDC...")
    
    # 1. Approve USDC
    nonce = w3.eth.get_transaction_count(account.address)
    tx = usdc.functions.approve(ESCROW_ADDRESS, budget).build_transaction({
        'chainId': 338, 'gas': 100000, 'gasPrice': w3.eth.gas_price, 'nonce': nonce
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    w3.eth.send_raw_transaction(signed.raw_transaction)
    
    # 2. Create Task
    nonce += 1
    tx = escrow.functions.createTask(task_id_bytes, budget, account.address).build_transaction({
        'chainId': 338, 'gas': 200000, 'gasPrice': w3.eth.gas_price, 'nonce': nonce
    })
    signed = w3.eth.account.sign_transaction(tx, pk)
    w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"[Orchestrator] Task created on-chain! Wait 5s for block...")
    time.sleep(5)

def generate_mock_x402():
    payload = {
        "payment": {
            "token": USDC_ADDRESS,
            "amount": "100000",
            "recipient": "0xABC123..."
        },
        "signature": "0x" + "1" * 130 
    }
    return base64.b64encode(json.dumps(payload).encode()).decode()

def test_flow():
    # 1. Prepare Task Data
    # generate unique task id to avoid conflict
    import secrets
    task_id = "0x" + secrets.token_hex(32)
    
    # -- NEW: Create on-chain task first so the Agent can actually 'spend' --
    create_onchain_task(task_id)
    
    req_payload = {
        "prompt": "Say hello to the user and tell them a joke about blockchains.",
        "taskId": task_id,
        "subTaskId": "sub-prod-001"
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-TEST-BYPASS": "true", 
        "X-TASK-ID": task_id,
        "X-PAYMENT": generate_mock_x402()
    }

    print(f"\n[Client] Dispatching Task to Agent: {task_id}")
    
    try:
        start_time = time.time()
        resp = requests.post(f"{AGENT_URL}/agent", json=req_payload, headers=headers)
        duration = time.time() - start_time
        
        print(f"[Client] Status Code: {resp.status_code}")
        if resp.status_code == 200:
            print(f"[Client] Response Received in {duration:.2f}s:")
            print(json.dumps(resp.json(), indent=2))
            print("\n[Client] Success! The Agent has completed the task and claimed the 0.1 USDC.")
            print(f"Check transaction on Explorer for TaskId: {task_id}")
        else:
            print(f"[Client] Error Response:")
            print(json.dumps(resp.json(), indent=2))
            
    except Exception as e:
        print(f"[Client] Connection Failed: {e}")

if __name__ == "__main__":
    test_flow()
