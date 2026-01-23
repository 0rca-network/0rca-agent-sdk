import os
import time
import threading
import requests
import json
import traceback
from typing import Callable, List, Optional, Dict, Any

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS

from .config import AgentConfig
from .core.payment import PaymentManager, ToolPaywallError
from .core.persistence import init_db, log_request, update_request_success, update_request_failed
from .core.a2a import AgentRegistry, A2AProtocol
from .core.wallet import AgentWalletManager
from .core.task_context import TaskContext, TaskStatus
from .contracts.task_escrow import TaskEscrowClient

class AgentServer:
    """
    Agent Server implementing x402, A2A, and multi-backend support.
    """

    def __init__(self, config: AgentConfig, handler: Callable[[str], str]):
        self.config = config
        self.config.validate()
        
        # 0. Setup File Logging
        self.log_file_path = "/tmp/agent_server.log"
        # Reset log on start
        try:
            with open(self.log_file_path, "w", encoding="utf-8") as f:
                f.write("--- SERVER STARTING ---\n")
        except PermissionError:
            # Fallback for environments where /tmp isn't writable or root restricted
            print(f"Warning: Cannot write to {self.log_file_path}. Continuing without file logs.")
            self.log_file_path = None
        
        self._log("Agent Server Initializing...")

        # 1. Initialize Persistence
        init_db(self.config.db_path)
        
        # 2. Initialize Payment
        self.payment = PaymentManager(self.config)

        # 3. Initialize Identity Wallet
        self.wallet_manager = AgentWalletManager(self.config.identity_wallet_path)
        self.agent_wallet_address = self.wallet_manager.address
        self._agent_private_key = self.wallet_manager._private_key

        self._log(f"Agent Identity Wallet: {self.agent_wallet_address}")
        self._log(f"Creator Payout Wallet: {self.config.wallet_address}")

        # 4. Initialize A2A
        self.registry = AgentRegistry()
        try:
            self.registry.register(
                agent_id=self.config.agent_id,
                endpoint=f"http://localhost:8000", 
                name=self.config.agent_id
            )
        except Exception as e:
            self._log(f"A2A Registration Error: {e}")

        # 5. Initialize Sovereign Vault
        self.vault_client = None
        if handler and hasattr(handler, "vault_client"):
            self.vault_client = handler.vault_client
            
        if not self.vault_client and os.getenv("AGENT_VAULT"):
            from .contracts.agent_vault import OrcaAgentVaultClient
            self.vault_client = OrcaAgentVaultClient(self.config, os.getenv("AGENT_VAULT"), self._agent_private_key)
        
        if self.vault_client:
            self._log(f"Sovereign Vault Linked: {self.vault_client.vault_address}")
        else:
            self._log("No Sovereign Vault linked.")

        self.a2a = A2AProtocol(self.config.agent_id, self.registry)

        # 5. Initialize Backend
        self.backend = self._load_backend(handler)
        
        # 6. Setup Flask
        self.app = Flask(__name__)
        self.app.agent_server = self 
        CORS(self.app)
        self._register_routes()

    def _log(self, msg: str):
        import datetime
        import sys
        # Set stdout encoding to utf-8 if possible
        if hasattr(sys.stdout, 'reconfigure'):
            try:
                sys.stdout.reconfigure(encoding='utf-8')
            except: pass

        ts = datetime.datetime.now().isoformat()
        line = f"[{ts}] {msg}\n"
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception: pass
        
        try:
            print(msg, flush=True)
        except UnicodeEncodeError:
            # Fallback for old consoles
            print(msg.encode('ascii', 'ignore').decode('ascii'), flush=True)

    def _load_backend(self, handler: Any):
        backend_type = self.config.ai_backend
        if backend_type == "crewai":
            from .backends.crewai_backend import CrewAIBackend
            backend = CrewAIBackend()
        elif backend_type == "agno":
            from .backends.agno_backend import AgnoBackend
            backend = AgnoBackend()
        elif backend_type == "crypto_com":
            from .backends.crypto_com_backend import CryptoComBackend
            backend = CryptoComBackend()
        else:
            from .backends.crewai_backend import CrewAIBackend
            backend = CrewAIBackend()
            
        backend.initialize(self.config, handler)
        return backend

    def _register_routes(self) -> None:
        app = self.app

        @app.route("/", methods=["GET"])
        def health():
            return f"0rca Agent SDK ({self.config.ai_backend}) Running"

        @app.route("/status", methods=["GET"])
        def get_status():
            try:
                rep = self.registry.on_chain.get_agent_reputation(self.config.on_chain_id)
                val = self.registry.on_chain.get_validation_status(self.config.on_chain_id)
                return jsonify({
                    "agent_id": self.config.agent_id,
                    "on_chain_id": self.config.on_chain_id,
                    "reputation": rep,
                    "validation": val,
                    "earnings_vault": self.vault_client.vault_address if self.vault_client else "Not Deployed",
                    "pending_balance_usdc": (self.vault_client.get_balance() / 10**6) if self.vault_client else 0.0,
                    "identity_wallet": self.agent_wallet_address
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/withdraw", methods=["POST"])
        def withdraw_earnings():
            try:
                if not self.vault_client: return jsonify({"error": "No vault configured"}), 400
                tx_hash = self.vault_client.withdraw()
                return jsonify({"status": "success", "txHash": tx_hash})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/agent", methods=["POST"])
        def handle_agent_request():
            self._log("!!! handle_agent_request CALLED !!!")
            try:
                data = request.json or {}
                prompt = data.get("prompt", "")
                if not prompt:
                    return jsonify({"error": "Prompt required"}), 400
                
                req_id = log_request(self.config.db_path, prompt)
                task_id = data.get("taskId") or request.headers.get("X-TASK-ID")
                
                if not task_id:
                     return jsonify({"error": "taskId required"}), 400

                self._log(f"Received Request: taskId={task_id}, prompt='{prompt[:50]}...'")

                # Check Payment
                signed_b64 = request.headers.get("X-PAYMENT")
                is_test_bypass = request.headers.get("X-TEST-BYPASS") == "true"
                if is_test_bypass: self._log("Bypassing x402 check (X-TEST-BYPASS=true)")

                price_val = 0
                try: price_val = float(self.config.price)
                except: pass

                if not signed_b64 and not is_test_bypass and price_val > 0:
                    self._log("x402 challenge issued.")
                    accepts = self.payment.build_requirements()
                    challenge = self.payment.encode_challenge(accepts)
                    resp = make_response(jsonify({"message": "Payment required", "accepts": accepts}), 402)
                    resp.headers["PAYMENT-REQUIRED"] = challenge
                    resp.headers["Access-Control-Expose-Headers"] = "PAYMENT-REQUIRED"
                    return resp

                # Run Backend
                try:
                    self._log("Executing backend...")
                    result = self.backend.handle_prompt(prompt)
                    self._log("Backend finished successfully.")
                    
                    # --- AUTOMATIC TASK ESCROW SPEND ---
                    if task_id and price_val > 0 and self.vault_client:
                        try:
                            amount_units = int(price_val * 10**6)
                            self._log(f"Attempting task spend: {task_id}, amount: {amount_units}")
                            # Use kwargs to be safe with different client signatures
                            if hasattr(self.vault_client, "spend"):
                                tx_hash = self.vault_client.spend(task_id=task_id, amount=amount_units)
                            else:
                                raise AttributeError("Vault client has no spend method")
                            self._log(f"Task spend successful: {tx_hash}")
                        except Exception as spend_err:
                            self._log(f"Task spend failed: {spend_err}")
                    
                    update_request_success(self.config.db_path, req_id, result, signed_b64)
                    return jsonify({"result": result, "taskId": task_id}), 200
                except ToolPaywallError as e:
                    self._log(f"Tool paywall triggered: {e.tool_name}")
                    accepts = self.payment.build_requirements(tool_name=e.tool_name)
                    challenge = self.payment.encode_challenge(accepts)
                    resp = make_response(jsonify({"message": f"Tool {e.tool_name} requires payment", "tool": e.tool_name, "accepts": accepts}), 402)
                    resp.headers["PAYMENT-REQUIRED"] = challenge
                    return resp
                except Exception as e:
                    err_trace = traceback.format_exc()
                    self._log(f"Backend execution failed: {e}")
                    update_request_failed(self.config.db_path, req_id, str(e))
                    return jsonify({"error": "Backend execution failed", "details": str(e), "trace": err_trace}), 500

            except Exception as e:
                self._log(f"Internal error: {e}")
                return jsonify({"error": "Internal error", "details": str(e)}), 500

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        self._log(f"Server starting on {host}:{port}")
        self.app.run(host=host, port=port, debug=debug)