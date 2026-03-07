# VersaAI Code Model - Quick Start Guide

Complete guide to using VersaAI as a code assistant with local models or APIs.

## 🚀 Quick Start (3 Steps)

### Option A: Local Model (Free, Private)

```bash
# 1. Download a code model (recommended: deepseek-coder-6.7b)
python scripts/download_code_models.py --model deepseek-coder-6.7b --install-deps

# 2. Start the CLI
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

# 3. Start coding!
> generate a binary search function in python
```

### Option B: Cloud API (Paid, Powerful)

```bash
# 1. Setup API keys
python scripts/download_code_models.py --setup-api

# 2. Load environment
source ~/.versaai/config/api_keys.env

# 3. Start the CLI
python versaai_cli.py --provider openai --model gpt-4-turbo

# Or use Claude
python versaai_cli.py --provider anthropic --model claude-3-sonnet-20240229
```

---

## 📥 Available Models

### Local Models (GGUF format via llama.cpp)

| Model | Size | RAM | Quality | Use Case |
|-------|------|-----|---------|----------|
| **deepseek-coder-1.3b** | 0.9GB | 2GB | Good | Testing, low-end systems |
| **deepseek-coder-6.7b** ⭐ | 4.1GB | 8GB | Excellent | **RECOMMENDED** - Best balance |
| **starcoder2-7b** | 5.0GB | 8GB | Excellent | General coding |
| **codellama-7b** | 4.1GB | 8GB | Very Good | Meta's offering |
| **deepseek-coder-33b** | 20GB | 24GB+ | Outstanding | Highest quality (requires GPU) |

⭐ **Recommended for most users:** `deepseek-coder-6.7b`

```bash
# List all available models
python scripts/download_code_models.py --list

# Download specific model
python scripts/download_code_models.py --model deepseek-coder-6.7b

# Download multiple models
python scripts/download_code_models.py \
  --model deepseek-coder-1.3b \
  --model deepseek-coder-6.7b
```

### Cloud API Models

**OpenAI (Requires API key)**
- `gpt-4-turbo` - Most capable, expensive (~$0.01/1K tokens)
- `gpt-3.5-turbo` - Fast, cheap (~$0.0005/1K tokens)

**Anthropic (Requires API key)**
- `claude-3-opus-20240229` - Highest quality
- `claude-3-sonnet-20240229` - Balanced
- `claude-3-haiku-20240307` - Fast & cheap

**Together.ai (Requires API key - Cheaper alternatives)**
- Access to many open models (DeepSeek, CodeLlama, etc.)
- Much cheaper than OpenAI/Anthropic

---

## 🔧 Installation & Setup

### 1. Install Dependencies

```bash
# Option A: Install everything automatically
python scripts/download_code_models.py --install-deps

# Option B: Manual installation
pip install llama-cpp-python transformers torch openai anthropic
```

**For GPU acceleration (NVIDIA):**
```bash
# Install llama-cpp-python with CUDA support
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 2. Download Models

```bash
# Recommended: Download DeepSeek-Coder 6.7B
python scripts/download_code_models.py --model deepseek-coder-6.7b

# Alternative: Download smaller model for testing
python scripts/download_code_models.py --model deepseek-coder-1.3b

# Alternative: Download StarCoder2
python scripts/download_code_models.py --model starcoder2-7b
```

### 3. Configure APIs (Optional)

```bash
# Interactive setup
python scripts/download_code_models.py --setup-api

# Manual setup
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export TOGETHER_API_KEY="..."
```

---

## 💻 Using the CLI

### Start the CLI

**Local model:**
```bash
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf
```

**OpenAI:**
```bash
python versaai_cli.py --provider openai --model gpt-4-turbo
```

**Anthropic:**
```bash
python versaai_cli.py --provider anthropic --model claude-3-sonnet-20240229
```

### CLI Commands

Once inside the CLI:

```
> help                          # Show all commands
> generate <description>        # Generate code
> explain <code>                # Explain code
> review <code>                 # Review code for issues
> debug <code> <error>          # Debug errors
> refactor <code>               # Refactor code
> test <code>                   # Generate tests
> optimize <code>               # Optimize performance
> lang <language>               # Set language (python, javascript, rust, etc.)
> file <path>                   # Load file for context
> clear                         # Clear conversation
> quit                          # Exit
```

### Example Session

```
VersaAI Code Assistant v1.0
Using llama-cpp LLM: deepseek-coder-6.7b-instruct.Q4_K_M.gguf
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> lang python
✓ Language set to: python

> generate a function to validate email addresses using regex

📝 Generated Code:
╭──────────────────────────────────────────────────╮
│ import re                                         │
│                                                   │
│ def validate_email(email: str) -> bool:          │
│     """                                           │
│     Validate email address using regex.          │
│                                                   │
│     Args:                                         │
│         email: Email address to validate         │
│                                                   │
│     Returns:                                      │
│         bool: True if valid, False otherwise     │
│     """                                           │
│     pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'       │
│     return re.match(pattern, email) is not None  │
╰──────────────────────────────────────────────────╯

> test

