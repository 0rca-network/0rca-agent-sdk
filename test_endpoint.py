import requests
import json

url = "http://localhost:8000/agent"
payload = {"prompt": "Hello integration test!"}
headers = {"Content-Type": "application/json"}

try:
    print(f"Testing {url}...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    print(f"Body: {response.text}")
    
    if response.status_code == 402:
        print("\nSUCCESS: Received 402 Payment Required challenge!")
        if "PAYMENT-REQUIRED" in response.headers:
            print(f"Challenge Token Found: {response.headers['PAYMENT-REQUIRED'][:30]}...")
except Exception as e:
    print(f"Test failed: {e}")
