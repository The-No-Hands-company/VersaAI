# VersaAI Multi-Model System - Quick Reference

## 📥 Installation & Setup

### 1. Download Models (Choose One Option)

#### Option A: Interactive Downloader (Recommended)
```bash
python scripts/download_all_models.py
```
**What it does:**
- Detects your system RAM
- Shows which models can run on your system
- Provides 4 download options:
  1. ALL (14-34GB) - Everything you can run
  2. ESSENTIAL (5GB) - Best balance (1.3B + 6.7B)
  3. BALANCED (10GB) - Great coverage (1.3B + 6.7B + 7B)
  4. CUSTOM - Pick specific models

#### Option B: Manual Download
```bash
python scripts/download_code_models.py --model deepseek-coder-6.7b
python scripts/download_code_models.py --model deepseek-coder-1.3b --model starcoder2-7b
```

### 2. Verify Installation
```bash
ls -lh ~/.versaai/models/
```
You should see .gguf files (0.9GB - 20GB each)

## 🚀 Usage

### Multi-Model Mode (Automatic Selection)
```bash
# Start VersaAI with automatic model selection
python versaai_cli.py --multi-model

# Or if installed as package
versaai --multi-model
```

### Single Model Mode (Manual Selection)
```bash
# Use specific model
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

# With GPU acceleration
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
  --n-gpu-layers -1
```

### API Mode (OpenAI/Claude)
```bash
# OpenAI
export OPENAI_API_KEY="your-key-here"
python versaai_cli.py --provider openai --model gpt-4-turbo

# Anthropic Claude
export ANTHROPIC_API_KEY="your-key-here"
python versaai_cli.py --provider anthropic --model claude-3-sonnet-20240229
```

## 📊 Model Comparison

| Model | Size | RAM | Speed | Quality | Best For |
|-------|------|-----|-------|---------|----------|
| **DeepSeek 1.3B** | 0.9GB | 4GB | ⚡⚡⚡⚡⚡ | ⭐⭐⭐ | Simple functions, quick tasks |
| **DeepSeek 6.7B** ⭐ | 4.1GB | 8GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | General coding (recommended) |
| **StarCoder2 7B** | 5.0GB | 8GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Multi-language, enterprise |
| **CodeLlama 7B** | 4.1GB | 8GB | ⚡⚡⚡⚡ | ⭐⭐⭐⭐ | Algorithms, optimization |
| **DeepSeek 33B** | 20GB | 32GB | ⚡⚡ | ⭐⭐⭐⭐⭐ | Complex debugging, refactoring |

## 🎯 How Model Selection Works

The system automatically picks the best model based on:

1. **Task Complexity**
   - "Write a simple function" → 1.3B (fast)
   - "Create a REST API" → 6.7B (balanced)
   - "Debug complex memory leak" → 33B (powerful)

2. **Programming Language**
   - Python/C++/Java → DeepSeek (specialized)
   - Multi-language → StarCoder2
   - Algorithms → CodeLlama

3. **Available RAM**
   - Automatically excludes models that won't fit
   - Falls back to smaller models if needed

## 🎮 CLI Commands

### Basic Commands
```
>>> Write a function to calculate fibonacci
>>> Explain how this code works: <paste code>
>>> Debug this error: <paste code>
>>> Refactor this class to use modern patterns
>>> Generate unit tests for this function
```

### Special Commands
```
/generate <description>  - Generate code
/explain <code>          - Explain code
/review <code>           - Code review
/debug <code>            - Debug code
/refactor <code>         - Refactor code
/test <code>             - Generate tests
/lang <language>         - Change language (python, c++, rust, etc.)
/file <path>             - Load file
/save <path>             - Save code

# Multi-model specific
/models                  - List available models
/switch <model>          - Force use of specific model
/auto                    - Re-enable automatic selection
/stats                   - System stats

help                     - Show all commands
quit                     - Exit
```

## 💾 System Requirements

### Minimum (ESSENTIAL)
- **Disk:** 5GB
- **RAM:** 8GB
- **Models:** DeepSeek 1.3B + 6.7B
- **Good for:** Most coding tasks

### Recommended (BALANCED)
- **Disk:** 15GB
- **RAM:** 16GB
- **Models:** 1.3B + 6.7B + StarCoder2 7B
- **Good for:** Professional development

