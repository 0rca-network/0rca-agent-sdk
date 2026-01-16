from web3 import Web3
import json
import os

def check_task():
    w3 = Web3(Web3.HTTPProvider("https://evm-t3.cronos.org"))
    contract_address = "0x9fE46736679d2D9a65F0992F2272dE9f3c7fa6e0"
    
    # Load ABI
    with open("orca_agent_sdk/contracts/abis/TaskEscrow.json", "r") as f:
        abi = json.load(f)
        
    contract = w3.eth.contract(address=contract_address, abi=abi)
    
    task_id = "0x" + "a" * 64
    task_id_bytes = bytes.fromhex(task_id[2:])
    
    print(f"Checking Task: {task_id}")
    task_data = contract.functions.tasks(task_id_bytes).call()
    print(f"Task Data: {task_data}")
    # (budget, remaining, creator, status, exists)
    
    if not task_data[4]:
        print("!!! TASK DOES NOT EXIST ON-CHAIN !!!")
        print("The agent cannot spend from a task that wasn't created by an orchestrator.")

if __name__ == "__main__":
    check_task()
