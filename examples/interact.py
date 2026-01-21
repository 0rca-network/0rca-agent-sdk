import requests
import sys
import time

def interact():
    url = "http://localhost:8001/agent"
    print("Welcome to Contract Agent Interaction!")
    print(f"Connecting to {url}...")
    
    while True:
        try:
            prompt = input("\nYou: ")
            if prompt.lower() in ["exit", "quit"]:
                break
                
            response = requests.post(url, json={"prompt": prompt})
            
            if response.status_code == 200:
                data = response.json()
                print(f"\nAgent: {data.get('response', data)}")
            else:
                print(f"\nError ({response.status_code}): {response.text}")
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nInteraction Error: {e}")
            time.sleep(1)

if __name__ == "__main__":
    interact()