### Optimal (FULL)
- **Disk:** 35GB
- **RAM:** 32GB+
- **GPU:** NVIDIA GPU (optional, speeds up inference)
- **Models:** All 5 including 33B
- **Good for:** Complex projects, enterprise

## 🔧 Troubleshooting

### "No models found"
```bash
# Download models first
python scripts/download_all_models.py
```

### "Insufficient RAM"
The system auto-falls back to smaller models. To force small models only:
```bash
python scripts/download_code_models.py --model deepseek-coder-1.3b
```

### Model is too slow
```bash
# Use GPU acceleration
python versaai_cli.py --multi-model --n-gpu-layers -1

# Or switch to faster model in CLI
>>> /switch deepseek-coder-1.3b
```

### Low quality responses
```bash
# Switch to larger model
>>> /switch deepseek-coder-6.7b

# Or use API models for best quality
python versaai_cli.py --provider openai --model gpt-4-turbo
```

### Out of disk space
```bash
# Remove large models you don't need
rm ~/.versaai/models/deepseek-coder-33b*.gguf

# Or download only essential models
python scripts/download_code_models.py --model deepseek-coder-6.7b
```

## 📚 Example Session

```bash
$ python versaai_cli.py --multi-model

✅ Found 3 model(s):
  ✅ deepseek-coder-1.3b (0.9GB)
  ✅ deepseek-coder-6.7b (4.1GB)
  ✅ starcoder2-7b (5.0GB)

📊 System: 15.2GB / 16.0GB RAM available
   3 model(s) can run on your system

🎯 Multi-model mode enabled - best model will be selected for each task

>>> Write a Python function to calculate prime numbers

🎯 Selected: deepseek-coder-1.3b (simple task, fast response)

def is_prime(n: int) -> bool:
    """Check if a number is prime"""
    if n < 2:
        return False
    for i in range(2, int(n ** 0.5) + 1):
        if n % i == 0:
            return False
    return True

>>> /switch deepseek-coder-6.7b
✅ Switched to: deepseek-coder-6.7b

>>> Optimize the prime function above with better algorithm

🎯 Using: deepseek-coder-6.7b

def is_prime(n: int) -> bool:
    """Optimized prime check using 6k±1 optimization"""
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

>>> /stats
📊 Multi-Model Statistics:
   Total models: 3
   Usable: 3
   Total size: 10.0GB
   Available RAM: 14.8GB / 16.0GB

>>> quit
Goodbye!
```

## 🎓 Advanced Usage

### Test Model Selection Programmatically
```python
from versaai.models.multi_model_manager import MultiModelManager

manager = MultiModelManager()

# Select model for task
task = "Implement binary search tree in C++"
model = manager.select_model_for_task(
    task=task,
    language="c++",
    prefer_quality=True
)

print(f"Selected: {model.name}")
print(f"Path: {model.path}")
```

### Check Available Models
```python
from versaai.models.multi_model_manager import MultiModelManager

manager = MultiModelManager()
stats = manager.get_stats()

print(f"Found {stats['total_models']} models")
for model in manager.list_models():
    print(f"  - {model['name']}: {model['size_gb']:.1f}GB")
```

## 📖 More Documentation

- **Full Guide:** `docs/MULTI_MODEL_GUIDE.md`
- **Implementation Details:** `MULTI_MODEL_COMPLETE.md`
- **Code Assistant:** `QUICKSTART_CODE_ASSISTANT.md`
- **Model Router:** `MODEL_ROUTER_COMPLETE.md`

## ✅ What You Have Now

1. ✅ **5 world-class code models** (DeepSeek, StarCoder2, CodeLlama)
2. ✅ **Automatic model selection** based on task complexity
3. ✅ **Resource-aware management** (never overload RAM)
4. ✅ **Complete CLI** with code generation, review, debugging, testing
5. ✅ **Offline & Private** - all processing happens locally
6. ✅ **Production-ready** - ready to use NOW

## 🚀 Next Steps

1. **Download models** (choose ESSENTIAL for 5GB or BALANCED for 10GB)
2. **Start coding** with `python versaai_cli.py --multi-model`
3. **Explore features** - try code generation, review, debugging
4. **Read docs** - see `docs/MULTI_MODEL_GUIDE.md` for more
5. **Continue development** - Phase 3-4 of ACTION_PLAN.md

---

**Your VersaAI is now a production-grade code assistant! 🎉**

For issues or questions, check:
- `TROUBLESHOOTING.md`
- `docs/FAQ.md`
- GitHub Issues
