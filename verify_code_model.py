#!/usr/bin/env python3
"""
VersaAI Code Model - Quick Verification & Demo
Run this to verify the code model integration is working correctly.
"""

import sys
import os
from pathlib import Path

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_success(text):
    print(f"✅ {text}")

def print_error(text):
    print(f"❌ {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def check_imports():
    """Check if all required modules can be imported"""
    print_header("Checking Python Imports")
    
    modules = [
        ("versaai.models.code_model", "Code Model"),
        ("versaai.models.code_llm", "LLM Integrations"),
        ("versaai.cli", "CLI"),
        ("versaai.memory.conversation", "Conversation Manager"),
        ("versaai.agents.reasoning", "Reasoning Engine"),
        ("versaai.agents.planning", "Planning System"),
        ("versaai.rag.rag_system", "RAG System"),
    ]
    
    all_ok = True
    for module_name, desc in modules:
        try:
            __import__(module_name)
            print_success(f"{desc}: {module_name}")
        except ImportError as e:
            print_error(f"{desc}: {module_name} - {e}")
            all_ok = False
    
    return all_ok

def check_optional_deps():
    """Check optional dependencies"""
    print_header("Checking Optional Dependencies")
    
    deps = [
        ("llama_cpp", "llama-cpp-python (for local GGUF models)"),
        ("transformers", "transformers (for HuggingFace models)"),
        ("openai", "openai (for OpenAI API)"),
        ("anthropic", "anthropic (for Claude API)"),
        ("rich", "rich (for beautiful CLI)"),
    ]
    
    for module_name, desc in deps:
        try:
            __import__(module_name)
            print_success(desc)
        except ImportError:
            print_info(f"{desc} - Not installed (optional)")

def check_models():
    """Check for downloaded models"""
    print_header("Checking Downloaded Models")
    
    models_dir = Path.home() / ".versaai" / "models"
    
    if not models_dir.exists():
        print_info("Models directory doesn't exist yet")
        print_info(f"Download models with: python scripts/download_code_models.py --model deepseek-coder-6.7b")
        return
    
    gguf_files = list(models_dir.glob("*.gguf"))
    
    if not gguf_files:
        print_info("No models found")
        print_info("Download with: python scripts/download_code_models.py --model deepseek-coder-6.7b")
    else:
        print_success(f"Found {len(gguf_files)} model(s):")
        for model_file in gguf_files:
            size_gb = model_file.stat().st_size / (1024**3)
            print(f"  • {model_file.name} ({size_gb:.1f} GB)")

def check_api_keys():
    """Check for API keys"""
    print_header("Checking API Keys")
    
    keys = [
        ("OPENAI_API_KEY", "OpenAI"),
        ("ANTHROPIC_API_KEY", "Anthropic"),
        ("TOGETHER_API_KEY", "Together.ai"),
    ]
    
    any_key = False
    for env_var, name in keys:
        if os.getenv(env_var):
            print_success(f"{name} API key found")
            any_key = True
        else:
            print_info(f"{name} API key not set (optional)")
    
    if not any_key:
        print_info("\nSet up API keys with: python scripts/download_code_models.py --setup-api")

def show_usage():
    """Show usage examples"""
    print_header("Usage Examples")
    
    print("1. Interactive Launcher (recommended):")
    print("   ./scripts/launch_code_assistant.sh\n")
    
    print("2. With local model:")
    print("   python -m versaai.cli --provider llama-cpp \\")
    print("     --model ~/.versaai/models/deepseek-coder-6.7b.gguf\n")
    
    print("3. With OpenAI:")
    print("   python -m versaai.cli --provider openai --model gpt-4-turbo\n")
    
    print("4. With Anthropic:")
    print("   python -m versaai.cli --provider anthropic --model claude-3-sonnet-20240229\n")
    
    print("5. Download models:")
    print("   python scripts/download_code_models.py --model deepseek-coder-6.7b\n")

def show_documentation():
    """Show documentation links"""
    print_header("Documentation")
    
    docs = [
        ("QUICKSTART_CODE_MODEL.md", "Quick Start Guide"),
        ("docs/CODE_MODEL_STATUS.md", "Implementation Status"),
        ("docs/CODE_MODEL_SESSION_SUMMARY.md", "Session Summary"),
        ("docs/ACTION_PLAN.md", "Development Roadmap"),
    ]
    
    project_root = Path(__file__).parent.parent
    
    for filename, desc in docs:
        filepath = project_root / filename
        if filepath.exists():
            print_success(f"{desc}: {filename}")
        else:
            print_info(f"{desc}: {filename} (not found)")

def run_quick_test():
    """Run a quick functionality test"""
    print_header("Quick Functionality Test")
    
    try:
        from versaai.models.code_model import CodeModel, CodeContext, CodeTaskType
        from versaai.models.code_llm import build_code_prompt, extract_code_from_response
        
        # Test 1: Create model instance
        print_info("Creating CodeModel instance...")
        model = CodeModel(
            model_id="test-model",
            enable_memory=False,  # Disable memory for quick test
            enable_rag=False
        )
        print_success("CodeModel created successfully")
        
        # Test 2: Build prompt
        print_info("Testing prompt builder...")
        prompt = build_code_prompt(
            task="Create a function to add two numbers",
            language="python"
        )
        assert "python" in prompt.lower()
        print_success("Prompt builder working")
        
        # Test 3: Extract code
        print_info("Testing code extraction...")
        response = "Here's the code:\n```python\ndef add(a, b):\n    return a + b\n```"
        code = extract_code_from_response(response, "python")
        assert "def add" in code
        print_success("Code extraction working")
        
        print_success("\n✅ All functionality tests passed!")
        
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("\n" + "╔" + "="*68 + "╗")
    print("║" + " "*20 + "VersaAI Code Model Verification" + " "*17 + "║")
    print("╚" + "="*68 + "╝")
    
    # Run checks
    imports_ok = check_imports()
    check_optional_deps()
    check_models()
    check_api_keys()
    
    if imports_ok:
        run_quick_test()
    
    show_usage()
    show_documentation()
    
    # Final summary
    print_header("Summary")
    
    if imports_ok:
        print_success("✅ VersaAI Code Model is ready to use!")
        print_info("\nQuick Start:")
        print("  ./scripts/launch_code_assistant.sh")
        print("\nOr download a model first:")
        print("  python scripts/download_code_models.py --model deepseek-coder-6.7b")
    else:
        print_error("Some imports failed. Please check your installation.")
        print_info("Try: pip install -e .")
    
    print()

if __name__ == "__main__":
    main()
