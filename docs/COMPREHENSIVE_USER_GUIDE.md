# VersaAI: Complete User Documentation

**Version:** 1.0.0  
**Last Updated:** 2025-11-19  
**Status:** Production Ready ✅

> **The Single Source of Truth** - Everything you need to know about VersaAI, from installation to advanced usage

---

## 📖 Overview

**VersaAI** is a production-grade, multi-model AI platform that provides intelligent code assistance through multiple interfaces:
- **CLI Code Assistant** - Terminal-based AI pair programmer
- **Code Editor Integration** - Real-time AI in your editor  
- **Python API** - Programmatic access for custom tools
- **Multi-Model Router** - Intelligently selects the best model for each task

### Key Capabilities

✅ **Code Assistance** - Completions, explanations, refactoring, debugging  
✅ **Multi-Model** - DeepSeek, StarCoder, CodeLlama, Qwen, GPT-4, Claude  
✅ **Intelligent Routing** - Automatically selects best model per task  
✅ **RAG System** - Understands your codebase context  
✅ **Privacy-First** - Local models keep your code private  
✅ **Cost-Effective** - Free local models + optional cloud APIs

---

## 🎯 Quick Navigation

| I want to... | Go to |
|--------------|-------|
| **Install VersaAI** | [Installation Guide](#-installation) |
| **Use the CLI Assistant** | [CLI Quick Start](#-cli-code-assistant-quick-start) |
| **Integrate with my editor** | [Editor Integration](#-code-editor-integration) |
| **Download AI models** | [Model Setup](#-model-setup) |
| **Configure multi-model routing** | [Multi-Model Configuration](#-multi-model-configuration) |
| **Troubleshoot issues** | [Troubleshooting](#-troubleshooting) |
| **Learn advanced features** | [Advanced Usage](#-advanced-usage) |

---

## 📦 Installation

### Prerequisites

| Requirement | Version | Notes |
|------------|---------|-------|
| **Python** | 3.8+ | 3.10+ recommended |
| **pip** | 21.0+ | For package management |
| **Git** | Any | For cloning repository |
| **RAM** | 8GB minimum | 16GB+ for larger models |
| **Disk Space** | 5GB minimum | 20GB+ for multiple models |

### Step 1: Clone Repository

```bash
git clone https://github.com/The-No-hands-Company/VersaAI.git
cd VersaAI
```

### Step 2: Install VersaAI

```bash
# Install in development mode
pip install -e .

# Or install with optional dependencies
pip install -e ".[all]"
```

### Step 3: Verify Installation

```bash
versaai --version
versaai --help
```

**Expected output:**
```
VersaAI Code Assistant v1.0.0
Usage: versaai [OPTIONS] COMMAND [ARGS]...
```

✅ **Installation Complete!**

---

## 🚀 CLI Code Assistant: Quick Start

The CLI Code Assistant is your AI pair programmer in the terminal.

### Launch Code Assistant

```bash
versaai
```

This will launch an interactive setup wizard:

```
╔════════════════════════════════════════════════════════════════╗
║              VersaAI Code Assistant Launcher                   ║
╚════════════════════════════════════════════════════════════════╝

Select Model Type:

  1. Local Model (GGUF via llama.cpp) - Free, Private
  2. OpenAI API (GPT-4, GPT-3.5) - Paid, Powerful
  3. Anthropic API (Claude) - Paid, Powerful
  4. Placeholder Mode (No LLM) - Testing Only

Choice [1-4]:
```

### Option 1: Use Local Model (Recommended)

**Benefits:** Free, private, no internet required

1. Select option `1` (Local Model)
2. Choose from available models or download new ones

**Available Models:**

| Model | Size | RAM Required | Best For |
|-------|------|--------------|----------|
| **deepseek-coder-1.3b** | 834MB | 2GB | Fast, lightweight coding |
| **deepseek-coder-6.7b** | 4.1GB | 8GB | Balanced performance |
| **starcoder2-7b** | 4.3GB | 8GB | Code generation |
| **codellama-7b** | 4.0GB | 8GB | General coding |
| **qwen2.5-coder-7b** | 4.4GB | 8GB | Latest model, great quality |

### Option 2: Use Cloud API

**Benefits:** Most powerful, latest models

1. Select option `2` (OpenAI) or `3` (Anthropic)
2. Enter your API key when prompted
3. Select model (GPT-4, Claude, etc.)

**API Keys:**
- OpenAI: Get from https://platform.openai.com/api-keys
- Anthropic: Get from https://console.anthropic.com/

### Using the Assistant

Once launched, you can:

```
💬 Chat Mode:
> Explain how async/await works in Python

📝 Code Mode (use /code):
> /code Write a function to validate email addresses

🔧 File Mode (use /file):
> /file path/to/file.py  # Analyze specific file

🎯 Project Mode (use /project):
> /project  # Enable codebase context (RAG)
```

**Keyboard Shortcuts:**
- `Ctrl+D` or `/exit` - Exit assistant
- `Ctrl+C` - Cancel current request
- `Ctrl+L` - Clear screen
- `/help` - Show all commands

---

## 🎨 Code Editor Integration

VersaAI integrates with the NLPL Code Editor to provide real-time AI assistance.

### Setup (One-time)

#### 1. Install Code Editor

```bash
cd /path/to/code_editor
npm install
npx @electron/rebuild  # Rebuild native modules for Electron
```

#### 2. Start VersaAI Backend

```bash
cd /path/to/VersaAI
python -m versaai.code_editor_bridge.server
```

**Output:**
```
🚀 VersaAI Code Editor Bridge Server
📡 WebSocket server running on ws://localhost:9001
✅ Ready for connections
```

#### 3. Start Code Editor

```bash
cd /path/to/code_editor
npm run dev
```

### Using AI in the Editor

#### Open AI Assistant Panel

**Method 1:** Press `Ctrl+Alt+V`  
**Method 2:** Click the 🤖 icon in the left Activity Bar  
**Method 3:** Command Palette → "VersaAI: Toggle Assistant"

#### AI Features

| Feature | How to Use |
|---------|------------|
| **Chat with AI** | Type in the AI panel sidebar |
| **Explain Code** | Select code → Right-click → "Explain with AI" |
| **Generate Code** | Right-click → "Generate Code" → Describe |
| **Refactor Code** | Select code → Right-click → "Refactor with AI" |
| **Fix Bugs** | Select code → Right-click → "Debug with AI" |
| **Add Comments** | Select code → Right-click → "Document with AI" |
| **Code Completion** | Just type - AI suggests as you code |

#### Context-Aware Assistance

The AI knows:
- ✅ Current file you're editing
- ✅ Programming language
- ✅ Selected code
- ✅ Cursor position
- ✅ Project structure (with RAG enabled)

**Example Conversation:**
```
You: Explain this function
AI: This function validates email addresses using regex.
     It checks for valid format (user@domain.ext) and 
     returns True/False.

You: Can you make it more robust?
AI: [Provides improved version with edge case handling]
```

---

## 🧠 Model Setup

### Downloading Local Models

VersaAI provides an interactive model downloader.

#### Method 1: Using the Launcher

```bash
versaai
```

Select "Local Model" → Choose "Download new model" → Select from list

#### Method 2: Manual Download

```bash
# Download specific model
cd ~/.versaai/models

# DeepSeek Coder 1.3B (small, fast)
wget https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf

# DeepSeek Coder 6.7B (balanced)
wget https://huggingface.co/TheBloke/deepseek-coder-6.7b-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

# StarCoder2 7B (code generation)
wget https://huggingface.co/TheBloke/starcoder2-7b-GGUF/resolve/main/starcoder2-7b.Q4_K_M.gguf

# CodeLlama 7B (general coding)
wget https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf

# Qwen2.5-Coder 7B (latest, high quality)
wget https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct-GGUF/resolve/main/qwen2.5-coder-7b-instruct-q4_k_m.gguf
```

### Model Storage Locations

```
~/.versaai/
├── models/              # Downloaded model files (.gguf)
├── config/              # Configuration files
├── cache/               # Model cache and indexes
└── logs/                # Application logs
```

---

## 🔀 Multi-Model Configuration

VersaAI can use **multiple models simultaneously** and route tasks to the best model.

### Enable Multi-Model Router

Create `~/.versaai/config/models.yaml`:

```yaml
models:
  # Local Models
  - name: "deepseek-1.3b"
    type: "local"
    path: "~/.versaai/models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf"
    priority: 1
    tasks: ["completion", "chat", "simple_code"]
    
  - name: "deepseek-6.7b"
    type: "local"
    path: "~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
    priority: 2
    tasks: ["refactoring", "complex_code", "debugging"]
    
  - name: "starcoder2-7b"
    type: "local"
    path: "~/.versaai/models/starcoder2-7b.Q4_K_M.gguf"
    priority: 2
    tasks: ["code_generation", "boilerplate"]
    
  # Cloud Models (fallback)
  - name: "gpt-4"
    type: "openai"
    api_key: "${OPENAI_API_KEY}"
    priority: 3
    tasks: ["complex_reasoning", "architecture"]
    
  - name: "claude-3-sonnet"
    type: "anthropic"
    api_key: "${ANTHROPIC_API_KEY}"
    priority: 3
    tasks: ["explanation", "documentation"]

# Routing Rules
routing:
  strategy: "task_based"  # or "round_robin", "priority"
  
  task_mapping:
    code_completion: ["deepseek-1.3b", "starcoder2-7b"]
    code_generation: ["starcoder2-7b", "deepseek-6.7b", "gpt-4"]
    refactoring: ["deepseek-6.7b", "gpt-4"]
    debugging: ["deepseek-6.7b", "claude-3-sonnet"]
    explanation: ["claude-3-sonnet", "gpt-4"]
    chat: ["deepseek-1.3b", "gpt-4"]
  
  # Fallback order
  fallback_chain:
    - "deepseek-6.7b"
    - "gpt-4"
    - "claude-3-sonnet"
```

### Using Multi-Model Mode

```bash
# Launch with multi-model routing enabled
versaai --multi-model

# Or set in config
export VERSAAI_MULTI_MODEL=true
versaai
```

**How it works:**

1. **Task Analysis** - VersaAI analyzes your prompt
2. **Model Selection** - Chooses best model based on task type
3. **Execution** - Runs on selected model
4. **Fallback** - If model fails, tries next in chain

**Example:**

```
You: Complete this function: def validate_email(
AI: [Using deepseek-1.3b for fast completion]
    def validate_email(email: str) -> bool:
        import re
        pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        return bool(re.match(pattern, email))

You: Design a scalable microservices architecture for e-commerce
AI: [Routing to GPT-4 for complex architecture task]
    Here's a comprehensive microservices architecture...
```

---

## ⚙️ Configuration

### Configuration File Locations

```
~/.versaai/config/
├── settings.yaml       # Global settings
├── models.yaml         # Model configuration
└── api_keys.yaml       # API credentials (gitignored)
```

### Global Settings (`settings.yaml`)

```yaml
# General Settings
versaai:
  log_level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  default_model: "deepseek-coder-6.7b-instruct"
  cache_enabled: true
  
# Performance
performance:
  max_threads: 4
  context_window: 4096
  max_tokens: 2048
  temperature: 0.7
  
# RAG System
rag:
  enabled: true
  index_path: "~/.versaai/cache/codebase_index"
  chunk_size: 512
  overlap: 50
  
# Code Editor Bridge
editor_bridge:
  host: "localhost"
  port: 9001
  enable_completions: true
  completion_delay_ms: 300
  
# Privacy
privacy:
  anonymous_telemetry: false
  local_only: false  # Set true to disable all API models
```

### Environment Variables

```bash
# API Keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Model Settings
export VERSAAI_DEFAULT_MODEL="deepseek-6.7b"
export VERSAAI_TEMPERATURE="0.7"
export VERSAAI_MAX_TOKENS="2048"

# Features
export VERSAAI_MULTI_MODEL="true"
export VERSAAI_RAG_ENABLED="true"
export VERSAAI_LOCAL_ONLY="true"  # Disable API models

# Paths
export VERSAAI_HOME="~/.versaai"
export VERSAAI_MODELS_DIR="~/.versaai/models"
```

---

## 🔧 Advanced Usage

### RAG (Retrieval-Augmented Generation)

Enable AI to understand your entire codebase.

#### Setup RAG for Your Project

```bash
cd /your/project
versaai --index-project
```

**What this does:**
1. Scans all code files
2. Creates semantic embeddings
3. Builds searchable index
4. Enables context-aware responses

#### Using RAG in CLI

```bash
versaai --project /your/project

> Explain how authentication works in this project
AI: [Searches codebase, finds auth files, explains with context]

> Where is the user validation logic?
AI: [Points to specific files and functions]
```

#### Using RAG in Editor

RAG is automatically enabled when VersaAI backend is running. The AI knows your project structure.

### Custom Prompts

Create custom prompt templates in `~/.versaai/prompts/`:

```yaml
# ~/.versaai/prompts/custom.yaml

refactor_for_performance:
  system: "You are an expert at code optimization."
  template: |
    Analyze this code and suggest performance improvements:
    
    ```{language}
    {code}
    ```
    
    Focus on: {focus_areas}
    Provide: Optimized code + explanation

generate_tests:
  system: "You are a testing expert."
  template: |
    Generate comprehensive unit tests for:
    
    ```{language}
    {code}
    ```
    
    Framework: {test_framework}
    Coverage: Aim for 90%+
```

**Usage:**

```bash
versaai --prompt refactor_for_performance
```

### Batch Processing

Process multiple files:

```bash
# Analyze all Python files in directory
versaai batch analyze --pattern "*.py" --output report.md

# Generate docstrings for all functions
versaai batch document --pattern "*.py" --style google

# Refactor code across project
versaai batch refactor --pattern "src/**/*.js" --focus "async/await"
```

---

## 🐛 Troubleshooting

### Common Issues

#### ❌ "Failed to connect to VersaAI backend"

**Solution:**
```bash
# 1. Check if backend is running
ps aux | grep "code_editor_bridge"

# 2. Start backend
cd /path/to/VersaAI
python -m versaai.code_editor_bridge.server

# 3. Check port 9001 is not in use
lsof -i :9001
```

#### ❌ "Model not found"

**Solution:**
```bash
# 1. List available models
ls ~/.versaai/models/

# 2. Download model
versaai  # Select "Download new model"

# 3. Or use manual download (see Model Setup section)
```

#### ❌ "Out of memory"

**Solution:**
1. Use smaller model (deepseek-1.3b instead of 6.7b)
2. Reduce context window in settings
3. Close other applications
4. Increase swap space

```bash
# Check memory
free -h

# Use smaller model
versaai --model deepseek-1.3b
```

#### ❌ "Slow completions"

**Solution:**
1. Use faster model (deepseek-1.3b)
2. Enable GPU acceleration (if available)
3. Reduce `max_tokens` in settings
4. Disable RAG if not needed

```bash
# Use fast model
versaai --model deepseek-1.3b --max-tokens 512
```

#### ❌ "API rate limit exceeded"

**Solution:**
1. Use local models instead
2. Implement request throttling
3. Upgrade API tier

```yaml
# In models.yaml, set local models as primary
routing:
  fallback_chain:
    - "deepseek-6.7b"  # Try local first
    - "gpt-4"          # API as last resort
```

### Debug Mode

Enable detailed logging:

```bash
# CLI
versaai --debug

# Environment variable
export VERSAAI_LOG_LEVEL=DEBUG
versaai

# Check logs
tail -f ~/.versaai/logs/versaai.log
```

### Reset Configuration

```bash
# Backup current config
cp -r ~/.versaai/config ~/.versaai/config.backup

# Reset to defaults
rm -rf ~/.versaai/config
versaai --setup
```

---

## 📚 FAQ

### General Questions

**Q: Is VersaAI free?**  
A: Yes! Local models are completely free. Cloud APIs (GPT-4, Claude) require paid accounts but are optional.

**Q: Can I use VersaAI offline?**  
A: Yes! Local models work completely offline. Only API models require internet.

**Q: Does VersaAI send my code to servers?**  
A: Only if you use cloud APIs (GPT-4, Claude). Local models keep everything on your machine.

**Q: What languages does VersaAI support?**  
A: All major languages: Python, JavaScript, TypeScript, Java, C++, C#, Go, Rust, PHP, Ruby, and more.

**Q: Can I use my own models?**  
A: Yes! Any GGUF-format model works. Add path in `models.yaml`.

### Performance Questions

**Q: Which model is fastest?**  
A: `deepseek-coder-1.3b` is the fastest (2-5s response time).

**Q: Which model is most accurate?**  
A: `GPT-4` for cloud, `deepseek-6.7b` or `qwen2.5-coder-7b` for local.

**Q: How much RAM do I need?**  
A: 
- 1.3B models: 2-4GB RAM
- 7B models: 8-12GB RAM
- 13B+ models: 16GB+ RAM

**Q: Does it support GPU acceleration?**  
A: Yes! llama.cpp automatically uses GPU if available (CUDA/Metal/OpenCL).

### Integration Questions

**Q: Can I integrate VersaAI into my own editor?**  
A: Yes! Use the WebSocket API (`code_editor_bridge.server`) or Python API.

**Q: Does it work with VS Code?**  
A: Not directly yet, but you can use the Python API to create an extension.

**Q: Can I use it in CI/CD pipelines?**  
A: Yes! Use batch mode or Python API for automated code analysis/generation.

---

## 📖 Additional Resources

### Documentation Files

| Document | Purpose |
|----------|---------|
| `README.md` | Project overview |
| `INSTALL.md` | Detailed installation guide |
| `docs/USER_GUIDE.md` | In-depth user manual |
| `docs/TUTORIALS.md` | Step-by-step tutorials |
| `docs/CODE_EDITOR_INTEGRATION.md` | Editor integration details |
| `docs/MULTI_MODEL_GUIDE.md` | Multi-model setup |
| `docs/QUICK_REFERENCE.md` | Command cheat sheet |
| `docs/API_REFERENCE.md` | Python API documentation |

### Quick Reference Commands

```bash
# Installation
pip install -e .

# Launch CLI Assistant
versaai

# Download models
versaai  # Interactive downloader

# Start editor backend
python -m versaai.code_editor_bridge.server

# Index project for RAG
versaai --index-project

# Multi-model mode
versaai --multi-model

# Batch processing
versaai batch analyze --pattern "*.py"

# Debug mode
versaai --debug

# Show version
versaai --version

# Help
versaai --help
```

### Environment Setup Examples

#### Minimal Setup (Free, Local Only)
```bash
# 1. Install VersaAI
pip install -e .

# 2. Download small model
versaai  # Select deepseek-1.3b

# 3. Use
versaai
```

#### Full Setup (Multi-Model, Editor Integration)
```bash
# 1. Install VersaAI
pip install -e ".[all]"

# 2. Download multiple models
cd ~/.versaai/models
wget <model-urls>  # See Model Setup section

# 3. Configure multi-model
cat > ~/.versaai/config/models.yaml <<EOF
# See Multi-Model Configuration section
EOF

# 4. Add API keys (optional)
export OPENAI_API_KEY="..."
export ANTHROPIC_API_KEY="..."

# 5. Start backend for editor
python -m versaai.code_editor_bridge.server &

# 6. Use CLI or editor
versaai --multi-model
```

---

## 🤝 Support & Contributing

### Get Help

- **Documentation Issues**: Open issue on GitHub
- **Bug Reports**: Include logs from `~/.versaai/logs/`
- **Feature Requests**: Describe use case and benefits

### Contributing

Contributions welcome! See `CONTRIBUTING.md` for guidelines.

---

## 📄 License

VersaAI is licensed under the MIT License. See `LICENSE` for details.

---

**Version:** 1.0.0  
**Last Updated:** 2025-11-19  
**Maintained by:** The No-hands Company

**Enjoy AI-powered coding!** 🚀
