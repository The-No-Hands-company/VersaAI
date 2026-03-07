# VersaAI Quick Start Guide - Code Assistant with Real AI

**Last Updated:** November 18, 2025  
**Time to Get Started:** 5-30 minutes

---

## 🎯 What You Get

VersaAI Code Assistant with **real AI models**:
- ✅ Generate production-quality code
- ✅ Explain complex algorithms
- ✅ Review and improve code
- ✅ Debug errors intelligently
- ✅ Create unit tests automatically
- ✅ Multi-language support (Python, JS, C++, etc.)

---

## 🚀 3 Ways to Get Started

### Option A: API (Fastest - 5 minutes)

**Best for:** Quick start, best quality, no local setup

```bash
# 1. Install VersaAI
cd VersaAI
pip install -e .
pip install openai rich

# 2. Set API key
export OPENAI_API_KEY="sk-..."

# 3. Start coding!
versaai --provider openai --llm-model gpt-3.5-turbo
```

**Cost:** ~$0.01 per interaction  
**Quality:** ⭐⭐⭐⭐⭐

### Option B: Local Model (Free - 30 minutes)

**Best for:** Privacy, no ongoing costs, offline use

```bash
# 1. Install VersaAI and llama.cpp
cd VersaAI
pip install -e .
pip install llama-cpp-python rich

# 2. Download model (one-time, ~4GB)
mkdir -p models
wget https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf -P ./models/

# 3. Start coding!
versaai --provider local --llm-model ./models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf
```

**Cost:** Free  
**Quality:** ⭐⭐⭐⭐  
**Privacy:** ✅ Complete (runs locally)

### Option C: HuggingFace (Advanced - 1 hour)

**Best for:** Custom models, fine-tuning, research

```bash
# 1. Install VersaAI and transformers
cd VersaAI
pip install -e .
pip install transformers torch accelerate rich

# 2. Start coding (model downloads automatically)
versaai --provider huggingface --llm-model bigcode/starcoder2-7b

# 3. Optional: Enable quantization to save memory
versaai --provider huggingface --llm-model bigcode/starcoder2-7b --load-in-8bit
```

**Cost:** Free  
**Quality:** ⭐⭐⭐⭐  
**Note:** First run downloads ~14GB model

---

## 💻 CLI Usage

### Interactive Mode

```bash
# Start the assistant
versaai --provider openai --llm-model gpt-3.5-turbo

# You'll see:
VersaAI [python]> 
```

### Commands

```bash
# Generate code (natural language)
VersaAI [python]> Create a function to calculate factorial with memoization

# Explain code
VersaAI [python]> /explain
# Then paste your code and press Ctrl+D

# Review code for issues
VersaAI [python]> /review
# Paste code and Ctrl+D

# Debug an error
VersaAI [python]> /debug
# Paste buggy code, then enter error message

# Generate tests
VersaAI [python]> /test
# Paste code to test

# Change language
VersaAI [python]> /lang javascript
VersaAI [javascript]> Create a React component for a todo list

# Show help
VersaAI [python]> /help

# Exit
VersaAI [python]> /quit
```

---

## 🐍 Python API

### Basic Usage

```python
from versaai.models import CodeModel, CodeContext

# Initialize (picks up your provider from installation)
model = CodeModel(
    llm_provider="openai",
    llm_model="gpt-3.5-turbo"
)

# Generate code
result = model.generate_code(
    task="Create a binary search function",
    context=CodeContext(
        language="python",
        requirements=["Add type hints", "Include docstring"]
    )
)

print(result["code"])
```

### With Memory (Multi-turn)

```python
model = CodeModel(
    llm_provider="openai",
    llm_model="gpt-3.5-turbo",
    enable_memory=True  # Remember conversation
)

# First request
result1 = model.generate_code(
    "Create a User model with SQLAlchemy",
    CodeContext(language="python")
)

# Second request - knows about User model!
result2 = model.generate_code(
    "Now create an API to get all users",
    CodeContext(language="python", framework="FastAPI")
)
```

### Different Providers

```python
# OpenAI
model = CodeModel(
    llm_provider="openai",
    llm_model="gpt-4-turbo"
)

# Anthropic Claude
model = CodeModel(
    llm_provider="anthropic",
    llm_model="claude-3-sonnet-20240229"
)

# Local model
model = CodeModel(
    llm_provider="local",
    llm_model="./models/deepseek-coder.gguf"
)

# HuggingFace
model = CodeModel(
    llm_provider="huggingface",
    llm_model="bigcode/starcoder2-7b"
)
```

