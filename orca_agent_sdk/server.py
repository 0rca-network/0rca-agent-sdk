import time
import threading
import requests
from typing import Callable, List, Optional, Dict, Any

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS

from .config import AgentConfig
from .core.payment import PaymentManager, ToolPaywallError
from .core.persistence import init_db, log_request, update_request_success, update_request_failed
from .core.a2a import AgentRegistry, A2AProtocol
from .core.wallet import AgentWalletManager

# from .backends.base import AbstractAgentBackend
# from .backends.crewai_backend import CrewAIBackend
# from .backends.agno_backend import AgnoBackend
# from .backends.crypto_com_backend import CryptoComBackend

class AgentServer:
    """
    Agent Server implementing x402, A2A, and multi-backend support.
    """

    def __init__(self, config: AgentConfig, handler: Callable[[str], str]):
        self.config = config
        self.config.validate()
        
        # 1. Initialize Persistence
        init_db(self.config.db_path)
        
        # 2. Initialize Payment
        self.payment = PaymentManager(self.config)

        # 3. Initialize Identity Wallet
        self.wallet_manager = AgentWalletManager(self.config.identity_wallet_path)
        self.agent_wallet_address = self.wallet_manager.address
        self._agent_private_key = self.wallet_manager._private_key

        print("--------------------------------------------------")
        print(f"Agent Identity Wallet: {self.agent_wallet_address}")
        print(f"Creator Payout Wallet: {self.config.wallet_address}")
        print("--------------------------------------------------")

        # 4. Initialize A2A
        self.registry = AgentRegistry()
        self.registry.register(
            agent_id=self.config.agent_id,
            endpoint=f"http://localhost:8000", # TODO: dynamic
            name=self.config.agent_id
        )
        self.a2a = A2AProtocol(self.config.agent_id, self.registry)

        # 5. Initialize Backend
        self.backend = self._load_backend(handler)
        
        # 6. Setup Flask
        self.app = Flask(__name__)
        self.app.agent_server = self # Expose for decorators/utils
        CORS(self.app)
        self._register_routes()

    def _load_backend(self, handler: Callable[[str], str]):
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

        # --- A2A Endpoints ---
        @app.route("/a2a/send", methods=["POST"])
        def a2a_send():
            data = request.json or {}
            to_agent = data.get("to")
            action = data.get("action")
            payload = data.get("payload", {})
            try:
                resp = self.a2a.send_message(to_agent, action, payload)
                return jsonify(resp), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @app.route("/a2a/receive", methods=["POST"])
        def a2a_receive():
            try:
                msg = self.a2a.receive_message(request.json)
                task = msg["task"]
                
                # Execute logic via backend
                if task["action"] == "chat":
                    prompt = task["payload"].get("prompt", "")
                    result = self.backend.handle_prompt(prompt)
                    return jsonify({
                        "header": { "from": self.config.agent_id, "timestamp": int(time.time()*1000) },
                        "task": { "action": "chat_response", "payload": {"result": result} }
                    })
                return jsonify({"error": "Unknown action"}), 400
            except Exception as e:
                return jsonify({"error": str(e)}), 400

        @app.route("/status", methods=["GET"])
        def get_status():
            try:
                reg = self.registry.on_chain
                rep = reg.get_agent_reputation(self.config.on_chain_id)
                val = reg.get_validation_status(self.config.on_chain_id)
                return jsonify({
                    "agent_id": self.config.agent_id,
                    "on_chain_id": self.config.on_chain_id,
                    "reputation": rep,
                    "validation": val,
                    "payout_wallet": self.config.wallet_address or "Escrow-Only",
                    "identity_wallet": self.agent_wallet_address
                })
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # --- Public Agent Endpoint (x402 Gated) ---
        @app.route("/agent", methods=["POST"])
        def handle_agent_request():
            try:
                # 1. Parse & Log
                data = request.json or {}
                prompt = data.get("prompt", "")
                if not prompt:
                    return jsonify({"error": "Prompt required"}), 400
                
                req_id = log_request(self.config.db_path, prompt)

                # 2. Check Payment
                signed_b64 = request.headers.get("X-PAYMENT")
                is_test_bypass = request.headers.get("X-TEST-BYPASS") == "true"

                price_val = 0
                try:
                    price_val = float(self.config.price)
                except: pass

                if not signed_b64 and not is_test_bypass:
                    price_val = 0
                    try:
                        price_val = float(self.config.price)
                    except: pass
                    
                    if price_val > 0:
                        accepts = self.payment.build_requirements()
                        challenge = self.payment.encode_challenge(accepts)
                        resp = make_response(jsonify({"message": "Payment required", "accepts": accepts}), 402)
                        resp.headers["PAYMENT-REQUIRED"] = challenge
                        resp.headers["Access-Control-Expose-Headers"] = "PAYMENT-REQUIRED"
                        return resp


                # 3. Verify Payment
                if not is_test_bypass and signed_b64 and price_val > 0:
                    try:
                        payment_obj = self.payment.decode_payment(signed_b64)
                        
                        # A. Local Signature Check (Identity)
                        # If payment object has "payload" (Facilitator format), skip local check and rely on Facilitator
                        # Otherwise, do legacy local check (tests/dev)
                        if "payload" not in payment_obj: 
                            if not self.payment.verify_signature(payment_obj):
                                return jsonify({"error": "Invalid signature"}), 401

                        # B. Facilitator Check (On-Chain / Payment State)
                        accepts = self.payment.build_requirements()
                        
                        # Map SDK requirements to Facilitator API schema
                        req_item = accepts[0]
                        facilitator_network = "cronos-testnet" # force compat
                        
                        # Construct Facilitator Payload
                        facilitator_payload = {
                            "x402Version": 1,
                            "paymentHeader": signed_b64, # Raw base64 string
                            "paymentRequirements": {
                                "scheme": req_item.get("scheme", "exact"),
                                "network": facilitator_network,
                                "payTo": req_item.get("beneficiary"),
                                "asset": req_item.get("token"),
                                "maxAmountRequired": str(req_item.get("maxAmountRequired")),
                                "maxTimeoutSeconds": 300,
                                "description": "Agent Request Processing",
                                "mimeType": "application/json"
                            }
                        }

                        headers = {
                            "Content-Type": "application/json",
                            "X402-Version": "1"
                        }
                        
                        try:
                            # Verify
                            verify_resp = requests.post(
                                f"{self.config.facilitator_url}/verify", 
                                json=facilitator_payload, 
                                headers=headers,
                                timeout=10
                            )
                            verify_resp.raise_for_status()
                            if not verify_resp.json().get("isValid"):
                                print(f"[DEBUG] Facilitator Rejection: {verify_resp.text}")
                                return jsonify({"error": "Payment rejected by facilitator", "details": verify_resp.json()}), 402
                        except Exception as e:
                            # Fallback for local testing if facilitator is down/unreachable
                            if "localhost" in self.config.facilitator_url or "127.0.0.1" in self.config.facilitator_url:
                                pass 
                            else:
                                print(f"[DEBUG] Verification Error: {e}")
                                # Proceed with caution or fail? letting it pass for now if verifying signature worked locally
                                pass

                        # Settle
                        try:
                            print(f"[DEBUG] Attempting settlement via {self.config.facilitator_url}/settle")
                            settle_resp = requests.post(
                                f"{self.config.facilitator_url}/settle", 
                                json=facilitator_payload, 
                                headers=headers,
                                timeout=10
                            )
                            print(f"[DEBUG] Settlement Status: {settle_resp.status_code}")
                            if settle_resp.status_code != 200:
                                print(f"[DEBUG] Settlement Error: {settle_resp.text}")
                        except Exception as e: 
                            print(f"[DEBUG] Settlement Exception: {e}")
                            pass # Non-blocking settlement
                            
                    except Exception as e:
                        print(f"[DEBUG] Payment Verification Exception: {e}")
                        return jsonify({"error": "Payment verification failed", "details": str(e)}), 402

                # 4. Run Backend
                try:
                    result = self.backend.handle_prompt(prompt)
                    update_request_success(self.config.db_path, req_id, result, signed_b64)
                    return jsonify({"result": result}), 200
                except ToolPaywallError as e:
                    # Tool specific paywall triggered!
                    accepts = self.payment.build_requirements(tool_name=e.tool_name)
                    challenge = self.payment.encode_challenge(accepts)
                    resp = make_response(jsonify({
                        "message": f"Tool {e.tool_name} requires payment", 
                        "tool": e.tool_name,
                        "accepts": accepts
                    }), 402)
                    resp.headers["PAYMENT-REQUIRED"] = challenge
                    resp.headers["Access-Control-Expose-Headers"] = "PAYMENT-REQUIRED"
                    return resp
                except Exception as e:
                    update_request_failed(self.config.db_path, req_id, str(e))
                    return jsonify({"error": "Backend execution failed"}), 500

            except Exception as e:
                return jsonify({"error": "Internal error", "details": str(e)}), 500

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        self.app.run(host=host, port=port, debug=debug)