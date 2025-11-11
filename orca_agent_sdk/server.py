import base64
import hashlib
import json
import requests
import threading
import time
from typing import Callable, List, Tuple

from flask import Flask, jsonify, request
from algosdk.v2client import algod, indexer
from algosdk.atomic_transaction_composer import (
    AtomicTransactionComposer,
    AccountTransactionSigner,
    TransactionWithSigner,
)
from algosdk.transaction import PaymentTxn
from algosdk.abi import Method
from algosdk import mnemonic
from algokit_utils.transactions.transaction_composer import populate_app_call_resources
from algosdk.encoding import msgpack_encode
import sqlite3

from .config import AgentConfig


# --- Internal DB helpers (opinionated, hidden from agent devs) ---


def _init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs_local (
                job_id TEXT PRIMARY KEY,
                job_input TEXT NOT NULL,
                sender_address TEXT NOT NULL,
                txn_ids TEXT,
                status TEXT NOT NULL,
                created_at INTEGER DEFAULT (unixepoch()),
                completed_at INTEGER,
                output TEXT
            );

            CREATE TABLE IF NOT EXISTS access_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                access_token TEXT UNIQUE NOT NULL,
                created_at INTEGER DEFAULT (unixepoch())
            );

            CREATE INDEX IF NOT EXISTS idx_access_token ON access_tokens(access_token);
            CREATE INDEX IF NOT EXISTS idx_job_agent ON access_tokens(job_id, agent_id);
            """
        )
        conn.commit()
    finally:
        conn.close()


def _db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _create_job(db_path: str, job_input: str, sender_address: str) -> str:
    job_id = f"J{int(time.time() * 1000)}"
    with _db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO jobs_local (job_id, job_input, sender_address, status)
            VALUES (?, ?, ?, 'queued')
            """,
            (job_id, job_input, sender_address),
        )
        conn.commit()
    return job_id


def _update_job_payment_processing(db_path: str, job_id: str, txn_ids: List[str]) -> None:
    with _db(db_path) as conn:
        conn.execute(
            """
            UPDATE jobs_local
            SET status = 'payment_processing', txn_ids = ?
            WHERE job_id = ?
            """,
            (",".join(txn_ids), job_id),
        )
        conn.commit()


def _update_job_status(db_path: str, job_id: str, status: str) -> None:
    with _db(db_path) as conn:
        conn.execute(
            "UPDATE jobs_local SET status = ? WHERE job_id = ?",
            (status, job_id),
        )
        conn.commit()


def _complete_job(db_path: str, job_id: str, output: str) -> None:
    with _db(db_path) as conn:
        conn.execute(
            """
            UPDATE jobs_local
            SET status = 'succeeded', output = ?, completed_at = unixepoch()
            WHERE job_id = ?
            """,
            (output, job_id),
        )
        conn.commit()


def _get_job(db_path: str, job_id: str):
    with _db(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM jobs_local WHERE job_id = ?",
            (job_id,),
        ).fetchone()
    return row


def _create_access_token(db_path: str, job_id: str, agent_id: str) -> str:
    import secrets

    token = secrets.token_hex(32)
    with _db(db_path) as conn:
        conn.execute(
            """
            INSERT INTO access_tokens (job_id, agent_id, access_token)
            VALUES (?, ?, ?)
            """,
            (job_id, agent_id, token),
        )
        conn.commit()
    return token


def _verify_access_token(db_path: str, job_id: str, access_token: str) -> bool:
    with _db(db_path) as conn:
        row = conn.execute(
            """
            SELECT 1 FROM access_tokens
            WHERE job_id = ? AND access_token = ?
            """,
            (job_id, access_token),
        ).fetchone()
    return row is not None


def _push_to_remote_server(config: AgentConfig, job_id: str, access_token: str, job_input: str, sender_address: str, job_output: str = "") -> None:
    """Push access token and job details to remote server"""
    if not config.agent_token or not config.remote_server_url:
        return
    
    job_input_hash = hashlib.sha256(job_input.encode()).hexdigest()
    
    payload = {
        "user_id": sender_address,
        "wallet_address": sender_address,
        "job_id": job_id,
        "agent_id": config.agent_id,
        "access_token": access_token,
        "job_input_hash": job_input_hash,
        "job_output": json.dumps({"result": job_output, "status": "completed"}) if job_output else ""
    }
    
    headers = {
        "Content-Type": "application/json",
        "X-Agent-Token": config.agent_token
    }
    
    try:
        requests.post(config.remote_server_url, json=payload, headers=headers, timeout=10)
    except Exception:
        pass


# --- Algorand helpers ---


