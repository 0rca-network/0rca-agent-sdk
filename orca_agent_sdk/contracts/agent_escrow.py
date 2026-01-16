from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from ..config import AgentConfig
from ..constants import AGENT_ESCROW
from . import load_abi

class AgentEscrowClient:
    def __init__(self, config: AgentConfig, private_key: str):
        self.config = config
        self.private_key = private_key
        
        # Initialize Web3
        rpc_url = getattr(config, "rpc_url", "https://evm-t3.cronos.org")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        
        if not AGENT_ESCROW:
            raise ValueError("AGENT_ESCROW address not configured.")
            
        self.contract_address = self.w3.to_checksum_address(AGENT_ESCROW)
        self.abi = load_abi("AgentEscrow")
        
        self.contract = self.w3.eth.contract(address=self.contract_address, abi=self.abi)
        self.account = self.w3.eth.account.from_key(private_key)

        try:
            self.chain_id = int(config.chain_caip.split(":")[-1])
        except:
            self.chain_id = 338

    def withdraw(self, agent_id: int) -> str:
        """
        Withdraws all accumulated earnings for the agent.
        """
        nonce = self.w3.eth.get_transaction_count(self.account.address)
        
        tx = self.contract.functions.withdraw(
            agent_id
        ).build_transaction({
            'chainId': self.chain_id,
            'gas': 200000,
            'gasPrice': self.w3.eth.gas_price,
            'nonce': nonce,
        })
        
        signed_tx = self.w3.eth.account.sign_transaction(tx, self.private_key)
        print(f"[AgentEscrow] Withdrawing earnings for agent {agent_id}...", flush=True)
        tx_hash = self.w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        return self.w3.to_hex(tx_hash)

    def get_balance(self, agent_id: int) -> int:
        """
        Returns the current earnings balance in the vault.
        """
        return self.contract.functions.agentEarnings(agent_id).call()
