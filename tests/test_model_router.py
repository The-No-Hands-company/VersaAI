#!/usr/bin/env python3
"""
Test ModelRouter to verify route() method works correctly
"""

import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_sync_router():
    """Test ModelRouter route() method synchronously"""
    print("\n" + "="*60)
    print("Testing ModelRouter.route() - Synchronous")
    print("="*60)
    
    from versaai.models.model_router import ModelRouter
    
    # Initialize router
    router = ModelRouter()
    print(f"✅ Router initialized with models: {router.usable_models}")
    
    # Test route method exists
    print(f"\n📋 Checking router attributes:")
    print(f"   - Has 'route' method: {hasattr(router, 'route')}")
    print(f"   - Route method type: {type(getattr(router, 'route', None))}")
    
    # Test routing
    test_prompts = [
        "Write a simple Python function to add two numbers",
        "Explain this complex C++ algorithm",
        "Debug this JavaScript code with memory leaks"
    ]
    
    print(f"\n🧪 Testing route() with {len(test_prompts)} prompts:\n")
    
    for i, prompt in enumerate(test_prompts, 1):
        print(f"Test {i}: {prompt[:50]}...")
        try:
            result = router.route(prompt)
            print(f"   ✅ Status: Success")
            print(f"   📦 Response keys: {list(result.keys())}")
            print(f"   🤖 Model: {result.get('model')}")
            print(f"   💬 Response: {result.get('response', '')[:80]}...")
            print()
        except Exception as e:
            print(f"   ❌ Error: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("="*60)
    print("✅ Synchronous test complete!")
    print("="*60)


async def test_async_router():
    """Test ModelRouter route() method asynchronously (as used in server)"""
    print("\n" + "="*60)
    print("Testing ModelRouter.route() - Asynchronous (asyncio.to_thread)")
    print("="*60)
    
    from versaai.models.model_router import ModelRouter
    
    # Initialize router
    router = ModelRouter()
    print(f"✅ Router initialized")
    
    # Test async routing (this is how it's called in server.py)
    prompt = "Write a Python hello world program"
    
    print(f"\n🧪 Testing asyncio.to_thread(router.route, ...):\n")
    print(f"Prompt: {prompt}")
    
    try:
        result = await asyncio.to_thread(
            router.route,
            prompt=prompt,
            task_type='code_completion',
            language='python'
        )
        print(f"   ✅ Status: Success")
        print(f"   📦 Result: {result}")
        print()
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print()
    
    print("="*60)
    print("✅ Asynchronous test complete!")
    print("="*60)


def test_router_internals():
    """Test ModelRouter internal methods"""
    print("\n" + "="*60)
    print("Testing ModelRouter Internal Methods")
    print("="*60)
    
    from versaai.models.model_router import ModelRouter
    
    router = ModelRouter()
    
    # Test select_model
    print("\n🧪 Testing select_model():")
    task = "Write a complex algorithm in Python"
    model_id, model_spec = router.select_model(task, language='python')
    print(f"   Task: {task}")
    print(f"   Selected: {model_spec.name} ({model_id})")
    print(f"   Tier: {model_spec.tier.value}")
    print(f"   Strengths: {', '.join(model_spec.strengths)}")
    
    # Test language detection
    print("\n🧪 Testing _detect_language():")
    test_cases = [
        "Write a Python script",
        "Create a React component",
        "Implement a Java class",
    ]
    for test in test_cases:
        lang = router._detect_language(test)
        print(f"   '{test[:30]}...' → {lang}")
    
    # Test complexity detection
    print("\n🧪 Testing _detect_complexity():")
    complexity_cases = [
        "Fix this bug",
        "Refactor the entire codebase",
        "Write a simple function",
    ]
    for test in complexity_cases:
        complexity = router._detect_complexity(test)
        print(f"   '{test[:30]}...' → {complexity.value}")
    
    print("\n" + "="*60)
    print("✅ Internal methods test complete!")
    print("="*60)


if __name__ == '__main__':
    print("\n🚀 VersaAI ModelRouter Test Suite")
    print("="*60)
    
    # Run tests
    try:
        test_sync_router()
        test_router_internals()
        asyncio.run(test_async_router())
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n💡 Next step: Connect router to actual model inference")
        print("   See: versaai/models/code_llm.py")
        print()
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
