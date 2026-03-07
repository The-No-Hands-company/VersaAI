# Multi-Model Code Assistant - User Guide

## Overview

VersaAI's Multi-Model Code Assistant automatically selects and uses the best available model for each coding task. Instead of manually choosing between models, the system intelligently routes your requests based on:

- **Task complexity** (simple function vs. complex architecture)
- **Programming language** (Python, C++, JavaScript, etc.)
- **Available system resources** (RAM, VRAM)
- **User preferences** (speed vs. quality)

## Model Space Requirements

Here are the 5 recommended models and their disk space requirements:

| Model | Size | RAM Required | Tier | Best For |
|-------|------|--------------|------|----------|
| **DeepSeek-Coder 1.3B** | 0.9GB | 4GB | Fast | Simple functions, quick tasks |
| **DeepSeek-Coder 6.7B** ⭐ | 4.1GB | 8GB | Balanced | General coding, recommended |
| **StarCoder2 7B** | 5.0GB | 8GB | Balanced | Multi-language, enterprise |
| **CodeLlama 7B** | 4.1GB | 8GB | Balanced | Algorithms, general purpose |
| **DeepSeek-Coder 33B** | 20GB | 32GB | Powerful | Complex refactoring, debugging |

**Total if downloading all 5 models:** ~34GB

## Quick Start

### 1. Download Models

#### Option A: Download All Models (Recommended for full capabilities)
```bash
python scripts/download_all_models.py
```

This interactive script will:
- Check your system RAM
- Show which models can run on your system
- Let you choose which models to download
- Download them automatically

#### Option B: Download Specific Models
```bash
python scripts/download_code_models.py --model deepseek-coder-6.7b --model starcoder2-7b
```

### 2. Start Multi-Model CLI

```bash
python versaai_cli.py --multi-model
```

Or if installed as a package:
```bash
versaai --multi-model
```

## Download Options

When running `download_all_models.py`, you'll see these options:

1. **Download ALL** - All models your system can run (auto-detected based on RAM)
2. **Download ESSENTIAL** - Just 1.3B + 6.7B (~5GB) - Good for most tasks
3. **Download BALANCED** - 1.3B + 6.7B + 7B (~10GB) - Great coverage
4. **Custom selection** - Pick exactly which models you want

### Example: Essential Setup (Fastest)

```bash
python scripts/download_all_models.py
# Select option 2 (ESSENTIAL)
# Downloads only: deepseek-coder-1.3b (0.9GB) + deepseek-coder-6.7b (4.1GB)
# Total: ~5GB
```

### Example: Full Setup (Best Quality)

```bash
python scripts/download_all_models.py
# Select option 1 (ALL)
# Downloads all available models that fit your RAM
# Total: 14GB - 34GB depending on your system
```

## How Multi-Model Selection Works

### Automatic Model Selection

The system analyzes your request and automatically picks the best model:

```python
# User prompt: "Write a simple Python function to add two numbers"
# → Selects: DeepSeek-Coder 1.3B (fast, sufficient for simple task)

# User prompt: "Debug this complex C++ memory leak with RAII patterns"
# → Selects: DeepSeek-Coder 33B or CodeLlama 7B (powerful, handles complexity)

# User prompt: "Refactor entire React application to use modern hooks"
# → Selects: StarCoder2 7B or DeepSeek 6.7B (balanced, good for JavaScript)
```

### Selection Criteria

1. **Task Complexity Detection**
   - Simple: Single functions, small scripts → Fast models (1.3B)
   - Medium: Classes, modules, APIs → Balanced models (6-7B)
   - Complex: Architecture, refactoring, debugging → Powerful models (13-33B)

