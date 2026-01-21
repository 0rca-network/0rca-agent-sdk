from typing import Dict, Any, Optional, List
import json
import os
import requests
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from crewai.tools import tool

from .agent import OrcaAgent
from .config import AgentConfig

class ContractAgent(OrcaAgent):
    """
    An agent specifically designed to interact with smart contracts on Cronos and other EVM chains.
    """

    def __init__(
        self,
        name: str,
        model: str,
        system_prompt: str,
        tools: Optional[List[Dict[str, Any]]] = None,
        credits_file: Optional[str] = None,
        price: str = "0.0",
        api_key: Optional[str] = None,
        vault_address: Optional[str] = None,
        rpc_urls: Optional[Dict[str, str]] = None
    ):
        # Default RPC URLs
        self.rpc_urls = rpc_urls or {
            "cronos": "https://evm.cronos.org",
            "ethereum": "https://eth.llamarpc.com",
            "base": "https://mainnet.base.org",
            "arbitrum": "https://arb1.arbitrum.io/rpc"
        }
        
        # Internal state for loaded contracts
        self._loaded_contracts = {} # contract_id -> {chain, address, abi, contract_obj, w3}
        
        # Initialize base OrcaAgent
        super().__init__(
            name=name,
            model=model,
            system_prompt=system_prompt,
            tools=tools,
            credits_file=credits_file,
            price=price,
            api_key=api_key,
            vault_address=vault_address
        )
        
        # Register the contract tools
        self._register_contract_tools()
        
        # Update backend options to include newly added native tools
        if hasattr(self, "backend_options"):
            self.backend_options["native_tools"] = self.native_tools

    def _register_contract_tools(self):
        """Registers the smart contract interaction tools."""
        
        @tool("load_contract")
        def load_contract(chain: str, address: str) -> str:
            """
            Load an EVM smart contract ABI and expose callable functions.
            Supported chains: cronos, ethereum, base, arbitrum.
            """
            chain = chain.lower()
            if chain not in self.rpc_urls:
                return json.dumps({"error": f"Unsupported chain: {chain}"})
            
            try:
                rpc_url = self.rpc_urls[chain]
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                
                address = w3.to_checksum_address(address)
                
                # Fetch ABI (Simplified version, ideally uses explorer API)
                abi = self._fetch_abi(chain, address)
                if not abi:
                    return json.dumps({"error": f"Could not fetch ABI for {address} on {chain}"})
                
                contract_obj = w3.eth.contract(address=address, abi=abi)
                
                # Try to get a name for the contract if possible
                contract_id = self._get_contract_name(abi) or f"contract_{address[:8]}"
                
                self._loaded_contracts[contract_id] = {
                    "chain": chain,
                    "address": address,
                    "abi": abi,
                    "contract": contract_obj,
                    "w3": w3
                }
                
                functions = []
                for item in abi:
                    if item.get("type") == "function":
                        functions.append({
                            "name": item.get("name"),
                            "inputs": [i.get("type") for i in item.get("inputs", [])]
                        })
                
                return json.dumps({
                    "contractId": contract_id,
                    "functions": functions
                }, indent=2)
                
            except Exception as e:
                return json.dumps({"error": str(e)})

        @tool("describe_function")
        def describe_function(contractId: str, functionName: str) -> str:
            """Get detailed parameter info for a contract function."""
            if contractId not in self._loaded_contracts:
                return json.dumps({"error": f"Contract {contractId} not loaded"})
            
            contract_info = self._loaded_contracts[contractId]
            abi = contract_info["abi"]
            
            for item in abi:
                if item.get("type") == "function" and item.get("name") == functionName:
                    return json.dumps(item, indent=2)
            
            return json.dumps({"error": f"Function {functionName} not found in contract {contractId}"})

        @tool("simulate_contract_call")
        def simulate_contract_call(contractId: str, functionName: str, args: Dict[str, Any], value: str = "0") -> str:
            """
            Simulate a smart contract call without sending transaction.
            Args should be a dictionary of parameter names and values.
            Value is the amount of native token (wei) to send if payable.
            """
            if contractId not in self._loaded_contracts:
                return json.dumps({"error": f"Contract {contractId} not loaded"})
            
            contract_info = self._loaded_contracts[contractId]
            contract = contract_info["contract"]
            w3 = contract_info["w3"]
            
            try:
                # Prepare arguments in order
                func_abi = next(i for i in contract_info["abi"] if i.get("name") == functionName)
                ordered_args = []
                for input_def in func_abi.get("inputs", []):
                    ordered_args.append(args.get(input_def["name"]))
                
                # Simulate
                # Use public key of agent for simulation if available
                from_address = self.config.wallet_address or "0x0000000000000000000000000000000000000000"
                
                call_data = {
                    "from": from_address,
                    "value": int(value)
                }
                
                # Check if it's a read or write call
                if func_abi.get("stateMutability") in ["view", "pure"]:
                    result = contract.functions[functionName](*ordered_args).call(call_data)
                    return json.dumps({
                        "success": True,
                        "returnValue": str(result)
                    })
                else:
                    # Simulation for state-changing calls
                    gas_estimate = contract.functions[functionName](*ordered_args).estimate_gas(call_data)
                    return json.dumps({
                        "success": True,
                        "gasEstimate": str(gas_estimate),
                        "returnValue": None
                    })
                    
            except Exception as e:
                return json.dumps({"success": False, "error": str(e)})

        @tool("execute_contract_call")
        def execute_contract_call(contractId: str, functionName: str, args: Dict[str, Any], value: str = "0") -> str:
            """
            Execute smart contract function on-chain.
            """
            if contractId not in self._loaded_contracts:
                return json.dumps({"error": f"Contract {contractId} not loaded"})
            
            # Safety Filter
            blocked_functions = ["setOwner", "upgradeTo", "setImplementation", "transferOwnership"]
            if functionName in blocked_functions:
                return json.dumps({"error": f"Function {functionName} is blocked for safety reasons. Manual confirmation required."})
            
            if functionName == "approve":
                # Check for MAX approval
                for arg_val in args.values():
                    if str(arg_val).startswith("0xffffff") or str(arg_val) == str(2**256 - 1):
                        return json.dumps({"error": "approving MAX amount is blocked for safety. Please specify a smaller amount."})

            # Value Limit
            USER_LIMIT = Web3.to_wei(1, 'ether') # Example limit
            if int(value) > USER_LIMIT:
                return json.dumps({"error": f"Value {value} exceeds safety limit of 1 ETH."})

            contract_info = self._loaded_contracts[contractId]
            contract = contract_info["contract"]
            w3 = contract_info["w3"]
            private_key = self._private_key
            
            if not private_key:
                return json.dumps({"error": "No private key available for signing transactions"})
            
            try:
                account = w3.eth.account.from_key(private_key)
                from_address = account.address
                
                func_abi = next(i for i in contract_info["abi"] if i.get("name") == functionName)
                ordered_args = []
                for input_def in func_abi.get("inputs", []):
                    ordered_args.append(args.get(input_def["name"]))
                
                nonce = w3.eth.get_transaction_count(from_address)
                chain_id = w3.eth.chain_id
                
                tx_params = {
                    'chainId': chain_id,
                    'gasPrice': w3.eth.gas_price,
                    'nonce': nonce,
                    'value': int(value)
                }
                
                # Build transaction
                tx = contract.functions[functionName](*ordered_args).build_transaction(tx_params)
                
                # Sign
                signed_tx = w3.eth.account.sign_transaction(tx, private_key)
                
                # Send
                tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
                
                return json.dumps({
                    "txHash": w3.to_hex(tx_hash),
                    "status": "submitted"
                })
                
            except Exception as e:
                return json.dumps({"error": str(e)})

        @tool("read_contract")
        def read_contract(contractId: str, functionName: str, args: Optional[Dict[str, Any]] = None) -> str:
            """Call view or pure function from contract."""
            if contractId not in self._loaded_contracts:
                return json.dumps({"error": f"Contract {contractId} not loaded"})
            
            contract_info = self._loaded_contracts[contractId]
            contract = contract_info["contract"]
            
            try:
                func_abi = next(i for i in contract_info["abi"] if i.get("name") == functionName)
                ordered_args = []
                if args:
                    for input_def in func_abi.get("inputs", []):
                        ordered_args.append(args.get(input_def["name"]))
                
                result = contract.functions[functionName](*ordered_args).call()
                return json.dumps({"result": str(result)}, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})

        # Add tools to native_tools list so OrcaAgent (and backends) can find them
        self.native_tools.extend([
            load_contract, 
            describe_function, 
            simulate_contract_call, 
            execute_contract_call, 
            read_contract
        ])

    def _fetch_abi(self, chain: str, address: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch ABI from explorer or cache."""
        # Check cache first (Simple file-based cache)
        cache_dir = os.path.join(os.getcwd(), ".abi_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{chain}_{address}.json")
        
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                return json.load(f)
        
        # Explorer APIs
        api_urls = {
            "cronos": "https://api.cronoscan.com/api",
            "ethereum": "https://api.etherscan.io/api",
            "base": "https://api.basescan.org/api",
            "arbitrum": "https://api.arbiscan.io/api"
        }
        
        api_key_env = {
            "cronos": "CRONOSCAN_API_KEY",
            "ethereum": "ETHERSCAN_API_KEY",
            "base": "BASESCAN_API_KEY",
            "arbitrum": "ARBISCAN_API_KEY"
        }
        
        api_url = api_urls.get(chain)
        api_key = os.getenv(api_key_env.get(chain, ""))
        
        if not api_url:
            return None
        
        params = {
            "module": "contract",
            "action": "getabi",
            "address": address,
            "apikey": api_key
        }
        
        try:
            response = requests.get(api_url, params=params)
            data = response.json()
            if data.get("status") == "1":
                abi = json.loads(data.get("result"))
                # Save to cache
                with open(cache_file, "w") as f:
                    json.dump(abi, f)
                return abi
        except Exception as e:
            print(f"Error fetching ABI: {e}")
            
        return None

    def _get_contract_name(self, abi: List[Dict[str, Any]]) -> Optional[str]:
        """Attempts to find a name for the contract from the ABI or bytecode."""
        # In a real impl, we'd check common function like name() or look at explorer metadata
        return None
