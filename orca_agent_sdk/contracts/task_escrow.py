from typing import Optional, Dict, Any
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from ..config import AgentConfig
from ..constants import TASK_ESCROW
from . import load_abi

class TaskEscrowClient:
    def __init__(self, config: AgentConfig, private_key: str):
        self.config = config
        self.private_key = private_key
        
        # Initialize Web3
        rpc_url = getattr(config, "rpc_url", "https://evm-t3.cronos.org")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not TASK_ESCROW:
            raise ValueError("TASK_ESCROW address not configured. Please set TASK_ESCROW environment variable.")
            
        self.contract_address = self.w3.to_checksum_address(TASK_ESCROW)
        
        # Load Official ABI
        self.abi = load_abi("TaskEscrow")
        
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        self.account = self.w3.eth.account.from_key(private_key)

        # Chain ID from CAIP (e.g. eip155:338 -> 338)
        try:
            self.chain_id = int(config.chain_caip.split(":")[-1])
        except (ValueError, AttributeError):
            self.chain_id = 338 # Default to Cronos Testnet

    def spend(self, task_id: str, agent_id: int, amount: int) -> str:
        """
        Calls spend() on TaskEscrow contract.
        Returns transaction hash.
        """
        # Convert task_id to bytes32 if string
        if isinstance(task_id, str):
            if task_id.startswith("0x"):
                task_id_bytes = bytes.fromhex(task_id[2:])
            else:
                # If it's a raw string, we might need to hash it or pad it. 
                # Assuming here it's a hex string without 0x or needs simple encoding
                # For safety, let's assume it comes as a hex string from the orchestrator.
                # If not, we might fail. Let's start with bytes conversion.
                try:
                    task_id_bytes = bytes.fromhex(task_id)
                except:
                    # Fallback: KECCAK256 of the string ID? Or just encode?
                    # Let's assume standard bytes32 hex input for now.
                    raise ValueError("task_id must be a hex string representing bytes32")

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        tx = self.contract.functions.spend(
            task_id_bytes,
            agent_id,
            amount
        ).build_transaction({
            'chainId': self.chain_id, 
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        print(f"[TaskEscrowClient] Sending 'spend' transaction for task {task_id}...", flush=True)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return self.w3.to_hex(tx_hash)