---

## 📦 Installation Details

### Minimal (CLI only)

```bash
cd VersaAI
pip install -e .
pip install openai rich  # or anthropic, or llama-cpp-python
```

### Full (All providers)

```bash
cd VersaAI
pip install -e .

# All LLM providers
pip install llama-cpp-python  # Local models
pip install transformers torch accelerate  # HuggingFace
pip install openai  # OpenAI API
pip install anthropic  # Anthropic API

# UI enhancement
pip install rich

# Optional: GPU support for local models
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall
```

### Development Setup

```bash
cd VersaAI
pip install -e ".[dev]"  # Install with dev dependencies
```

---

## 🔧 Configuration

### Environment Variables

```bash
# API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Optional: Default provider
export VERSAAI_PROVIDER="openai"
export VERSAAI_MODEL="gpt-3.5-turbo"
```

### Config File (Future)

```yaml
# ~/.versaai/config.yaml
default_provider: openai
default_model: gpt-3.5-turbo
enable_memory: true
enable_rag: true
```

---

## 🎓 Examples

### See Full Examples

```bash
# View example code
cat examples/code_assistant_example.py

# Run examples (requires API key or local model)
python3 examples/code_assistant_example.py
```

### Quick Test

```bash
# Test without LLM (just infrastructure)
python3 tests/test_code_llm_integration.py

# Test with OpenAI
export OPENAI_API_KEY="sk-..."
python3 examples/code_assistant_example.py
```

---

## 🆘 Troubleshooting

### "Module not found: versaai"

```bash
# Install in editable mode
cd VersaAI
pip install -e .
```

### "API key not found"

```bash
# Set environment variable
export OPENAI_API_KEY="sk-..."

# Verify
echo $OPENAI_API_KEY
```

### "Out of memory" (local models)

```bash
# Use quantization
versaai --provider hf --llm-model bigcode/starcoder2-7b --load-in-8bit

# Or smaller model
versaai --provider local --llm-model ./models/starcoder-1b.gguf
```

### "llama.cpp failed to load model"

```bash
# Reinstall with GPU support
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall

# Or CPU only
pip install llama-cpp-python
```

### "Model download too slow"

```bash
# Use HuggingFace CLI for better download
pip install huggingface_hub
huggingface-cli download TheBloke/deepseek-coder-6.7B-instruct-GGUF --local-dir ./models/
```

---

## 📚 Documentation

- **Full Guide:** `docs/CODE_ASSISTANT_INTEGRATION.md`
- **Implementation:** `docs/CODE_MODEL_COMPLETE.md`
- **Training Resources:** `docs/CODE_MODEL_TRAINING_RESOURCES.md`
- **Action Plan:** `docs/ACTION_PLAN.md`

---

## 🎯 Next Steps

1. **Choose your setup** (API, Local, or HuggingFace)
2. **Install dependencies** (5-30 minutes)
3. **Try the CLI** (`versaai --provider ... --llm-model ...`)
4. **Read examples** (`examples/code_assistant_example.py`)
5. **Integrate into your workflow**

---

## 💡 Tips

### For Best Results

- **GPT-4 Turbo** - Complex algorithms, architecture design
- **Claude 3 Sonnet** - Code explanation, documentation
- **GPT-3.5 Turbo** - Quick prototypes, simple tasks
- **DeepSeek Coder** - Local development, privacy-sensitive

### Cost Optimization

- Use **GPT-3.5** for simple tasks ($0.002/request)
- Use **GPT-4** only for complex problems ($0.03/request)
- Use **local models** for experimentation (free)
- Enable **memory** to reduce redundant context

### Performance Tips

- **Local models:** Use GPU acceleration (`--gpu-layers -1`)
- **HuggingFace:** Enable quantization (`--load-in-8bit`)
- **APIs:** Use streaming for long responses (future feature)

---

## ✅ Quick Reference

| Need | Use This |
|------|----------|
| **Best quality** | `--provider openai --llm-model gpt-4-turbo` |
| **Fastest** | `--provider openai --llm-model gpt-3.5-turbo` |
| **Free/Private** | `--provider local --llm-model ./models/deepseek.gguf` |
| **Good balance** | `--provider anthropic --llm-model claude-3-sonnet` |
| **Multi-language** | Any provider works, specify with `/lang` command |

---

## 🚀 You're Ready!

Start generating code with real AI:

```bash
pip install -e . && pip install openai rich
export OPENAI_API_KEY="sk-..."
versaai --provider openai --llm-model gpt-3.5-turbo
```

**Happy coding! 🎉**
