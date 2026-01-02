import json
import secrets
import requests
import threading
import time
from typing import Callable, List, Optional, Dict, Any

from flask import Flask, jsonify, request, make_response
from flask_cors import CORS
import sqlite3
from x402 import X402

from .config import AgentConfig


# --- Internal DB helpers ---


def _init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS request_log (
                request_id TEXT PRIMARY KEY,
                prompt TEXT,
                payment_token TEXT,
                status TEXT NOT NULL,
                created_at INTEGER DEFAULT (unixepoch()),
                completed_at INTEGER,
                output TEXT
            );
            """
        )
        conn.commit()
    finally:
        conn.close()


def _db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _log_request(db_path: str, prompt: str) -> str:
    request_id = secrets.token_hex(8)
    with _db(db_path) as conn:
        conn.execute(
            "INSERT INTO request_log (request_id, prompt, status) VALUES (?, ?, 'pending')",
            (request_id, prompt),
        )
        conn.commit()
    return request_id


def _update_request_success(db_path: str, request_id: str, output: str, payment_token: str = "") -> None:
    with _db(db_path) as conn:
        conn.execute(
            """
            UPDATE request_log 
            SET status = 'succeeded', output = ?, payment_token = ?, completed_at = unixepoch() 
            WHERE request_id = ?
            """,
            (output, payment_token, request_id),
        )
        conn.commit()


def _update_request_failed(db_path: str, request_id: str, error: str) -> None:
    with _db(db_path) as conn:
        conn.execute(
            "UPDATE request_log SET status = 'failed', output = ? WHERE request_id = ?",
            (error, request_id),
        )
        conn.commit()


# --- Agent Server ---


class AgentServer:
    """
    Agent Server implementing the x402 Payment Protocol.
    
    Flow:
    1. Client POSTs to /agent (or configured endpoint).
    2. Server checks for X-PAYMENT header.
    3. If missing/invalid -> Returns 402 with X402 challenge.
    4. Client signs challenge and retries.
    5. Server verifies payment via Facilitator.
    6. Server executes agent handler and returns result.
    """

    def __init__(self, config: AgentConfig, handler: Callable[[str], str]):
        self.config = config
        self.config.validate()
        self.handler = handler
        
        # Initialize x402 util
        self.x402 = X402()

        _init_db(self.config.db_path)

        self.app = Flask(__name__)
        CORS(self.app)
        self._register_routes()

    def _build_payment_requirements(self) -> List[Dict[str, Any]]:
        return [{
            "scheme": "exact",
            "network": self.config.chain_caip,
            "token": self.config.token_address,
            "resource": "/agent", # Generic resource for now
            "maxAmountRequired": self.config.price,
            "beneficiary": self.config.wallet_address
        }]

    def _register_routes(self) -> None:
        app = self.app

        @app.route("/", methods=["GET"])
        def health():
            return "Orca Agent SDK (x402 enabled) Running"

        @app.route("/agent", methods=["POST"])
        def handle_agent_request():
            try:
                # 1. Parse Input
                data = request.json or {}
                prompt = data.get("prompt", "")
                if not prompt:
                    return jsonify({"error": "Prompt is required"}), 400

                request_id = _log_request(self.config.db_path, prompt)

                # 2. Check X-PAYMENT header
                signed_b64 = request.headers.get("X-PAYMENT")

                if not signed_b64:
                    return self._respond_payment_required()

                # 3. Decode Payment
                try:
                    payment_obj = self.x402.decode_payment(signed_b64)
                except Exception as e:
                    return jsonify({"error": f"Invalid payment format: {str(e)}"}), 400

                # 4. Verify & Settle via Facilitator
                # We do verifying + settling in one go usually, or separate. 
                # For safety, let's verify then settle.
                
                accepts = self._build_payment_requirements()
                
                # Check with facilitator
                verify_payload = {
                    "payment": payment_obj,
                    "accepts": accepts
                }
                
                try:
                    verify_resp = requests.post(
                        f"{self.config.facilitator_url}/verify",
                        json=verify_payload,
                        timeout=self.config.timeout_seconds
                    )
                    verify_resp.raise_for_status()
                    verify_json = verify_resp.json()
                except Exception as e:
                     return jsonify({"error": "Facilitator verification failed", "details": str(e)}), 500

                if not verify_json.get("valid"):
                    return jsonify({"error": "Payment rejected by facilitator", "details": verify_json}), 402

                # Optional: Settle immediately (capture funds)
                # Some facilitators auto-settle on verify, but standard x402 often implies separate settle or verify-settle.
                # We will attempt settlement to ensure we get paid before running usage.
                settlement = {}
                try:
                    settle_resp = requests.post(
                        f"{self.config.facilitator_url}/settle",
                        json=verify_payload, # Usually same payload or just payment
                        timeout=self.config.timeout_seconds
                    )
                    if settle_resp.status_code == 200:
                        settlement = settle_resp.json()
                except Exception:
                    # If settle fails but verify passed, we might still proceed or fail. 
                    # For a strict agent, we should probably fail or log warning.
                    pass

                # 5. Run Agent Logic
                try:
                    result = self.handler(prompt)
                    if not isinstance(result, str):
                        result = str(result)
                    
                    _update_request_success(self.config.db_path, request_id, result, signed_b64)
                    
                    return jsonify({
                        "result": result,
                        "settlement": settlement
                    }), 200
                    
                except Exception as e:
                    _update_request_failed(self.config.db_path, request_id, str(e))
                    return jsonify({"error": "Agent execution failed", "details": str(e)}), 500

            except Exception as e:
                return jsonify({"error": "Internal server error", "details": str(e)}), 500

    def _respond_payment_required(self):
        accepts = self._build_payment_requirements()
        try:
            challenge = self.x402.encode_payment_required({"accepts": accepts})
        except Exception as e:
             return jsonify({"error": "Failed to generate x402 challenge", "details": str(e)}), 500

        response = make_response(
            jsonify({"message": "Payment required", "accepts": accepts}), 402
        )
        response.headers["PAYMENT-REQUIRED"] = challenge
        response.headers["Access-Control-Expose-Headers"] = "PAYMENT-REQUIRED"
        return response

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        self.app.run(host=host, port=port, debug=debug)