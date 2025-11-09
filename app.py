from flask import Flask, request, jsonify
import json
import base64
from database import init_db, create_job, get_job

app = Flask(__name__)

@app.route("/")
def hello():
    return "Agent Server Running"

@app.route("/start_job", methods=["POST"])
def start_job():
    """Start a new job and return job_id with unsigned transaction"""
    data = request.get_json()
    if not data or "job_input" not in data:
        return jsonify({"error": "job_input required"}), 400
    
    job_input = data["job_input"]
    job_id, job_input_hash = create_job(job_input)
    
    # Generate mock unsigned group transaction (base64 encoded)
    unsigned_txn = base64.b64encode(f"mock_txn_{job_id}".encode()).decode()
    
    return jsonify({
        "job_id": job_id,
        "unsigned_group_txn": unsigned_txn,
        "price": 0.1
    })

@app.route("/job/<job_id>", methods=["GET"])
def get_job_status(job_id):
    """Get job status and result"""
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify({
        "job_id": job["job_id"],
        "status": job["status"],
        "created_at": job["created_at"],
        "output": job["output"]
    })

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8000)
