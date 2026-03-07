#!/usr/bin/env python3
"""
Test script for VersaAI Code LLM integration

Tests the code_llm module with different providers (if available).
"""

import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from versaai.models.code_llm import (
    create_code_llm,
    GenerationConfig,
    build_code_prompt,
    extract_code_from_response
)


def test_prompt_builder():
    """Test prompt building"""
    print("=" * 70)
    print("TEST 1: Prompt Builder")
    print("=" * 70)
    
    prompt = build_code_prompt(
        task="Create a function to calculate factorial",
        language="python",
        requirements=["Add type hints", "Handle negative numbers"],
        framework="NumPy"
    )
    
    print(prompt)
    print("\n✅ Prompt builder working\n")


def test_code_extraction():
    """Test code extraction from markdown"""
    print("=" * 70)
    print("TEST 2: Code Extraction")
    print("=" * 70)
    
    # Test with markdown code block
    response1 = """
Here's a factorial function:

```python
def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("n must be non-negative")
    if n == 0:
        return 1
    return n * factorial(n - 1)
```

This implements recursion.
    """
    
    code1 = extract_code_from_response(response1, "python")
    print("Extracted from markdown:")
    print(code1)
    
    # Test with plain code
    response2 = "def hello():\n    return 'world'"
    code2 = extract_code_from_response(response2, "python")
    print("\nExtracted from plain text:")
    print(code2)
    
    print("\n✅ Code extraction working\n")


def test_openai_llm():
    """Test OpenAI LLM (if API key available)"""
    print("=" * 70)
    print("TEST 3: OpenAI LLM")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping test")
        return
    
    try:
        llm = create_code_llm("openai", "gpt-3.5-turbo")
        
        prompt = "Write a Python function to reverse a string. Keep it simple."
        config = GenerationConfig(max_tokens=256, temperature=0.7)
        
        print(f"Prompt: {prompt}")
        print("\nGenerating...")
        
        response = llm.generate(prompt, config)
        code = extract_code_from_response(response, "python")
        
        print("\nGenerated code:")
        print(code)
        print("\n✅ OpenAI LLM working\n")
        
    except Exception as e:
        print(f"❌ OpenAI test failed: {e}\n")


def test_anthropic_llm():
    """Test Anthropic LLM (if API key available)"""
    print("=" * 70)
    print("TEST 4: Anthropic Claude LLM")
    print("=" * 70)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set, skipping test")
        return
    
    try:
        llm = create_code_llm("anthropic", "claude-3-haiku-20240307")
        
        prompt = "Write a Python function to check if a number is prime. Keep it simple."
        config = GenerationConfig(max_tokens=256, temperature=0.7)
        
        print(f"Prompt: {prompt}")
        print("\nGenerating...")
        
        response = llm.generate(prompt, config)
        code = extract_code_from_response(response, "python")
        
        print("\nGenerated code:")
        print(code)
        print("\n✅ Anthropic LLM working\n")
        
    except Exception as e:
        print(f"❌ Anthropic test failed: {e}\n")


def test_local_llm():
    """Test local LLM (if model file exists)"""
    print("=" * 70)
    print("TEST 5: Local LLM (llama.cpp)")
    print("=" * 70)
    
    # Common model paths to check
    model_paths = [
        "./models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "./models/deepseek-coder.gguf",
        "./models/codellama.gguf",
        "./models/starcoder.gguf",
    ]
    
    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break
    
    if not model_path:
        print(f"⚠️  No local model found. Checked:")
        for path in model_paths:
            print(f"    - {path}")
        print("\nSkipping local LLM test")
        return
    
    try:
        print(f"Loading model: {model_path}")
        llm = create_code_llm("local", model_path, n_gpu_layers=0, verbose=False)
        
        prompt = "def fibonacci(n):\n    # Implement iteratively\n    "
        config = GenerationConfig(max_tokens=128, temperature=0.7)
        
        print(f"\nPrompt: {prompt}")
        print("Generating...")
        
        response = llm.generate(prompt, config)
        
        print("\nGenerated code:")
        print(response)
        print("\n✅ Local LLM working\n")
        
    except ImportError:
        print("❌ llama-cpp-python not installed. Install with:")
        print("   pip install llama-cpp-python\n")
    except Exception as e:
        print(f"❌ Local LLM test failed: {e}\n")


def test_huggingface_llm():
    """Test HuggingFace LLM (if transformers installed)"""
    print("=" * 70)
    print("TEST 6: HuggingFace LLM")
    print("=" * 70)
    
    try:
        import transformers
        import torch
    except ImportError:
        print("⚠️  transformers/torch not installed, skipping test")
        print("   Install with: pip install transformers torch")
        return
    
    # Use a very small model for testing
    model_id = "microsoft/phi-2"  # 2.7B model
    
    print(f"⚠️  This test will download ~5GB model: {model_id}")
    print("   Press Ctrl+C to skip, or Enter to continue...")
    
    try:
        input()
    except KeyboardInterrupt:
        print("\n⚠️  Skipped by user\n")
        return
    
    try:
        llm = create_code_llm("huggingface", model_id, device="auto")
        
        prompt = "# Python function to add two numbers\ndef add(a, b):\n    "
        config = GenerationConfig(max_tokens=64, temperature=0.7)
        
        print(f"\nPrompt: {prompt}")
        print("Generating...")
        
        response = llm.generate(prompt, config)
        
        print("\nGenerated code:")
        print(response)
        print("\n✅ HuggingFace LLM working\n")
        
    except Exception as e:
        print(f"❌ HuggingFace test failed: {e}\n")


def test_code_model_integration():
    """Test CodeModel with LLM integration"""
    print("=" * 70)
    print("TEST 7: CodeModel Integration")
    print("=" * 70)
    
    # Test with OpenAI if available
    if os.getenv("OPENAI_API_KEY"):
        try:
            from versaai.models import CodeModel, CodeContext
            
            print("Creating CodeModel with OpenAI...")
            model = CodeModel(
                model_id="test-assistant",
                llm_provider="openai",
                llm_model="gpt-3.5-turbo",
                enable_memory=False,
                enable_rag=False
            )
            
            print("Generating code...")
            context = CodeContext(
                language="python",
                requirements=["Keep it simple"]
            )
            
            result = model.generate_code(
                task="Create a function to check if a string is a palindrome",
                context=context,
                use_reasoning=False
            )
            
            print("\nGenerated code:")
            print(result["code"])
            print("\n✅ CodeModel integration working\n")
            
        except Exception as e:
            print(f"❌ CodeModel integration failed: {e}\n")
    else:
        print("⚠️  OPENAI_API_KEY not set, skipping integration test\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("VersaAI Code LLM Integration Tests")
    print("=" * 70 + "\n")
    
    # Always run these
    test_prompt_builder()
    test_code_extraction()
    
    # Run provider tests (skip if not configured)
    test_openai_llm()
    test_anthropic_llm()
    test_local_llm()
    # test_huggingface_llm()  # Skip by default (large download)
    
    # Integration test
    test_code_model_integration()
    
    print("=" * 70)
    print("Tests Complete!")
    print("=" * 70)
    print("""
Next steps:
1. Set OPENAI_API_KEY or ANTHROPIC_API_KEY for API tests
2. Download a GGUF model to ./models/ for local tests
3. Install llama-cpp-python for local model support
4. Try the CLI: versaai --provider openai --llm-model gpt-3.5-turbo
    """)


if __name__ == "__main__":
    main()
