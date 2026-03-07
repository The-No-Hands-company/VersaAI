#!/usr/bin/env python3
"""
VersaAI Code Assistant - Quick Example

This example demonstrates how to use VersaAI's code model
with real LLM integration for actual code generation.

Prerequisites:
    pip install versaai openai  # or anthropic, or llama-cpp-python
    export OPENAI_API_KEY="sk-..."  # for OpenAI
"""

import os
from versaai.models import CodeModel, CodeContext, CodeTaskType


def example_basic_generation():
    """Example 1: Basic code generation"""
    print("=" * 70)
    print("EXAMPLE 1: Basic Code Generation")
    print("=" * 70)
    
    # Create model with OpenAI (change to your preferred provider)
    model = CodeModel(
        model_id="my-coding-assistant",
        llm_provider="openai",
        llm_model="gpt-3.5-turbo",  # Fast and cheap
        enable_memory=False,  # Disable for simple one-off generation
        enable_rag=False
    )
    
    # Create context
    context = CodeContext(
        language="python",
        requirements=["Add type hints", "Include docstring"]
    )
    
    # Generate code
    result = model.generate_code(
        task="Create a function to calculate the nth Fibonacci number using memoization",
        context=context,
        use_reasoning=False  # Direct generation (faster)
    )
    
    # Display result
    print("\nGenerated Code:")
    print(result["code"])
    print(f"\nLanguage: {result['language']}")
    print("=" * 70 + "\n")


def example_with_framework():
    """Example 2: Generate code with specific framework"""
    print("=" * 70)
    print("EXAMPLE 2: Framework-Specific Code")
    print("=" * 70)
    
    model = CodeModel(
        llm_provider="openai",
        llm_model="gpt-3.5-turbo"
    )
    
    context = CodeContext(
        language="python",
        framework="FastAPI",
        requirements=[
            "Use Pydantic models for validation",
            "Add error handling",
            "Include type hints"
        ]
    )
    
    result = model.generate_code(
        task="Create a REST API endpoint for user registration that accepts email and password",
        context=context
    )
    
    print("\nGenerated FastAPI Code:")
    print(result["code"])
    print("=" * 70 + "\n")


def example_explain_code():
    """Example 3: Explain existing code"""
    print("=" * 70)
    print("EXAMPLE 3: Code Explanation")
    print("=" * 70)
    
    model = CodeModel(
        llm_provider="openai",
        llm_model="gpt-3.5-turbo"
    )
    
    # Code to explain
    code = """
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
    """
    
    context = CodeContext(language="python")
    
    result = model.explain_code(
        code=code,
        context=context,
        detail_level="detailed"
    )
    
    print("\nExplanation:")
    print(result["explanation"])
    
    if result.get("key_concepts"):
        print("\nKey Concepts:")
        for concept in result["key_concepts"]:
            print(f"  - {concept}")
    
    print("=" * 70 + "\n")


def example_with_memory():
    """Example 4: Multi-turn conversation with memory"""
    print("=" * 70)
    print("EXAMPLE 4: Multi-turn Conversation with Memory")
    print("=" * 70)
    
    model = CodeModel(
        llm_provider="openai",
        llm_model="gpt-3.5-turbo",
        enable_memory=True,  # Enable conversation tracking
        enable_rag=False
    )
    
    # First request
    print("\n[Turn 1] Generate User model...")
    result1 = model.generate_code(
        task="Create a SQLAlchemy User model with id, email, and password fields",
        context=CodeContext(language="python", framework="SQLAlchemy")
    )
    print(result1["code"])
    
    # Second request - will use memory from first
    print("\n[Turn 2] Generate API endpoint (knows about User model)...")
    result2 = model.generate_code(
        task="Now create a FastAPI endpoint to create a new user",
        context=CodeContext(language="python", framework="FastAPI")
    )
    print(result2["code"])
    
    # Show conversation history
    print("\n[Conversation History]")
    history = model.get_conversation_history()
    print(f"Total turns: {len(history)}")
    
    print("=" * 70 + "\n")


