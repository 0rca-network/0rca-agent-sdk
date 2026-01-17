from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from ..config import AgentConfig
import json
import os
from . import load_abi

class OrcaAgentVaultClient:
    """
    Client for interacting with a sovereign OrcaAgentVault contract.
    Handles tasks, earnings, and withdrawals for a specific agent.
    """
    def __init__(self, config: AgentConfig, vault_address: str, private_key: str):
        self.config = config
        self.private_key = private_key
        self.vault_address = Web3.to_checksum_address(vault_address)
        
        # Initialize Web3
        rpc_url = getattr(config, "rpc_url", "https://evm-t3.cronos.org")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        # Load ABI
        self.abi = load_abi("OrcaAgentVault")
        self.contract = self.w3.eth.contract(address=self.vault_address, abi=self.abi)
        self.account = self.w3.eth.account.from_key(private_key)

        try:
            self.chain_id = int(config.chain_caip.split(":")[-1])
        except:
            self.chain_id = 338 # Default to Cronos Testnet

    def spend(self, task_id: str, amount: int) -> str:
        """
        Agent claims payment from a task budget into its internal earnings.
        """
        if task_id.startswith("0x"):
            task_id_bytes = bytes.fromhex(task_id[2:])
        else:
            task_id_bytes = bytes.fromhex(task_id)

        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        # Check if we should use CroGas for gasless relay
        if hasattr(self.config, "crogas_url") and self.config.crogas_url:
            from .crogas import CroGasClient
            
            calldata = self.contract.encode_abi("spend", [task_id_bytes, amount])
            crogas = CroGasClient(
                api_url=self.config.crogas_url,
                private_key=self.private_key,
                chain_id=self.chain_id,
                usdc_address=getattr(self.config, "usdc_address", "0x38Bf87D7281A2F84c8ed5aF1410295f7BD4E20a1")
            )
            
            try:
                print(f"[VaultClient] Attempting gasless 'spend' via CroGas...", flush=True)
                result = crogas.execute(to=self.vault_address, data=calldata)
                return result.get("txHash")
            except Exception as e:
                print(f"[VaultClient] CroGas relay failed, falling back to direct: {e}", flush=True)
        
        tx = self.contract.functions.spend(
            task_id_bytes,
            amount
        ).build_transaction({
            'chainId': self.chain_id,
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        print(f"[VaultClient] Sending direct 'spend' to vault {self.vault_address} for task {task_id}...", flush=True)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return self.w3.to_hex(tx_hash)

    def withdraw(self) -> str:
        """
        Developer (owner) withdraws all earnings from the vault.
        """
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        tx = self.contract.functions.withdraw().build_transaction({
            'chainId': self.chain_id,
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        print(f"[VaultClient] Withdrawing all earnings from vault {self.vault_address}...", flush=True)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return self.w3.to_hex(tx_hash)

    def get_balance(self) -> int:
        """
        Returns the accumulated earnings balance in the vault.
        """
        return self.contract.functions.accumulatedEarnings().call()

    def get_task(self, task_id: str) -> dict:
        """
        Returns info about a task.
        """
        if task_id.startswith("0x"):
            task_id_bytes = bytes.fromhex(task_id[2:])
        else:
            task_id_bytes = bytes.fromhex(task_id)
            
        data = self.contract.functions.tasks(task_id_bytes).call()
        return {
            "budget": data[0],
            "remaining": data[1],
            "creator": data[2],
            "exists": data[3],
            "closed": data[4]
        }
