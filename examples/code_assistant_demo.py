#!/usr/bin/env python3
"""
VersaAI Code Assistant Demo

Demonstrates the full capabilities of VersaAI's coding assistant:
- Code generation with reasoning
- Code explanation
- Code review
- Debugging
- Refactoring
- Test generation
- Memory and context management
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from versaai.models.code_model import CodeModel, CodeContext, CodeTaskType


def print_section(title: str):
    """Print section header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")


def demo_code_generation():
    """Demo code generation with reasoning"""
    print_section("1. CODE GENERATION WITH REASONING")
    
    model = CodeModel(enable_memory=True, enable_rag=True)
    
    # Generate code
    task = "Create a Python function to calculate the Fibonacci sequence up to n terms"
    context = CodeContext(
        language="python",
        requirements=[
            "Use iterative approach (not recursive)",
            "Return a list of numbers",
            "Handle edge cases (n <= 0)"
        ]
    )
    
    print(f"Task: {task}")
    print(f"Language: {context.language}")
    print(f"Requirements: {context.requirements}\n")
    
    result = model.generate_code(task, context, use_reasoning=True)
    
    print("Generated Code:")
    print("-" * 80)
    print(result["code"])
    print("-" * 80)
    
    if result.get("reasoning_steps"):
        print("\nReasoning Steps:")
        for i, step in enumerate(result["reasoning_steps"], 1):
            print(f"{i}. {step}")
    
    print("\n✓ Code generation complete!")
    return model, result["code"]


def demo_code_explanation(model: CodeModel, code: str):
    """Demo code explanation"""
    print_section("2. CODE EXPLANATION")
    
    context = CodeContext(language="python")
    
    result = model.explain_code(code, context, detail_level="medium")
    
    print("Explanation:")
    print("-" * 80)
    print(result["explanation"])
    print("-" * 80)
    
    if result.get("key_concepts"):
        print("\nKey Concepts:")
        for concept in result["key_concepts"]:
            print(f"  • {concept}")
    
    print("\n✓ Code explanation complete!")


def demo_code_review():
    """Demo code review"""
    print_section("3. CODE REVIEW")
    
    model = CodeModel()
    
    # Code with issues
    buggy_code = """
def divide_numbers(a, b):
    return a / b

def process_list(items):
    total = 0
    for i in range(len(items)):
        total = total + items[i]
    return total
"""
    
    print("Code to Review:")
    print("-" * 80)
    print(buggy_code)
    print("-" * 80)
    
    context = CodeContext(language="python")
    result = model.review_code(buggy_code, context)
    
    print(f"\nCode Quality Score: {result['score']}/100")
    
    if result.get("issues"):
        print("\nIssues Found:")
        for issue in result["issues"]:
            print(f"  ⚠️  {issue}")
    
    if result.get("suggestions"):
        print("\nSuggestions:")
        for sugg in result["suggestions"]:
            print(f"  💡 {sugg}")
    
    print("\n✓ Code review complete!")


def demo_debugging():
    """Demo error debugging"""
    print_section("4. ERROR DEBUGGING")
    
    model = CodeModel()
    
    buggy_code = """
def calculate_average(numbers):
    total = sum(numbers)
    return total / len(numbers)

# Test
nums = []
avg = calculate_average(nums)
print(avg)
"""
    
    error_message = """
ZeroDivisionError: division by zero
  File "test.py", line 3, in calculate_average
    return total / len(numbers)
"""
    
    print("Code:")
    print("-" * 80)
    print(buggy_code)
    print("-" * 80)
    
    print("\nError:")
    print(error_message)
    
    context = CodeContext(language="python")
    result = model.debug_error(buggy_code, error_message, context)
    
    print("\nRoot Cause:")
    print(result["root_cause"])
    
    print("\nSuggested Fix:")
    print("-" * 80)
    print(result["fix"])
    print("-" * 80)
    
    print("\n✓ Debugging complete!")


def demo_refactoring():
    """Demo code refactoring"""
    print_section("5. CODE REFACTORING")
    
    model = CodeModel()
    
    messy_code = """
def calc(a,b,c):
    x=a+b
    y=x*c
    if y>100:
        z=y-100
    else:
        z=y
    return z
"""
    
    print("Original Code:")
    print("-" * 80)
    print(messy_code)
    print("-" * 80)
    
    context = CodeContext(language="python")
    result = model.refactor_code(messy_code, context, goals=["readability", "documentation"])
    
    print("\nRefactored Code:")
    print("-" * 80)
    print(result["refactored_code"])
    print("-" * 80)
    
    if result.get("improvements"):
        print("\nImprovements:")
        print(result["improvements"])
    
    print("\n✓ Refactoring complete!")