2. **Language Optimization**
   - Python/C++/Java → DeepSeek-Coder (specialized)
   - Multi-language/Enterprise → StarCoder2 (600+ languages)
   - Algorithms/Performance → CodeLlama (Meta's optimizer)

3. **Resource Constraints**
   - Automatically excludes models that won't fit in available RAM
   - Falls back to smaller models if needed
   - Shows warnings if optimal model can't be used

## CLI Usage

### Multi-Model Mode
```bash
# Basic multi-model mode
versaai --multi-model

# With specific language
versaai --multi-model --lang rust

# Verbose mode (see which model is selected)
versaai --multi-model --verbose
```

### Single Model Mode
```bash
# Use specific model
versaai --provider llama-cpp --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

# With GPU acceleration
versaai --provider llama-cpp --model ~/.versaai/models/model.gguf --n-gpu-layers -1
```

### API Mode (Cloud Models)
```bash
# OpenAI
versaai --provider openai --model gpt-4-turbo

# Anthropic Claude
versaai --provider anthropic --model claude-3-sonnet-20240229
```

## Commands in CLI

Once in the CLI, you can use these commands:

```
/generate <description>  - Generate code from description
/explain <code>          - Explain how code works
/review <code>           - Review code quality
/debug <code>            - Debug code with errors
/refactor <code>         - Refactor code
/test <code>             - Generate unit tests
/lang <language>         - Change programming language
/file <path>             - Load code from file
/save <path>             - Save generated code
/models                  - Show available models (multi-model mode)
/switch <model>          - Switch to specific model
/history                 - Show conversation history
/clear                   - Clear conversation
help                     - Show all commands
quit                     - Exit
```

## Multi-Model Specific Commands

When running in multi-model mode, additional commands are available:

```
/models                  - List all available models and their status
/switch <model_name>     - Force use of specific model
/auto                    - Re-enable automatic model selection
/stats                   - Show system stats and model usage
```

### Example Session

```bash
$ versaai --multi-model

✅ Found 3 model(s):
  ✅ deepseek-coder-1.3b (0.9GB)
  ✅ deepseek-coder-6.7b (4.1GB)
  ⚠️  deepseek-coder-33b (20.0GB)

📊 System: 15.2GB / 16.0GB RAM available
   2 model(s) can run on your system

>>> Write a function to calculate fibonacci numbers

🎯 Selected model: deepseek-coder-1.3b (simple task, fast response)

def fibonacci(n: int) -> int:
    """Calculate nth fibonacci number"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

>>> /switch deepseek-coder-6.7b
✅ Switched to: deepseek-coder-6.7b

>>> Optimize the fibonacci function above with memoization

🎯 Using model: deepseek-coder-6.7b (forced by user)

from functools import lru_cache

@lru_cache(maxsize=None)
def fibonacci(n: int) -> int:
    """Calculate nth fibonacci number with memoization"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

## System Requirements

### Minimum (ESSENTIAL setup)
- **Disk Space:** 5GB
- **RAM:** 8GB
- **Models:** 2 (DeepSeek 1.3B + 6.7B)

### Recommended (BALANCED setup)
- **Disk Space:** 15GB
- **RAM:** 16GB
- **Models:** 3-4 (1.3B + 6.7B + 7B variants)

### Optimal (FULL setup)
- **Disk Space:** 35GB
- **RAM:** 32GB+
- **Models:** All 5 including 33B model
- **GPU:** Optional but speeds up inference significantly

## Performance Tips

1. **GPU Acceleration** (if you have NVIDIA GPU):
   ```bash
   versaai --multi-model --n-gpu-layers -1
   ```

2. **Reduce Context Window** (if running out of RAM):
   ```bash
   versaai --provider llama-cpp --model <path> --n-ctx 4096
   ```

3. **Use 4-bit Quantization** (already in downloaded GGUF files):
   - Q4_K_M models are 4-bit quantized (great quality/size balance)
   - Q5_K_M models are 5-bit quantized (higher quality, larger)
   - Q8_0 models are 8-bit (highest quality, much larger)

## Troubleshooting

### "No models found"
```bash
# Download models first
python scripts/download_all_models.py
```

### "Insufficient RAM"
The system will automatically fall back to smaller models. To force use of only small models:
```bash
# Download only the 1.3B model
python scripts/download_code_models.py --model deepseek-coder-1.3b
```

### "Model too slow"
- Use GPU acceleration with `--n-gpu-layers -1`
- Switch to faster model with `/switch deepseek-coder-1.3b`
- Reduce context with `--n-ctx 2048`

### "Poor code quality"
- Switch to larger model with `/switch deepseek-coder-6.7b`
- Or use API models: `versaai --provider openai --model gpt-4-turbo`

## Advanced: Custom Model Router

You can customize the model selection logic:

```python
from versaai.models.multi_model_manager import MultiModelManager
from versaai.models.model_router import ModelRouter

# Initialize
manager = MultiModelManager()

# Custom selection
task = "Implement binary search tree in C++"
language = "c++"

model = manager.select_model_for_task(
    task=task,
    language=language,
    prefer_speed=False,  # Prioritize quality
    prefer_quality=True
)

print(f"Selected: {model.name}")
print(f"Path: {model.path}")
```

## Integration with VersaAI Ecosystem

The multi-model system integrates with all VersaAI capabilities:

- **Memory Systems:** All models share conversation history
- **RAG (Retrieval-Augmented Generation):** Models can query your codebase
- **Agent Framework:** Models can be used by specialized agents
- **VersaOS/VersaModeling/VersaGameEngine:** Models assist in each domain

## Comparison: Multi-Model vs Single Model vs API

| Feature | Multi-Model (Local) | Single Model (Local) | API (OpenAI/Claude) |
|---------|---------------------|----------------------|---------------------|
| **Cost** | Free (after download) | Free (after download) | $10-100/month |
| **Privacy** | ✅ Fully private | ✅ Fully private | ❌ Sent to cloud |
| **Internet** | ❌ Not required | ❌ Not required | ✅ Required |
| **Quality** | ⭐⭐⭐⭐ (task-dependent) | ⭐⭐⭐ (fixed) | ⭐⭐⭐⭐⭐ (best) |
| **Speed** | ⭐⭐⭐⭐ (auto-optimized) | ⭐⭐⭐ (depends on model) | ⭐⭐⭐⭐⭐ (fast) |
| **Setup** | Medium (34GB download) | Easy (5GB download) | Very easy (just API key) |
| **Flexibility** | ⭐⭐⭐⭐⭐ (adaptive) | ⭐⭐ (one-size-fits-all) | ⭐⭐⭐⭐ (multiple models) |

## Conclusion

**Use Multi-Model Mode if:**
- You want the best balance of speed and quality
- You have 15GB+ disk space and 16GB+ RAM
- You want fully private, offline code assistance
- You work on diverse tasks (simple scripts to complex systems)

**Use Single Model Mode if:**
- You have limited disk space (<10GB)
- You prefer consistency over optimization
- You have a specific model preference

**Use API Mode if:**
- You want the absolute best quality
- You don't mind cloud dependency
- You have a budget for API calls
- You need multi-modal features (images, audio, etc.)

---

**Next Steps:**
1. Download models: `python scripts/download_all_models.py`
2. Start CLI: `versaai --multi-model`
3. Read [QUICKSTART_CODE_ASSISTANT.md](QUICKSTART_CODE_ASSISTANT.md) for more examples
4. Explore model router: `cat versaai/models/model_router.py`