📝 Generated Tests:
╭──────────────────────────────────────────────────╮
│ import pytest                                     │
│                                                   │
│ def test_validate_email_valid():                 │
│     assert validate_email("user@example.com")    │
│     assert validate_email("test.user@domain.co") │
│                                                   │
│ def test_validate_email_invalid():               │
│     assert not validate_email("invalid")         │
│     assert not validate_email("@example.com")    │
│     assert not validate_email("user@")           │
╰──────────────────────────────────────────────────╯

> quit
Goodbye! 👋
```

---

## 🎯 Features

### ✅ Currently Working

- **Code Generation** - Generate code from natural language
- **Code Explanation** - Understand what code does
- **Code Review** - Get suggestions for improvement
- **Debugging** - Help fix errors and bugs
- **Refactoring** - Improve code structure
- **Test Generation** - Generate unit tests
- **Documentation** - Generate docstrings and comments
- **Multi-language** - Python, JavaScript, TypeScript, Rust, C++, Go, Java, etc.
- **Conversation Memory** - Remembers context across turns
- **Syntax Highlighting** - Beautiful code display (with `rich` package)

### 🚧 Integrated VersaAI Features

The code model integrates with VersaAI's production infrastructure:

- **Short-term Memory** - Conversation tracking (implemented)
- **Long-term Memory** - Code knowledge base (implemented)
- **Reasoning Engine** - Chain-of-thought problem solving (implemented)
- **Planning System** - Task decomposition (implemented)
- **RAG System** - Code search and retrieval (implemented)
- **C++ Core** - High-performance logging and context (implemented)

---

## 📊 Performance Tips

### Local Models

**GPU Acceleration (Recommended):**
```bash
# Check GPU is being used
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
  --n-gpu-layers -1  # -1 = use all GPU layers
```

**CPU-only:**
```bash
# Use more threads
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
  --n-threads 8
```

### API Models

**Cost Optimization:**
- Use `gpt-3.5-turbo` for simple tasks
- Use `claude-3-haiku` for fast, cheap responses
- Use `gpt-4-turbo` / `claude-3-opus` for complex tasks only

**Rate Limiting:**
- Set `max_tokens` lower for shorter responses
- Use `temperature=0.2` for more deterministic output
- Use `temperature=0.8` for more creative code

---

## 🔍 Troubleshooting

### Model won't load

**Problem:** "Failed to load model"

**Solutions:**
```bash
# Check model file exists
ls -lh ~/.versaai/models/

# Verify download completed
python scripts/download_code_models.py --model deepseek-coder-6.7b

# Check disk space
df -h ~/.versaai/models/

# Try smaller model
python scripts/download_code_models.py --model deepseek-coder-1.3b
```

### Out of memory

**Problem:** "RuntimeError: Out of memory"

**Solutions:**
```bash
# Use smaller quantization
# Q4_K_M = 4-bit quantization (smaller, faster)
# Q5_K_M = 5-bit quantization (bigger, better quality)
# Q8_0 = 8-bit quantization (biggest, best quality)

# Reduce context size
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf \
  --n-ctx 4096  # Default is 8192

# Use smaller model
python scripts/download_code_models.py --model deepseek-coder-1.3b
```

### Slow generation

**Problem:** Code generation is slow

**Solutions:**
```bash
# Use GPU acceleration
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/model.gguf \
  --n-gpu-layers -1

# Use more CPU threads
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/model.gguf \
  --n-threads $(nproc)  # Use all CPU cores

# Use API instead (faster)
python versaai_cli.py --provider openai --model gpt-3.5-turbo
```

### API errors

**Problem:** "Authentication error" or "Rate limit exceeded"

**Solutions:**
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Load API keys
source ~/.versaai/config/api_keys.env

# Check API quota/billing
# OpenAI: https://platform.openai.com/usage
# Anthropic: https://console.anthropic.com/settings/billing

# Use local model instead
python versaai_cli.py --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf
```

---

## 📚 Resources

### Model Sources

- **HuggingFace Models:** https://huggingface.co/models?pipeline_tag=text-generation&other=code
- **TheBloke GGUF Collection:** https://huggingface.co/TheBloke
- **llama.cpp:** https://github.com/ggerganov/llama.cpp
- **Code Models Leaderboard:** https://huggingface.co/spaces/bigcode/bigcode-models-leaderboard

### API Documentation

- **OpenAI:** https://platform.openai.com/docs
- **Anthropic:** https://docs.anthropic.com/
- **Together.ai:** https://docs.together.ai/

### VersaAI Documentation

- **Architecture:** `docs/Architecture.md`
- **Development Roadmap:** `docs/Development_Roadmap.md`
- **Action Plan:** `docs/ACTION_PLAN.md`

---

## 🤝 Contributing

Found a bug or want to improve the code model? See `CONTRIBUTING.md`

---

## 📝 Next Steps

After you're comfortable with the code model:

1. **Integrate with VersaOS** - Use the code model in your OS projects
2. **Integrate with VersaModeling** - Generate 3D modeling scripts
3. **Integrate with VersaGameEngine** - Generate game logic
4. **Fine-tune on your code** - Train on your specific codebase
5. **Build custom agents** - Create specialized coding agents

See `docs/ACTION_PLAN.md` for the full development roadmap.

---

**VersaAI - Production-Grade AI for Everyone** 🚀
