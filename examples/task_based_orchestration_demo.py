"""
Example: Task-Based Orchestration and Spend Flow

This script demonstrates how an Orchestrator creates a task and dispatches it to an Agent.
The Agent then performs work (simulated) and spends from the TaskEscrow.
"""

import time
import requests
import json
from web3 import Web3

# Configuration
ORCHESTRATOR_URL = "http://localhost:3000" # Fake Orchestrator
AGENT_URL = "http://localhost:8000"
TASK_ESCROW_ADDR = "0x71be791E25abacA49FEaD19054FB044686c90c3b" # Placeholder
AgENT_ID = "0"

def create_task_on_chain(task_id: str, budget: int):
    print(f"[Orchestrator] Creating task {task_id} on chain with budget {budget}...")
    # Real implementation would call TaskEscrow.createTask(...) via Web3
    time.sleep(1)
    print(f"[Orchestrator] Task {task_id} created.")

def dispatch_task_to_agent(task_id: str, prompt: str):
    print(f"[Orchestrator] Dispatching task {task_id} to Agent...")
    
    payload = {
        "prompt": prompt,
        "taskId": task_id,
        "maxBudget": 1000000 # 1 USDC
    }
    
    try:
        # User/Orchestrator calls /agent endpoint
        # In a real scenario, this might be via A2A or direct HTTP if allowed
        headers = {
            "X-TASK-ID": task_id,
            # X-PAYMENT header would be here if using x402
        }
        
        resp = requests.post(f"{AGENT_URL}/agent", json=payload, headers=headers)
        print(f"[Agent Response] {resp.status_code} - {resp.json()}")
    except Exception as e:
        print(f"Failed to dispatch: {e}")

def main():
    task_id = "0x" + "a" * 64 # Fake 32-byte hash
    budget = 10 * 10**6 # 10 USDC
    
    # 1. Orchestrator funds task
    create_task_on_chain(task_id, budget)
    
    # 2. Orchestrator requests Agent
    dispatch_task_to_agent(task_id, "Analyze the market sentiment for CRO")

if __name__ == "__main__":
    main()