def _build_unsigned_group(
    cfg: AgentConfig, client: algod.AlgodClient, sender_address: str
) -> Tuple[List[str], List[str]]:
    """
    Build unsigned group transactions for:
    - Payment of cfg.price_microalgos from sender -> cfg.receiver_address
    - App call to cfg.app_id using method 'pay(pay)void'

    Uses a dummy signer only for ATC assembly; caller returns base64-encoded txns.
    """
    method = Method.from_signature("pay(pay)void")

    # Dummy key ONLY for building txns; never used for signing on-chain.
    dummy_mn = (
        "announce feed swing base certain rib rose phrase crouch rotate voyage enroll "
        "same sort flush emotion pulp airport notice inject pelican zero blossom about honey"
    )
    dummy_sk = mnemonic.to_private_key(dummy_mn)
    signer = AccountTransactionSigner(dummy_sk)

    atc = AtomicTransactionComposer()
    sp = client.suggested_params()
    sp.flat_fee = True
    sp.fee = cfg.flat_fee

    atc.add_method_call(
        app_id=cfg.app_id,
        method=method,
        sender=sender_address,
        sp=sp,
        signer=signer,
        method_args=[
            TransactionWithSigner(
                PaymentTxn(
                    sender=sender_address,
                    sp=sp,
                    receiver=cfg.receiver_address,
                    amt=cfg.price_microalgos,
                ),
                signer,
            )
        ],
    )

    atc = populate_app_call_resources(atc, client)
    group = atc.build_group()

    unsigned_txns: List[str] = []
    txn_ids: List[str] = []

    for tws in group:
        txn = tws.txn
        txid = txn.get_txid()
        txn_ids.append(txid)

        unsigned_bytes = msgpack_encode(txn)
        if isinstance(unsigned_bytes, str):
            unsigned_bytes = unsigned_bytes.encode()
        unsigned_txns.append(base64.b64encode(unsigned_bytes).decode())

    return unsigned_txns, txn_ids


def _verify_txns_onchain(
    cfg: AgentConfig,
    idx: indexer.IndexerClient,
    job_row,
    submitted_txids: List[str],
) -> Tuple[bool, str]:
    if not job_row:
        return False, "Job not found"

    expected_ids = (job_row["txn_ids"] or "").split(",") if job_row["txn_ids"] else []
    if set(submitted_txids) != set(expected_ids):
        return False, "Submitted txids do not match expected"

    sender = job_row["sender_address"]

    for txid in submitted_txids:
        try:
            res = idx.transaction(txid)
            txn = res["transaction"]

            if txn["sender"] != sender:
                return False, f"Sender mismatch for {txid}"

            tx_type = txn["tx-type"]

            if tx_type == "pay":
                pay = txn["payment-transaction"]
                if pay["receiver"] != cfg.receiver_address:
                    return False, f"Receiver mismatch for {txid}"
                if pay["amount"] != cfg.price_microalgos:
                    return False, f"Amount mismatch for {txid}"

            elif tx_type == "appl":
                appl = txn["application-transaction"]
                if appl["application-id"] != cfg.app_id:
                    return False, f"App ID mismatch for {txid}"
                # Optional: verify ABI selector if you want stricter checks
        except Exception as e:
            return False, f"On-chain verification failed for {txid}: {e}"

    return True, "OK"


# --- Public AgentServer (what devs instantiate) ---


