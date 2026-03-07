import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

print("Starting import check...")
try:
    import versaai
    print(f"Imported versaai: {versaai}")
    from versaai import agents
    print(f"Imported agents: {agents}")
    from versaai.models import ModelRegistry
    print(f"Imported ModelRegistry: {ModelRegistry}")
except Exception as e:
    print(f"Import failed: {e}")
