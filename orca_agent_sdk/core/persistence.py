import sqlite3
import secrets
import time

def _db(db_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path: str) -> None:
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

def log_request(db_path: str, prompt: str) -> str:
    request_id = secrets.token_hex(8)
    with _db(db_path) as conn:
        conn.execute(
            "INSERT INTO request_log (request_id, prompt, status) VALUES (?, ?, 'pending')",
            (request_id, prompt),
        )
        conn.commit()
    return request_id

def update_request_success(db_path: str, request_id: str, output: str, payment_token: str = "") -> None:
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

def update_request_failed(db_path: str, request_id: str, error: str) -> None:
    with _db(db_path) as conn:
        conn.execute(
            "UPDATE request_log SET status = 'failed', output = ? WHERE request_id = ?",
            (error, request_id),
        )
        conn.commit()
