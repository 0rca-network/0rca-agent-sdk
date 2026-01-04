from crypto_com_agent_client import Agent
print(f"Agent methods: {[m for m in dir(Agent) if not m.startswith('_')]}")
