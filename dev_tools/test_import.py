import sys
print("Starting import test...")
try:
    from crypto_com_agent_client import Agent
    print("Import successful.")
except Exception as e:
    print(f"Import failed: {e}")
