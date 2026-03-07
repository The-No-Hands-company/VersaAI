#!/usr/bin/env python3
"""
Interactive CLI for testing the CodingAgent
"""
import sys
import os
import argparse

# Add parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from versaai.agents.coding_agent import CodingAgent
from versaai.models import ModelRegistry

# Mock LLM for testing without real keys
class MockLLM:
    def generate(self, prompt, **kwargs):
        return f"""Here is the code you requested for: {prompt[:30]}...
        
def generated_function():
    print("This is generated code from the CodingAgent")
    return True
"""

def mock_load(model_id, **kwargs):
    return MockLLM()

def main():
    parser = argparse.ArgumentParser(description="Test CodingAgent CLI")
    parser.add_argument("--mock", action="store_true", help="Use mock LLM instead of real one")
    args = parser.parse_args()

    print("🤖 Initializing CodingAgent...")
    
    if args.mock:
        print("⚠️  Using MOCK LLM mode")
        ModelRegistry.load = mock_load
        
    agent = CodingAgent()
    agent.initialize()
    
    print("\n✅ CodingAgent ready! (Type 'quit' to exit)")
    print("-" * 50)
    
    while True:
        try:
            task = input("\n📝 Enter coding task: ").strip()
            if task.lower() in ('quit', 'exit'):
                break
            if not task:
                continue
                
            print("\n⚙️  Agent working...")
            
            print("\n⚙️  Agent working...")
            
            def print_status(msg, stream=False):
                if stream:
                    # Print raw token stream
                    print(msg, end="", flush=True)
                else:
                    # System messages
                    print(f"\n👉 {msg}")
                
            context = {'status_callback': print_status}
            result = agent.execute(task, context=context)
            
            print("\n📄 Result:")
            print("-" * 20)
            print(result.get('result', 'No result'))
            print("-" * 20)
            
            if 'files_created' in result:
                print(f"📂 Files created: {result['files_created']}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
