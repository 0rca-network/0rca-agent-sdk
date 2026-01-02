import os
import json
from eth_account import Account

class AgentWalletManager:
    """
    Manages the internal IDENTITY wallet for the agent.
    This wallet is for identification/A2A purposes only, NOT for holding funds.
    """
    def __init__(self, wallet_file_path: str):
        self.path = wallet_file_path
        self.address = None
        self._private_key = None
        self._initialize()

    def _initialize(self):
        # NOTE: Wallet encryption can be added here in a production implementation
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                    self.address = data["address"]
                    self._private_key = data["private_key"]
            except Exception as e:
                # If file is corrupted, generate new one (or could error out depending on policy)
                self._generate_new()
        else:
            self._generate_new()

    def _generate_new(self):
        account = Account.create()
        self.address = account.address
        self._private_key = account.key.hex()
        
        # Persist locally so it survives restarts
        with open(self.path, "w") as f:
            json.dump({
                "address": self.address,
                "private_key": self._private_key
            }, f)
