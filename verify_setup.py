#!/usr/bin/env python3
"""
VersaAI Setup Verification Script
Verifies that the hybrid architecture is properly configured.
"""

import sys
import os

def check_python_package():
    """Verify Python package structure"""
    print("=" * 60)
    print("CHECKING PYTHON PACKAGE")
    print("=" * 60)
    
    try:
        import versaai
        print(f"✅ versaai package found (v{versaai.__version__})")
    except ImportError as e:
        print(f"❌ versaai package not found: {e}")
        return False
    
    return True

def check_cpp_bindings():
    """Verify C++ bindings are available"""
    print("\n" + "=" * 60)
    print("CHECKING C++ BINDINGS")
    print("=" * 60)
    
    try:
        from versaai import versaai_core
        print("✅ C++ bindings imported successfully")
        
        # Check Logger
        logger = versaai_core.Logger.get_instance()
        logger.info("Verification test", "VerifyScript")
        print("✅ Logger working (check logs above)")
        
        # Check what's available
        components = [attr for attr in dir(versaai_core) if not attr.startswith('_')]
        print(f"✅ Available components: {', '.join(components)}")
        
        return True
        
    except ImportError as e:
        print(f"❌ C++ bindings not available: {e}")
        print("   Build them with: cd bindings/build && ninja && ninja install")
        return False
    except Exception as e:
        print(f"❌ Error testing bindings: {e}")
        return False

def check_rag_system():
    """Verify RAG system is available"""
    print("\n" + "=" * 60)
    print("CHECKING RAG SYSTEM")
    print("=" * 60)
    
    try:
        from versaai.rag import RAGPipeline, QueryDecomposer, PlannerAgent, CriticAgent
        print("✅ RAG components imported successfully")
        
        # Try to create instances (without actual models)
        try:
            decomposer = QueryDecomposer(use_llm=False)
            print("✅ QueryDecomposer instantiated")
        except:
            print("⚠️  QueryDecomposer needs configuration")
        
        return True
        
    except ImportError as e:
        print(f"❌ RAG system not available: {e}")
        return False

def check_documentation():
    """Verify key documentation exists"""
    print("\n" + "=" * 60)
    print("CHECKING DOCUMENTATION")
    print("=" * 60)
    
    docs = [
        "QUICKSTART.md",
        "SUMMARY_2025-11-18.md",
        "docs/ACTION_PLAN.md",
        "docs/HYBRID_ARCHITECTURE_STATUS.md",
        "docs/Development_Roadmap.md",
    ]
    
    all_found = True
    for doc in docs:
        if os.path.exists(doc):
            print(f"✅ {doc}")
        else:
            print(f"❌ {doc} not found")
            all_found = False
    
    return all_found

def check_build_system():
    """Verify build system is configured"""
    print("\n" + "=" * 60)
    print("CHECKING BUILD SYSTEM")
    print("=" * 60)
    
    checks = [
        ("bindings/CMakeLists.txt", "CMake configuration"),
        ("bindings/versaai_bindings.cpp", "Minimal bindings"),
        ("bindings/versaai_bindings.cpp.full", "Comprehensive bindings (needs fix)"),
    ]
    
    all_found = True
    for path, desc in checks:
        if os.path.exists(path):
            print(f"✅ {desc}: {path}")
        else:
            print(f"❌ {desc}: {path} not found")
            all_found = False
    
    # Check for built bindings
    import glob
    bindings = glob.glob("versaai/versaai_core*.so") + glob.glob("versaai/versaai_core*.pyd")
    if bindings:
        print(f"✅ Built bindings: {bindings[0]}")
    else:
        print("⚠️  No built bindings found - run: cd bindings/build && ninja install")
    
    return all_found

def main():
    """Run all checks"""
    print("\n" + "🔍 " * 20)
    print("VersaAI SETUP VERIFICATION")
    print("🔍 " * 20 + "\n")
    
    results = {
        "Python Package": check_python_package(),
        "C++ Bindings": check_cpp_bindings(),
        "RAG System": check_rag_system(),
        "Documentation": check_documentation(),
        "Build System": check_build_system(),
    }
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {name}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ ALL CHECKS PASSED - VersaAI is properly configured!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Read QUICKSTART.md")
        print("2. Follow docs/ACTION_PLAN.md")
        print("3. Start with fixing comprehensive bindings")
        return 0
    else:
        print("❌ SOME CHECKS FAILED - Review errors above")
        print("=" * 60)
        print("\nQuick fixes:")
        print("- Build bindings: cd bindings/build && ninja install")
        print("- Install package: pip install -e .")
        print("- Read QUICKSTART.md for help")
        return 1

if __name__ == "__main__":
    sys.exit(main())