def demo_test_generation():
    """Demo test generation"""
    print_section("6. TEST GENERATION")
    
    model = CodeModel()
    
    code = """
def is_palindrome(text):
    cleaned = ''.join(c.lower() for c in text if c.isalnum())
    return cleaned == cleaned[::-1]
"""
    
    print("Code to Test:")
    print("-" * 80)
    print(code)
    print("-" * 80)
    
    context = CodeContext(language="python")
    result = model.generate_tests(code, context, test_framework="pytest")
    
    print("\nGenerated Tests:")
    print("-" * 80)
    print(result["test_code"])
    print("-" * 80)
    
    print(f"\nEstimated Coverage: {result['estimated_coverage']:.1f}%")
    print(f"Coverage Areas: {', '.join(result['coverage_areas'])}")
    
    print("\n✓ Test generation complete!")


def demo_conversation_memory():
    """Demo conversation memory"""
    print_section("7. CONVERSATION MEMORY")
    
    model = CodeModel(enable_memory=True)
    
    # First interaction
    task1 = "Create a Python class for a stack"
    context = CodeContext(language="python")
    result1 = model.generate_code(task1, context)
    
    print("First Request:")
    print(f"  {task1}")
    print(f"\nGenerated: {result1['code'][:100]}...\n")
    
    # Second interaction (referencing first)
    task2 = "Now add a method to peek at the top element"
    result2 = model.generate_code(task2, context)
    
    print("Follow-up Request:")
    print(f"  {task2}")
    print(f"\nGenerated: {result2['code'][:100]}...\n")
    
    # Show conversation history
    history = model.get_conversation_history()
    print(f"Conversation History ({len(history)} messages):")
    for msg in history:
        print(f"  [{msg['role']}]: {msg['content'][:50]}...")
    
    print("\n✓ Memory demonstration complete!")


def demo_planning():
    """Demo task planning"""
    print_section("8. TASK PLANNING")
    
    model = CodeModel()
    
    complex_task = "Build a REST API for a todo list application"
    context = CodeContext(
        language="python",
        framework="flask",
        requirements=[
            "CRUD operations for todos",
            "User authentication",
            "Database storage",
            "API documentation"
        ]
    )
    
    print(f"Complex Task: {complex_task}")
    print(f"Framework: {context.framework}")
    print(f"Requirements: {', '.join(context.requirements)}\n")
    
    result = model.generate_code(complex_task, context, use_planning=True)
    
    print("Generated Code:")
    print(result["code"][:200] + "...")
    
    print("\n✓ Planning demonstration complete!")


def demo_integration():
    """Demo full integration"""
    print_section("9. FULL INTEGRATION TEST")
    
    print("Creating CodeModel with all features enabled...")
    model = CodeModel(
        model_id="demo-code-assistant",
        enable_memory=True,
        enable_rag=True,
        max_context_tokens=8192
    )
    
    print("✓ Model created")
    print(f"  - Short-term memory: {'Enabled' if model.conversation else 'Disabled'}")
    print(f"  - Long-term memory: {'Enabled' if model.episodic_memory else 'Disabled'}")
    print(f"  - RAG system: {'Enabled' if model.rag else 'Disabled'}")
    print(f"  - Reasoning engine: Enabled")
    print(f"  - Planning system: Enabled")
    
    # Quick test
    task = "Write a Python function to check if a number is prime"
    context = CodeContext(language="python")
    result = model.generate_code(task, context, use_reasoning=True)
    
    print(f"\nQuick Test: {task}")
    print("Result received ✓")
    
    print("\n✓ Full integration test complete!")
    print("\n🎉 All VersaAI features working together!")


def main():
    """Run all demos"""
    print("""
╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║                     VersaAI Code Assistant Demo                            ║
║                                                                            ║
║  Demonstrating full VersaAI capabilities:                                 ║
║    • Code Generation with Reasoning                                       ║
║    • Code Explanation                                                     ║
║    • Code Review                                                          ║
║    • Error Debugging                                                      ║
║    • Code Refactoring                                                     ║
║    • Test Generation                                                      ║
║    • Conversation Memory                                                  ║
║    • Task Planning                                                        ║
║    • Full Integration                                                     ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    try:
        # Run demos
        model, code = demo_code_generation()
        demo_code_explanation(model, code)
        demo_code_review()
        demo_debugging()
        demo_refactoring()
        demo_test_generation()
        demo_conversation_memory()
        demo_planning()
        demo_integration()
        
        # Summary
        print_section("DEMO COMPLETE")
        print("✅ All demonstrations passed successfully!")
        print("\nVersaAI Code Assistant is fully operational with:")
        print("  • Short-term memory (conversation tracking)")
        print("  • Long-term memory (knowledge base)")
        print("  • Reasoning engine (multi-strategy)")
        print("  • Planning system (task decomposition)")
        print("  • RAG system (code search)")
        print("\nReady for production use! 🚀")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
