import sys
import os
import asyncio
import json

# Add parent dir to path to find versaai package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from versaai.code_editor_bridge.chat_service import EditorChatService
from versaai.models import ModelRegistry

# Mock Model Registry
class MockLLM:
    def generate(self, prompt, **kwargs):
        return f"MockResponse for: {prompt[:20]}..."

def mock_load(model_id):
    return MockLLM()

ModelRegistry.load = mock_load

async def verify_chat_routing():
    print("\n--- Verifying Chat Service Routing ---")
    
    # Initialize Service
    service = EditorChatService()
    
    # 1. Test Research Routing
    print("\nTest 1: Research Routing")
    response = await service.chat(
        session_id="test_session",
        message="Research quantum computing",
        task_type="research"
    )
    print(f"Response: {response['response']}")
    print(f"Model Used: {response['model']}")
    
    assert response['model'] == 'ResearchAgent'
    assert "MockResponse" in response['response'] or "Mock Search Result" in response['response'] or "Mock retrieval" in response['response']
    
    # 2. Test Coding Routing
    print("\nTest 2: Coding Routing")
    response = await service.chat(
        session_id="test_session",
        message="Write a python function",
        task_type="coding"
    )
    print(f"Response: {response['response']}")
    print(f"Model Used: {response['model']}")
    
    assert response['model'] == 'CodingAgent'
    
    print("\n✅ Chat Service Integration PASSED")

if __name__ == "__main__":
    try:
        asyncio.run(verify_chat_routing())
    except Exception as e:
        print(f"\n❌ VERIFICATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