class AgentServer:
    """
    Opinionated server that:
    - Exposes:
        POST /start_job
        POST /submit_payment
        GET  /job/<job_id>
    - Handles Algorand-based payment verification.
    - Persists jobs + access_tokens in SQLite.
    - Runs user handler in background once payment is verified.

    Agent dev is expected to:
    - Provide AgentConfig (agent_id, receiver_address, price_microalgos, etc).
    - Provide handler: function(job_input: str) -> str
    """

    def __init__(self, config: AgentConfig, handler: Callable[[str], str]):
        self.config = config
        self.config.validate()
        self.handler = handler

        _init_db(self.config.db_path)

        self.algod = algod.AlgodClient(
            self.config.algod_token, self.config.algod_url
        )
        self.indexer = indexer.IndexerClient(
            self.config.indexer_token, self.config.indexer_url
        )

        self.app = Flask(__name__)
        self._register_routes()

    # --- Flask routes ---

    def _register_routes(self) -> None:
        app = self.app

        @app.route("/", methods=["GET"])
        def health():
            """
            Health check: GET /
            
            Response: "Orca Agent SDK Server Running"
            """
            return "Orca Agent SDK Server Running"

        @app.route("/start_job", methods=["POST"])
        def start_job():
            """
            Create job: POST /start_job
            
            Request:
            {
                "sender_address": "USER_ALGO_ADDRESS",
                "job_input": "User request or prompt"
            }
            
            Response:
            {
                "job_id": "J1762754481290",
                "unsigned_group_txns": ["...base64_txn_1...", "...base64_txn_2..."],
                "txn_ids": ["EXPECTED_TXID_1", "EXPECTED_TXID_2"],
                "payment_required": 1000000
            }
            """
            data = request.get_json() or {}
            sender_address = data.get("sender_address")
            job_input = data.get("job_input")

            if not sender_address or not job_input:
                return (
                    jsonify(
                        {
                            "error": "sender_address and job_input are required",
                        }
                    ),
                    400,
                )

            job_id = _create_job(
                self.config.db_path,
                job_input=job_input,
                sender_address=sender_address,
            )

            unsigned_group, txn_ids = _build_unsigned_group(
                self.config, self.algod, sender_address
            )

            _update_job_payment_processing(self.config.db_path, job_id, txn_ids)

            return jsonify(
                {
                    "job_id": job_id,
                    "unsigned_group_txns": unsigned_group,
                    "txn_ids": txn_ids,
                    "payment_required": self.config.price_microalgos,
                }
            )

        @app.route("/submit_payment", methods=["POST"])
        def submit_payment():
            """
            Verify payment: POST /submit_payment
            
            Request:
            {
                "job_id": "J1762754481290",
                "txid": ["REAL_TXID_1", "REAL_TXID_2"]
            }
            
            Response (success):
            {
                "status": "success",
                "message": "Payment verified, job started",
                "access_token": "ACCESS_TOKEN_VALUE"
            }
            
            Response (error - 402):
            {
                "status": "error",
                "message": "Payment verification failed reason"
            }
            """
            data = request.get_json() or {}
            job_id = data.get("job_id")
            txids = data.get("txid")

            if not job_id or not txids:
                return (
                    jsonify({"error": "job_id and txid are required"}),
                    400,
                )

            if not isinstance(txids, list):
                return jsonify({"error": "txid must be an array"}), 400

            job = _get_job(self.config.db_path, job_id)
            ok, msg = _verify_txns_onchain(
                self.config,
                self.indexer,
                job,
                txids,
            )

            if not ok:
                _update_job_status(self.config.db_path, job_id, "failed")
                return jsonify({"status": "error", "message": msg}), 402

            # Mark running, create token, start execution
            _update_job_status(self.config.db_path, job_id, "running")
            access_token = _create_access_token(
                self.config.db_path,
                job_id=job_id,
                agent_id=self.config.agent_id,
            )
            
            # Push to remote server
            _push_to_remote_server(
                self.config, 
                job_id, 
                access_token, 
                job["job_input"], 
                job["sender_address"]
            )

            thread = threading.Thread(
                target=self._execute_job_safe, args=(job_id,)
            )
            thread.daemon = True
            thread.start()

            return jsonify(
                {
                    "status": "success",
                    "message": "Payment verified, job started",
                    "access_token": access_token,
                }
            )

        @app.route("/job/<job_id>", methods=["GET"])
        def get_job(job_id: str):
            """
            Retrieve result: GET /job/<job_id>[?access_token=TOKEN]
            
            Without access token (public view):
            {
                "job_id": "J1762754481290",
                "status": "running",
                "created_at": 1762754481,
                "output": null
            }
            
            With valid access_token:
            {
                "job_id": "J1762754481290",
                "status": "succeeded",
                "created_at": 1762754481,
                "completed_at": 1762754504,
                "output": "Echo: Hello from local SDK test"
            }
            """
            token = request.args.get("access_token")
            job = _get_job(self.config.db_path, job_id)
            if not job:
                return jsonify({"error": "Job not found"}), 404

            if token:
                if not _verify_access_token(
                    self.config.db_path, job_id, token
                ):
                    return (
                        jsonify(
                            {"error": "Invalid or expired access token"}
                        ),
                        401,
                    )
                # Full details
                return jsonify(
                    {
                        "job_id": job["job_id"],
                        "status": job["status"],
                        "created_at": job["created_at"],
                        "completed_at": job["completed_at"],
                        "output": job["output"],
                    }
                )

            # Public view: hide output
            return jsonify(
                {
                    "job_id": job["job_id"],
                    "status": job["status"],
                    "created_at": job["created_at"],
                    "output": None,
                }
            )

    # --- Internal job execution ---

    def _execute_job_safe(self, job_id: str) -> None:
        job = _get_job(self.config.db_path, job_id)
        if not job:
            return
        try:
            result = self.handler(job["job_input"])
            if not isinstance(result, str):
                result = str(result)
            _complete_job(self.config.db_path, job_id, result)
            
            # Get access token and push completed job to remote server
            with _db(self.config.db_path) as conn:
                token_row = conn.execute(
                    "SELECT access_token FROM access_tokens WHERE job_id = ?",
                    (job_id,)
                ).fetchone()
                if token_row:
                    _push_to_remote_server(
                        self.config,
                        job_id,
                        token_row["access_token"],
                        job["job_input"],
                        job["sender_address"],
                        result
                    )
        except Exception as e:
            _update_job_status(self.config.db_path, job_id, "failed")

    # --- Public run helper ---

    def run(self, host: str = "0.0.0.0", port: int = 8000, debug: bool = False):
        """
        Start the opinionated HTTP server.
        Agent dev typically just calls:
            AgentServer(config, handler).run()
        """
        self.app.run(host=host, port=port, debug=debug)