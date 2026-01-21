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
        
        # Pre-register our specialized tools
        contract_tools = self._get_contract_tools()
        
        if tools is None:
            tools = []
        
        # Combine provided tools with our contract tools
        combined_tools = tools + contract_tools
        
        # Initialize base OrcaAgent
        super().__init__(
            name=name,
            model=model,
            system_prompt=system_prompt,
            tools=combined_tools,
            credits_file=credits_file,
            price=price,
            api_key=api_key,
            vault_address=vault_address
        )

    def _get_contract_tools(self):
        """Returns the list of smart contract interaction tools."""
        
        @tool("load_contract")
        def load_contract(chain: str, address: str, abi_json: Optional[str] = None) -> str:
            """
            Load an EVM smart contract ABI and expose callable functions.
            Supported chains: cronos, ethereum, base, arbitrum.
            Optional: abi_json can be provided if automatic fetching fails.
            """
            chain = chain.lower()
            if chain not in self.rpc_urls:
                return json.dumps({"error": f"Unsupported chain: {chain}"})
            
            try:
                rpc_url = self.rpc_urls[chain]
                w3 = Web3(Web3.HTTPProvider(rpc_url))
                w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
                
                address = w3.to_checksum_address(address)
                
                # Fetch or use provided ABI
                if abi_json:
                    try:
                        abi = json.loads(abi_json)
                    except:
                        return json.dumps({"error": "Invalid ABI JSON provided"})
                else:
                    abi = self._fetch_abi(chain, address)
                
                if not abi:
                    return json.dumps({
                        "error": f"Could not fetch ABI for {address} on {chain}. Please provide ABI manually.",
                        "manual_instruction": "You can provide the ABI as a JSON string in the 'abi_json' parameter."
                    })
                
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
                    # Handle some common types
                    val = args.get(input_def["name"])
                    if input_def["type"].startswith("uint") or input_def["type"].startswith("int"):
                        val = int(val) if val is not None else 0
                    ordered_args.append(val)
                
                # Simulate
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
                return json.dumps({
                    "success": False, 
                    "error": str(e),
                    "tip": "Check if arguments are correct and you have enough balance/allowance."
                })

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
                    val = args.get(input_def["name"])
                    if input_def["type"].startswith("uint") or input_def["type"].startswith("int"):
                        val = int(val) if val is not None else 0
                    ordered_args.append(val)
                
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
                        val = args.get(input_def["name"])
                        if input_def["type"].startswith("uint") or input_def["type"].startswith("int"):
                            val = int(val) if val is not None else 0
                        ordered_args.append(val)
                
                result = contract.functions[functionName](*ordered_args).call()
                return json.dumps({"result": str(result)}, indent=2)
            except Exception as e:
                return json.dumps({"error": str(e)})

        return [load_contract, describe_function, simulate_contract_call, execute_contract_call, read_contract]

    def _fetch_abi(self, chain: str, address: str) -> Optional[List[Dict[str, Any]]]:
        """Fetch ABI from explorer or cache."""
        # 0. Protocol-specific Built-in Fallbacks (Optimized for Moonlander)
        BUILT_IN_ABIS = {
            "0xE6F6351fb66f3a35313fEEFF9116698665FBEeC9".lower(): [
                {"name": "openPosition", "type": "function", "stateMutability": "payable", "inputs": [{"name": "marketId", "type": "uint256"}, {"name": "isLong", "type": "bool"}, {"name": "collateralUsd", "type": "uint256"}, {"name": "leverage", "type": "uint256"}]},
                {"name": "closePosition", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "positionId", "type": "uint256"}]},
                {"name": "getPosition", "type": "function", "stateMutability": "view", "inputs": [{"name": "positionId", "type": "uint256"}], "outputs": [{"name": "pos", "type": "tuple", "components": [{"name": "owner", "type": "address"}, {"name": "marketId", "type": "uint256"}, {"name": "isLong", "type": "bool"}]}]},
                {"name": "getPoolInfo", "type": "function", "stateMutability": "view", "inputs": [], "outputs": [{"name": "info", "type": "tuple", "components": [{"name": "totalAUM", "type": "uint256"}, {"name": "mlpPrice", "type": "uint256"}]}]}
            ],
            "0xb4c70008528227e0545Db5BA4836d1466727DF13".lower(): [
                {"name": "name", "type": "function", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "string"}]},
                {"name": "symbol", "type": "function", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "string"}]},
                {"name": "balanceOf", "type": "function", "stateMutability": "view", "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
                {"name": "transfer", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "recipient", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]},
                {"name": "approve", "type": "function", "stateMutability": "nonpayable", "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}], "outputs": [{"name": "", "type": "bool"}]}
            ]
        }
        
        if address.lower() in BUILT_IN_ABIS:
            print(f"[{self.name}] Using built-in ABI for protocol contract {address}")
            return BUILT_IN_ABIS[address.lower()]

        # 1. Check cache first
        cache_dir = os.path.join(os.getcwd(), ".abi_cache")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, f"{chain}_{address}.json")
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    return json.load(f)
            except: pass
        
        # 2. Explorer APIs
        api_urls = {
            "cronos": "https://explorer-api.cronos.org/mainnet/api/v2",
            "ethereum": "https://api.etherscan.io/api",
            "base": "https://api.basescan.org/api",
            "arbitrum": "https://api.arbiscan.io/api"
        }
        
        api_url = api_urls.get(chain)
        if not api_url:
            return None
            
        def fetch_raw(addr):
            params = {
                "module": "contract",
                "action": "getabi",
                "address": addr
            }
            # Check for API key in env or use provided default for Cronos
            api_key_env = f"{chain.upper()}SCAN_API_KEY"
            if os.getenv(api_key_env):
                params["apikey"] = os.getenv(api_key_env)
            elif chain == "cronos":
                params["apikey"] = "okUm6990qPhrWWyuUHbKekc6biHBRJn8"
            elif chain == "ethereum" and os.getenv("ETHERSCAN_API_KEY"):
                params["apikey"] = os.getenv("ETHERSCAN_API_KEY")
            
            try:
                print(f"[{self.name}] Fetching ABI from {api_url} for {addr}...")
                resp = requests.get(api_url, params=params, timeout=12)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "1":
                        res = data.get("result")
                        return json.loads(res) if isinstance(res, str) else res
                    else:
                        print(f"[{self.name}] Explorer error: {data.get('message') or data.get('result')}")
            except Exception as e:
                print(f"[{self.name}] Error fetching raw ABI: {e}")
            return None

        # Try to detect if it's a proxy first (on Cronos)
        if chain == "cronos":
            params = {"module": "contract", "action": "getsourcecode", "address": address, "apikey": "okUm6990qPhrWWyuUHbKekc6biHBRJn8"}
            try:
                s_resp = requests.get(api_url, params=params, timeout=12)
                if s_resp.status_code == 200:
                    s_data = s_resp.json()
                    if s_data.get("status") == "1" and s_data.get("result"):
                        res = s_data.get("result")[0]
                        if res.get("Proxy") == "1" and res.get("Implementation"):
                            impl = res.get("Implementation")
                            print(f"[{self.name}] Proxy detected! Following implementation: {impl}")
                            # Try getabi on implementation
                            abi = fetch_raw(impl)
                            if abi and any(x.get('type') == 'function' for x in abi):
                                return abi
            except: pass

        # Fallback to direct ABI fetch
        abi = fetch_raw(address)
        if abi:
            try:
                with open(cache_file, "w") as f:
                    json.dump(abi, f)
            except: pass
            return abi
            
        return None

    def _get_contract_name(self, abi: List[Dict[str, Any]]) -> Optional[str]:
        # Try to find a hint in the ABI functions
        return None
