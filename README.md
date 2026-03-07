# VersaAI 🤖

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Status: Production](https://img.shields.io/badge/status-production-green.svg)]()

**Production-Grade Multi-Model AI Platform for Developers**

VersaAI is an intelligent code assistant that combines multiple AI models (local and cloud) to provide powerful coding assistance through a CLI, code editor integration, and Python API. Built for privacy, performance, and flexibility.

---

## ✨ Features

🤖 **Multi-Model AI** - Use DeepSeek, StarCoder, CodeLlama, Qwen, GPT-4, Claude  
🧠 **Intelligent Routing** - Automatically selects best model for each task  
💬 **CLI Code Assistant** - Interactive terminal-based AI pair programmer  
🔌 **Editor Integration** - Real-time AI assistance in NLPL Code Editor  
📚 **RAG System** - Understands your codebase with semantic search  
🔒 **Privacy-First** - Local models keep your code 100% private  
⚡ **High Performance** - Fast responses with optimized model loading  
💰 **Cost-Effective** - Free local models + optional cloud APIs

---

## 🚀 Quick Start

### Option 1: Full Stack (CLI + GUI + Editor Integration)

```bash
./launch.sh
# Select: 1. Full Stack (Backend + Flutter UI)
```

### Option 2: CLI Code Assistant Only

```bash
versaai
# Or: python3 versaai_cli.py
```

### Option 3: Flutter Desktop UI

```bash
cd ui && ./scripts/run_with_backend.sh
```

### Option 4: Code Editor Integration

```bash
python3 start_editor_bridge.py  # Backend server
# Then open NLPL Code Editor - AI features auto-connect
```

**Choose Your Model:**
- **Local Models** (Free, Private) - DeepSeek, StarCoder, CodeLlama, WizardCoder
- **OpenAI API** - GPT-4, GPT-3.5-Turbo (requires API key)
- **Anthropic API** - Claude 3.5, Claude 3 (requires API key)

📖 **See [INTEGRATION_COMPLETE.md](INTEGRATION_COMPLETE.md) for full documentation**

```
💬 Chat Mode:
> Explain async/await in Python

📝 Code Mode:
> /code Write a function to validate emails

🔧 File Mode:
> /file mycode.py  # Analyze specific file
```

**That's it!** You're now coding with AI assistance.

---

## 📖 Documentation

📘 **[Complete User Guide](COMPREHENSIVE_USER_GUIDE.md)** - Everything you need to know  
🚀 **[Quick Start Guide](QUICKSTART.md)** - Get started in 5 minutes  
📚 **[User Manual](docs/USER_GUIDE.md)** - In-depth documentation  
🎓 **[Tutorials](docs/TUTORIALS.md)** - Step-by-step guides  
🔌 **[Editor Integration](docs/CODE_EDITOR_INTEGRATION.md)** - Integrate with your editor  
🔀 **[Multi-Model Setup](docs/MULTI_MODEL_GUIDE.md)** - Use multiple models  
⚡ **[Quick Reference](docs/QUICK_REFERENCE.md)** - Command cheat sheet

---

## 🎯 Use Cases

| Use Case | Description |
|----------|-------------|
| **Code Completion** | Real-time suggestions as you type |
| **Code Explanation** | Understand unfamiliar code |
| **Refactoring** | Improve code quality and structure |
| **Debugging** | Find and fix bugs with AI help |
| **Test Generation** | Auto-generate unit tests |
| **Documentation** | Add comments and docstrings |
| **Code Review** | Get AI feedback on your code |
| **Learning** | Ask questions about programming concepts |

---

## 🔧 Installation Options

### Option 1: Basic (CLI Only)

```bash
pip install -e .
versaai
```

### Option 2: Full (CLI + Editor + All Features)

```bash
pip install -e ".[all]"

# Download models
versaai  # Interactive model downloader

# Start editor backend
python -m versaai.code_editor_bridge.server
```

### Option 3: Docker

```bash
docker pull versaai/versaai:latest
docker run -it versaai/versaai
```

---

## 🧠 Available Models

### Local Models (Free, Private)

| Model | Size | RAM | Best For |
|-------|------|-----|----------|
| **DeepSeek Coder 1.3B** | 834MB | 2GB | Fast completions |
| **DeepSeek Coder 6.7B** | 4.1GB | 8GB | Balanced quality |
| **StarCoder2 7B** | 4.3GB | 8GB | Code generation |
| **CodeLlama 7B** | 4.0GB | 8GB | General coding |
| **Qwen2.5-Coder 7B** | 4.4GB | 8GB | Latest, high quality |

### Cloud Models (Paid, Powerful)

| Model | Provider | Best For |
|-------|----------|----------|
| **GPT-4** | OpenAI | Complex tasks, architecture |
| **GPT-3.5 Turbo** | OpenAI | Fast, cost-effective |
| **Claude 3 Sonnet** | Anthropic | Explanations, docs |
| **Claude 3 Opus** | Anthropic | Highest quality |

---

## 🔌 Code Editor Integration

VersaAI integrates with the NLPL Code Editor for real-time AI assistance.

### Setup

```bash
# Terminal 1: Start VersaAI backend
cd VersaAI
python -m versaai.code_editor_bridge.server

# Terminal 2: Start Code Editor
cd code_editor
npm install
npm run dev
```

### Features in Editor

- **AI Chat Panel** - `Ctrl+Alt+V`
- **Code Completions** - Automatic suggestions
- **Explain Code** - Right-click → Explain
- **Refactor** - Right-click → Refactor
- **Generate Code** - Right-click → Generate
- **Debug** - Right-click → Debug

See **[Editor Integration Guide](docs/CODE_EDITOR_INTEGRATION.md)** for details.

---

## 🎓 Examples

### Example 1: Code Explanation

```bash
$ versaai

> Explain this code:
> def fibonacci(n):
>     return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)

AI: This is a recursive implementation of the Fibonacci sequence.
    It returns n for base cases (0 or 1), otherwise recursively
    calculates fib(n-1) + fib(n-2). Note: This has exponential
    time complexity O(2^n). Consider using memoization or iteration
    for better performance.
```

### Example 2: Code Generation

```bash
> /code Write a function to validate email addresses with regex

AI: Here's a robust email validation function:

    import re
    
    def validate_email(email: str) -> bool:
        """
        Validates email address format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
```

### Example 3: Multi-Model Mode

```bash
$ versaai --multi-model

> Complete: def quicksort(arr):
AI: [Using deepseek-1.3b for fast completion]
    def quicksort(arr):
        if len(arr) <= 1:
            return arr
        pivot = arr[len(arr) // 2]
        left = [x for x in arr if x < pivot]
        middle = [x for x in arr if x == pivot]
        right = [x for x in arr if x > pivot]
        return quicksort(left) + middle + quicksort(right)

> Design a scalable microservices architecture
AI: [Routing to GPT-4 for complex architecture]
    Here's a comprehensive microservices architecture...
```

---

## 🐛 Troubleshooting

### Issue: "Model not found"

```bash
# Download model
versaai  # Select "Download new model"

# Or manual download
cd ~/.versaai/models
wget <model-url>
```

### Issue: "Out of memory"

```bash
# Use smaller model
versaai --model deepseek-1.3b

# Or reduce context window
export VERSAAI_MAX_TOKENS=512
```

### Issue: "Can't connect to editor backend"

```bash
# Check if backend is running
ps aux | grep code_editor_bridge

# Start it
python -m versaai.code_editor_bridge.server
```

See **[Troubleshooting Guide](COMPREHENSIVE_USER_GUIDE.md#-troubleshooting)** for more.

---

## 🔒 Privacy & Security

### Local Models
- ✅ 100% offline, no data leaves your machine
- ✅ No telemetry, tracking, or analytics
- ✅ Your code stays private

### Cloud APIs (Optional)
- ⚠️ Data sent to OpenAI/Anthropic servers
- ⚠️ Subject to provider's privacy policy
- ✅ Can be disabled with `VERSAAI_LOCAL_ONLY=true`

---

## 📊 Benchmarks

| Task | DeepSeek 1.3B | DeepSeek 6.7B | GPT-4 |
|------|---------------|---------------|-------|
| **Code Completion** | 2s | 5s | 3s |
| **Code Generation** | 3s | 8s | 5s |
| **Explanation** | 4s | 10s | 6s |
| **Quality (1-10)** | 7/10 | 8.5/10 | 9.5/10 |
| **Cost** | Free | Free | ~$0.03/request |

---

## 🤝 Contributing

Contributions welcome! See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

### Development Setup

```bash
# Clone
git clone https://github.com/The-No-hands-Company/VersaAI.git
cd VersaAI

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black versaai/
isort versaai/
```

---

## 📄 License

MIT License - See **[LICENSE](LICENSE)** for details.

---

## 🙏 Acknowledgments

Built with:
- **llama.cpp** - Fast local model inference
- **OpenAI** & **Anthropic** - Cloud API support
- **Hugging Face** - Model hosting
- **langchain** - RAG framework

---

## 📞 Support

- **📖 Documentation**: See guides above
- **🐛 Bug Reports**: Open an issue on GitHub
- **💡 Feature Requests**: Open an issue with `[Feature]` tag
- **💬 Questions**: Open a discussion on GitHub

---

**Made with ❤️ by The No-hands Company**

**Start coding smarter with AI today!** 🚀

```bash
pip install -e .
versaai
```
