import os
from orca_agent_sdk.backends.crewai_backend import CrewAIBackend
from orca_agent_sdk.config import AgentConfig

def test_backend():
    print("Testing Backend Isolation...")
    config = AgentConfig(
        agent_id="test-agent",
        price="0.1",
        backend_options={
            "model": "gemini/gemini-2.0-flash",
            "provider_api_key": "AIzaSyDAXuIHqH6myK_x-s5RX69-oQeDOUEk5ek"
        }
    )
    
    backend = CrewAIBackend()
    try:
        backend.initialize(config)
        print("Backend Initialized.")
        
        result = backend.handle_prompt("Say hello")
        print(f"Result: {result}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_backend()
