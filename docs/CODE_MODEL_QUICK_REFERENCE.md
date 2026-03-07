# 🚀 VersaAI Code Model - Quick Reference Card

**Status:** ✅ **READY TO USE** | **Date:** 2025-11-18

---

## ⚡ Quick Start (3 Commands)

```bash
# 1. Download a code model
python scripts/download_code_models.py --model deepseek-coder-6.7b --install-deps

# 2. Launch the assistant
./scripts/launch_code_assistant.sh

# 3. Start coding!
VersaAI> generate a binary search function in python
```

---

## 📋 What Can It Do?

| Feature | Command | Description |
|---------|---------|-------------|
| **Generate Code** | `generate <task>` | Create code from description |
| **Explain Code** | `explain <code>` | Understand what code does |
| **Review Code** | `review <code>` | Get improvement suggestions |
| **Debug Code** | `debug <code> <error>` | Fix bugs and errors |
| **Refactor Code** | `refactor <code>` | Improve code structure |
| **Generate Tests** | `test <code>` | Create unit tests |
| **Optimize Code** | `optimize <code>` | Improve performance |
| **Document Code** | N/A | Generate docstrings |

**Languages:** Python, JavaScript, TypeScript, Rust, C++, Go, Java, and more!

---

## 🎯 Model Options

### Local Models (FREE - Private - No internet needed)

| Model | Size | RAM | Quality | Command |
|-------|------|-----|---------|---------|
| deepseek-coder-1.3b | 0.9GB | 2GB | ⭐⭐⭐ | `--model deepseek-coder-1.3b` |
| **deepseek-coder-6.7b** ⭐ | 4.1GB | 8GB | ⭐⭐⭐⭐⭐ | `--model deepseek-coder-6.7b` |
| starcoder2-7b | 5.0GB | 8GB | ⭐⭐⭐⭐⭐ | `--model starcoder2-7b` |

### Cloud APIs (PAID - Powerful - Requires API key)

| Provider | Model | Quality | Cost/1K tokens |
|----------|-------|---------|----------------|
| OpenAI | gpt-4-turbo | ⭐⭐⭐⭐⭐⭐ | ~$0.01 |
| OpenAI | gpt-3.5-turbo | ⭐⭐⭐⭐ | ~$0.0005 |
| Anthropic | claude-3-sonnet | ⭐⭐⭐⭐⭐ | ~$0.003 |

---

## 🔧 Common Commands

```bash
# List available models
python scripts/download_code_models.py --list

# Download model
python scripts/download_code_models.py --model deepseek-coder-6.7b

# Setup API keys
python scripts/download_code_models.py --setup-api

# Launch with local model
python -m versaai.cli --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

# Launch with OpenAI
export OPENAI_API_KEY="sk-..."
python -m versaai.cli --provider openai --model gpt-4-turbo

# Launch with Claude
export ANTHROPIC_API_KEY="sk-ant-..."
python -m versaai.cli --provider anthropic --model claude-3-sonnet-20240229

# GPU acceleration
python -m versaai.cli --provider llama-cpp \
  --model ~/.versaai/models/model.gguf \
  --n-gpu-layers -1  # Use all GPU layers

# Help
python -m versaai.cli --help
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART_CODE_MODEL.md](../QUICKSTART_CODE_MODEL.md) | Detailed quick start guide |
| [CODE_MODEL_STATUS.md](CODE_MODEL_STATUS.md) | Implementation status |
| [CODE_MODEL_SESSION_SUMMARY.md](CODE_MODEL_SESSION_SUMMARY.md) | Development summary |
| [ACTION_PLAN.md](ACTION_PLAN.md) | Full roadmap |

---

## ❓ FAQ

**Q: Do I need to train a model?**  
A: No! Pre-trained models (DeepSeek-Coder, StarCoder2) are excellent and ready to use.

**Q: Which model should I use?**  
A: **deepseek-coder-6.7b** - Best balance of quality and performance.

**Q: Can I use it offline?**  
A: Yes! Local models work completely offline.

**Q: How much does it cost?**  
A: Local models are FREE. Cloud APIs charge per token (~$0.0005-$0.01/1K tokens).

**Q: Is my code private?**  
A: Yes with local models. Cloud APIs send code to the provider.

**Q: What's next?**  
A: Build specialized agents, integrate with your workflow, fine-tune on your codebase.

---

## ✅ Verification

Run this to verify everything works:

```bash
python verify_code_model.py
```

---

## 🎯 Recommended Setup

**For most users:**
```bash
# 1. Download DeepSeek-Coder 6.7B
python scripts/download_code_models.py --model deepseek-coder-6.7b --install-deps

# 2. Launch
./scripts/launch_code_assistant.sh
```

**For API users:**
```bash
# 1. Setup API key
export OPENAI_API_KEY="sk-..."

# 2. Launch
python -m versaai.cli --provider openai --model gpt-3.5-turbo
```

---

**Ready to code?** 🚀

```bash
./scripts/launch_code_assistant.sh
```

---

**VersaAI - Production-Grade AI for Everyone**
