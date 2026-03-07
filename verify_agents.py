import sys
import os

# Add parent dir to path to find versaai package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from versaai.agents import ResearchAgent, CodingAgent, AgentBase
from versaai.models import ModelRegistry

# Mock Model Registry to avoid actual API calls during basic verification
original_load = ModelRegistry.load

class MockLLM:
    def generate(self, prompt, **kwargs):
        if "python" in prompt.lower():
            return "print('Hello from CodingAgent')"
        return "This is a mock response from ResearchAgent."

def mock_load(model_id):
    print(f"Mocking load for {model_id}")
    return MockLLM()

ModelRegistry.load = mock_load

def verify_research():
    print("\n--- Verifying ResearchAgent ---")
    agent = ResearchAgent()
    agent.initialize({"model": "test-model", "enable_web_search": True})
    
    result = agent.execute("Tell me about quantum computing")
    print(f"Result: {result['result']}")
    print(f"Steps: {result['steps']}")
    
    assert result['result'] == "This is a mock response from ResearchAgent."
    print("ResearchAgent Verification PASSED")

def verify_coding():
    print("\n--- Verifying CodingAgent ---")
    agent = CodingAgent()
    agent.initialize({"model": "test-model"})
    
    result = agent.execute("Write a python script")
    print(f"Result: {result['result']}")
    
    # Test tool (read file)
    # create a dummy file
    with open("test_dummy.txt", "w") as f:
        f.write("dummy content")
        
    read_content = agent._read_file("test_dummy.txt")
    print(f"File Read Test: {read_content}")
    assert read_content == "dummy content"
    
    os.remove("test_dummy.txt")
    print("CodingAgent Verification PASSED")
    
if __name__ == "__main__":
    try:
        verify_research()
        verify_coding()
        print("\nALL AGENT VERIFICATIONS PASSED")
    except Exception as e:
        print(f"\nVERIFICATION FAILED: {e}")
        sys.exit(1)