def example_different_languages():
    """Example 5: Generate code in different languages"""
    print("=" * 70)
    print("EXAMPLE 5: Multi-language Code Generation")
    print("=" * 70)
    
    model = CodeModel(
        llm_provider="openai",
        llm_model="gpt-3.5-turbo"
    )
    
    task = "Create a function to reverse a string"
    
    # Python
    print("\n[Python]")
    result = model.generate_code(
        task=task,
        context=CodeContext(language="python")
    )
    print(result["code"])
    
    # JavaScript
    print("\n[JavaScript]")
    result = model.generate_code(
        task=task,
        context=CodeContext(language="javascript")
    )
    print(result["code"])
    
    # C++
    print("\n[C++]")
    result = model.generate_code(
        task=task,
        context=CodeContext(language="cpp")
    )
    print(result["code"])
    
    print("=" * 70 + "\n")


def example_local_model():
    """Example 6: Use local model instead of API"""
    print("=" * 70)
    print("EXAMPLE 6: Local Model (Private & Free)")
    print("=" * 70)
    
    # Check if local model exists
    model_path = "./models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
    
    if not os.path.exists(model_path):
        print(f"\n⚠️  Local model not found at {model_path}")
        print("\nDownload with:")
        print("  mkdir -p models")
        print("  wget https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf -P ./models/")
        print("=" * 70 + "\n")
        return
    
    # Create model with local LLM
    model = CodeModel(
        llm_provider="local",
        llm_model=model_path,
        n_gpu_layers=-1  # Use GPU if available
    )
    
    result = model.generate_code(
        task="Create a function to check if a number is prime",
        context=CodeContext(language="python")
    )
    
    print("\nGenerated Code (using local model):")
    print(result["code"])
    print("\n✅ Completely private - no data sent to any API!")
    print("=" * 70 + "\n")


def example_with_reasoning():
    """Example 7: Generate code with reasoning (Chain-of-Thought)"""
    print("=" * 70)
    print("EXAMPLE 7: Code Generation with Reasoning")
    print("=" * 70)
    
    model = CodeModel(
        llm_provider="openai",
        llm_model="gpt-4-turbo",  # GPT-4 for better reasoning
        enable_memory=False
    )
    
    result = model.generate_code(
        task="Create a function to find the longest palindromic substring",
        context=CodeContext(
            language="python",
            requirements=["Optimize for performance", "Handle edge cases"]
        ),
        use_reasoning=True  # Enable Chain-of-Thought reasoning
    )
    
    print("\nGenerated Code:")
    print(result["code"])
    
    if result.get("reasoning_steps"):
        print("\n\nReasoning Steps:")
        for i, step in enumerate(result["reasoning_steps"], 1):
            print(f"{i}. {step}")
    
    print("=" * 70 + "\n")


def main():
    """Run examples"""
    print("\n" + "=" * 70)
    print("VersaAI Code Model - Usage Examples")
    print("=" * 70 + "\n")
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY"):
        print("⚠️  WARNING: No API key found!")
        print("\nTo run these examples, set:")
        print("  export OPENAI_API_KEY='sk-...'")
        print("  OR")
        print("  export ANTHROPIC_API_KEY='sk-ant-...'")
        print("\nOr use a local model (see example 6)")
        print("=" * 70 + "\n")
        
        # Still run one example to show structure
        print("Running code extraction example (no LLM needed)...\n")
        from versaai.models.code_llm import extract_code_from_response
        
        response = """
        Here's a solution:
        ```python
        def hello():
            return "world"
        ```
        """
        code = extract_code_from_response(response, "python")
        print(f"Extracted code:\n{code}")
        print("\n✅ Code extraction works!")
        return
    
    # Run examples (comment out the ones you don't want)
    try:
        # Basic examples
        example_basic_generation()
        example_with_framework()
        
        # Code understanding
        # example_explain_code()
        
        # Advanced features
        # example_with_memory()
        # example_different_languages()
        
        # Local model (if available)
        # example_local_model()
        
        # Reasoning
        # example_with_reasoning()
        
        print("\n" + "=" * 70)
        print("Examples Complete!")
        print("=" * 70)
        print("""
Uncomment other examples in main() to try:
- Code explanation
- Multi-turn conversation with memory
- Different programming languages
- Local models (free & private)
- Chain-of-Thought reasoning
        """)
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure API key is set correctly")
        print("2. Check internet connection (for API providers)")
        print("3. Install required packages: pip install openai")
        print("4. Try with a local model instead")


if __name__ == "__main__":
    main()
