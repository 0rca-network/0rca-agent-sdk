from crypto_com_agent_client import Agent
import inspect

# Initialize a dummy agent to see instance methods
agent = Agent()
print(f"Agent instance methods: {[m for m, _ in inspect.getmembers(agent, predicate=inspect.ismethod)]}")
