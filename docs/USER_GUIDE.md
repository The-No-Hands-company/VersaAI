# VersaAI - Complete User Documentation

## 📚 Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Quick Start](#quick-start)
4. [Code Assistant CLI](#code-assistant-cli)
5. [Code Editor Integration](#code-editor-integration)
6. [Model Management](#model-management)
7. [Features & Capabilities](#features--capabilities)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Usage](#advanced-usage)

---

## Overview

**VersaAI** is a production-grade, hierarchical AI ecosystem providing intelligent assistance for coding, development, and system integration. It features:

- 🤖 **Multiple AI Models** - DeepSeek Coder, StarCoder2, CodeLlama, GPT-4, Claude
- 💬 **Intelligent Chat** - Context-aware conversations about code
- ⚡ **Code Completion** - Real-time AI-powered suggestions
- 🔍 **RAG System** - Retrieval-Augmented Generation for better context
- 🎯 **Model Router** - Automatic model selection for optimal results
- 🔧 **CLI Tools** - Command-line interface for quick assistance
- 🖥️ **Editor Integration** - Seamless integration with code editors

### Architecture

```
VersaAI Core
├── Model Router          # Intelligent model selection
├── RAG System           # Context retrieval & augmentation
├── Memory Manager       # Conversation & context tracking
└── Integration Layers
    ├── CLI Assistant    # Command-line interface
    ├── Editor Bridge    # Code editor integration
    └── API Interface    # Programmatic access
```

---

## Installation & Setup

### Prerequisites

- **Python 3.8+**
- **pip** package manager
- **Git** (for cloning repository)
- **8GB+ RAM** (for local models)

### Basic Installation

```bash
# Clone the repository
cd /path/to/your/projects
git clone <repository-url> VersaAI
cd VersaAI

# Install VersaAI
pip install -e .

# Install required dependencies
pip install -r requirements.txt
```

### Full Installation (with AI models)

```bash
# Install VersaAI
pip install -e .

# Install model support
pip install llama-cpp-python  # For local GGUF models
pip install openai            # For OpenAI API
pip install anthropic         # For Anthropic Claude

# Download models (optional)
python scripts/download_models.py
```

### Verification

```bash
# Verify installation
python verify_setup.py

# Test code model
python verify_code_model.py
```

---

## Quick Start

### 1. Launch Code Assistant

```bash
python versaai_cli.py
```

You'll see:
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

### 2. Download a Model (First Time)

```bash
# Option A: Quick download (1.3B model, ~800MB)
python versaai_cli.py
# Select option 1 (Local Model)
# Choose "Download new model"
# Select DeepSeek Coder 1.3B

# Option B: Download manually
mkdir -p ~/.versaai/models
cd ~/.versaai/models
wget https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf
```

### 3. Start Chatting

```
You: How do I read a file in Python?

VersaAI: Here's how to read a file in Python:

```python
# Method 1: Read entire file
with open('file.txt', 'r') as f:
    content = f.read()

# Method 2: Read line by line
with open('file.txt', 'r') as f:
    for line in f:
        print(line.strip())

# Method 3: Read all lines into list
with open('file.txt', 'r') as f:
    lines = f.readlines()
```

The `with` statement ensures the file is properly closed.
```

---

## Code Assistant CLI

### Interactive Mode

```bash
python versaai_cli.py
```

Features:
- Multi-line input (press Enter twice to send)
- Code syntax highlighting
- Conversation history
- Model switching
- Save conversations

### Commands

While in interactive mode:

- `/help` - Show available commands
- `/models` - List available models
- `/switch` - Switch to different model
- `/clear` - Clear conversation
- `/save` - Save conversation to file
- `/load` - Load previous conversation
- `/quit` or `/exit` - Exit assistant

### Example Session

```
VersaAI> How do I implement a binary search in Python?

[AI provides implementation]

VersaAI> Can you add comments to explain it?

[AI adds detailed comments]

VersaAI> /save binary_search.txt
✅ Conversation saved to binary_search.txt

VersaAI> /quit
```

---

## Code Editor Integration

### Supported Editors

- ✅ **NLPL Code Editor** (Full integration)
- ⏳ **VS Code** (Coming soon)
- ⏳ **Neovim** (Planned)
- ⏳ **JetBrains IDEs** (Planned)

### Setup for NLPL Code Editor

#### Quick Setup (5 minutes)

```bash
cd /path/to/code_editor

# Option 1: Use startup script
./start_with_versaai.sh

# Option 2: Manual start
# Terminal 1:
cd /path/to/VersaAI
python -m versaai.code_editor_bridge.server

# Terminal 2:
cd /path/to/code_editor
npm run dev
```

#### Features in Editor

1. **Real-time Code Completion**
   - Triggered automatically as you type
   - Context-aware suggestions
   - Multi-language support

2. **AI Chat Panel**
   - Click 🤖 icon in activity bar
   - Or press `Ctrl+Shift+A`
   - Ask questions about your code
   - Get refactoring suggestions

3. **Quick Actions** (in chat panel)
   - 💡 Explain selected code
   - 🐛 Find bugs
   - ✨ Suggest improvements
   - 📝 Add documentation
   - 🧪 Write tests

### Testing Without AI Models

```bash
# Use test server (mock responses)
cd /path/to/code_editor
python3 test_versaai_bridge.py

# In another terminal
npm run dev
```

This allows you to test the UI without downloading AI models.

---

## Model Management

### Supported Models

#### Local Models (Free, Private)

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| DeepSeek Coder 1.3B | 0.8GB | ⚡⚡⚡ | ⭐⭐ | Quick completions |
| DeepSeek Coder 6.7B | 4GB | ⚡⚡ | ⭐⭐⭐ | Balanced |
| StarCoder2 7B | 4.5GB | ⚡⚡ | ⭐⭐⭐ | Code generation |
| StarCoder2 15B | 9GB | ⚡ | ⭐⭐⭐⭐ | Complex tasks |
| CodeLlama 7B | 4GB | ⚡⚡ | ⭐⭐⭐ | General coding |
| CodeLlama 13B | 7GB | ⚡ | ⭐⭐⭐⭐ | Advanced coding |
| CodeLlama 34B | 19GB | ⚡ | ⭐⭐⭐⭐⭐ | Expert level |
| Qwen2.5-Coder 7B | 4GB | ⚡⚡ | ⭐⭐⭐ | Multi-language |
| Qwen2.5-Coder 14B | 8GB | ⚡ | ⭐⭐⭐⭐ | Production code |

#### API Models (Paid, Cloud)

| Model | Provider | Speed | Quality | Cost |
|-------|----------|-------|---------|------|
| GPT-4 Turbo | OpenAI | ⚡ | ⭐⭐⭐⭐⭐ | $10-100/month |
| GPT-3.5 Turbo | OpenAI | ⚡⚡⚡ | ⭐⭐⭐ | $5-20/month |
| Claude 3 Opus | Anthropic | ⚡ | ⭐⭐⭐⭐⭐ | $15-75/month |
| Claude 3 Sonnet | Anthropic | ⚡⚡ | ⭐⭐⭐⭐ | $10-50/month |

### Downloading Models

```bash
# Interactive download
python versaai_cli.py
# Select "Local Model" → "Download new model"

# Direct download
python scripts/download_models.py --model deepseek-coder-1.3b

# All recommended models
python scripts/download_models.py --recommended
```

### Model Storage

Models are stored in:
```
~/.versaai/models/
├── deepseek-coder-1.3b-instruct.Q4_K_M.gguf
├── deepseek-coder-6.7b-instruct.Q4_K_M.gguf
├── starcoder2-7b.Q4_K_M.gguf
└── ...
```

### Switching Models

#### In CLI

```
VersaAI> /switch
Available models:
1. DeepSeek Coder 1.3B (current)
2. DeepSeek Coder 6.7B
3. StarCoder2 7B
4. GPT-4 (API)

Select model: 2
✅ Switched to DeepSeek Coder 6.7B
```

#### In Code Editor

Models are automatically selected based on task:
- **Completions**: Fast model (1.3B)
- **Chat**: Balanced model (6.7B)
- **Complex**: Best model (34B or GPT-4)

---

## Features & Capabilities

### Code Completion

**What it does:**
- Suggests code as you type
- Understands context from surrounding code
- Works with all programming languages
- Learns from your coding patterns

**Example:**
```python
def calculate_fibonacci(n):
    # AI suggests:
    if n <= 1:
        return n
    else:
        return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)
```

### Code Explanation

**What it does:**
- Explains complex code in plain English
- Breaks down algorithms step-by-step
- Identifies patterns and best practices

**Example:**
```
You: [Select complex regex]
     Explain: r'^(?=.*[A-Z])(?=.*[0-9])(?=.*[@#$])(.{8,})$'

AI: This regex validates passwords with these requirements:
    - At least one uppercase letter (?=.*[A-Z])
    - At least one number (?=.*[0-9])
    - At least one special character (?=.*[@#$])
    - Minimum 8 characters (.{8,})
```

### Bug Detection

**What it does:**
- Identifies potential bugs
- Suggests fixes
- Explains why it's a problem

**Example:**
```python
# Your code:
def divide(a, b):
    return a / b

# AI warns:
⚠️  Potential ZeroDivisionError if b is 0
✅  Suggested fix:
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
```

### Refactoring Suggestions

**What it does:**
- Improves code structure
- Enhances readability
- Optimizes performance

**Example:**
```python
# Before:
if user.is_active == True:
    if user.role == "admin":
        allow_access()

# AI suggests:
if user.is_active and user.role == "admin":
    allow_access()
```

### Test Generation

**What it does:**
- Creates unit tests
- Covers edge cases
- Uses appropriate test framework

**Example:**
```python
def add(a, b):
    return a + b

# AI generates:
import unittest

class TestMathFunctions(unittest.TestCase):
    def test_add_positive_numbers(self):
        self.assertEqual(add(2, 3), 5)
    
    def test_add_negative_numbers(self):
        self.assertEqual(add(-1, -1), -2)
    
    def test_add_zero(self):
        self.assertEqual(add(5, 0), 5)
```

### Documentation Generation

**What it does:**
- Generates docstrings
- Creates README sections
- Explains API usage

**Example:**
```python
def binary_search(arr, target):
    # AI adds:
    """
    Perform binary search on a sorted array.
    
    Args:
        arr (list): Sorted list of comparable elements
        target: Element to search for
    
    Returns:
        int: Index of target if found, -1 otherwise
    
    Time Complexity: O(log n)
    Space Complexity: O(1)
    """
    left, right = 0, len(arr) - 1
    # ... implementation
```

---

## Configuration

### Environment Variables

```bash
# Model directory
export VERSAAI_MODELS_DIR=~/.versaai/models

# API keys
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Backend host/port
export VERSAAI_HOST=localhost
export VERSAAI_PORT=8765

# Log level
export VERSAAI_LOG_LEVEL=INFO
```

### Configuration File

Create `~/.versaai/config.yaml`:

```yaml
models:
  default_local: deepseek-coder-6.7b
  default_api: gpt-4-turbo
  
  preferences:
    code_completion: deepseek-coder-1.3b
    chat: deepseek-coder-6.7b
    complex_tasks: gpt-4-turbo

completion:
  cache_ttl: 300  # seconds
  min_prefix_length: 2
  max_suggestions: 3
  temperature: 0.2

chat:
  max_context_tokens: 4000
  temperature: 0.7
  max_history: 20

server:
  host: localhost
  port: 8765
  max_clients: 10
```

---

## Troubleshooting

### Common Issues

#### 1. "No models found"

**Problem:** CLI can't find downloaded models

**Solution:**
```bash
# Check model directory
ls ~/.versaai/models/

# Download a model
python scripts/download_models.py --model deepseek-coder-1.3b

# Or set custom directory
export VERSAAI_MODELS_DIR=/path/to/models
```

#### 2. "Connection refused" in editor

**Problem:** Editor can't connect to VersaAI backend

**Solution:**
```bash
# Start backend server
python -m versaai.code_editor_bridge.server

# Check if running
ps aux | grep versaai

# Check port availability
lsof -i :8765
```

#### 3. Slow completions

**Problem:** AI responses are too slow

**Solutions:**
- Use smaller model (1.3B instead of 6.7B)
- Enable GPU acceleration
- Increase cache TTL
- Use local models instead of API

```bash
# Install GPU support (CUDA)
pip install llama-cpp-python --force-reinstall --no-cache-dir \
  --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cu121
```

#### 4. Out of memory

**Problem:** System runs out of RAM

**Solutions:**
- Use smaller model
- Close other applications
- Use quantized models (Q4 instead of Q8)
- Enable swap space

```bash
# Check memory usage
free -h

# Use smaller quantization
# Q4_K_M instead of Q8_0
```

#### 5. Model download fails

**Problem:** Download interrupted or fails

**Solutions:**
```bash
# Resume download
python scripts/download_models.py --model deepseek-coder-1.3b --resume

# Direct download with wget
cd ~/.versaai/models
wget -c https://huggingface.co/.../model.gguf

# Use mirror if HuggingFace is slow
python scripts/download_models.py --mirror modelscope
```

---

## Advanced Usage

### Custom Model Integration

```python
from versaai.model_router import ModelRouter

# Add custom model
router = ModelRouter()
router.register_model(
    name="my-custom-model",
    path="/path/to/model.gguf",
    priority=5,
    capabilities=["code_completion", "chat"]
)
```

### Programmatic API

```python
from versaai import VersaAICore

# Initialize
ai = VersaAICore()

# Code completion
completion = ai.complete_code(
    prefix="def fibonacci(n):",
    suffix="",
    language="python"
)

# Chat
response = ai.chat(
    message="How do I sort a list in Python?",
    context={"file": "main.py", "language": "python"}
)

# Code analysis
bugs = ai.analyze_code(
    code="...",
    analysis_type="bug_detection"
)
```

### RAG System

```python
from versaai.rag import RAGSystem

# Initialize
rag = RAGSystem()

# Index codebase
rag.index_directory("/path/to/project")

# Query with context
response = rag.query(
    "How is authentication implemented?",
    max_results=5
)
```

### Custom Agents

```python
from versaai.agents import AgentBase

class CustomAgent(AgentBase):
    def process(self, input_data):
        # Custom processing logic
        return result

# Register agent
ai.register_agent("custom", CustomAgent())

# Use agent
result = ai.execute_agent("custom", data)
```

---

## Appendix

### Keyboard Shortcuts (Editor)

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+A` | Toggle AI chat panel |
| `Ctrl+Space` | Trigger completion |
| `Tab` | Accept completion |
| `Esc` | Dismiss completion |
| `Ctrl+K` | Inline AI command (future) |

### CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/models` | List models |
| `/switch` | Switch model |
| `/clear` | Clear chat |
| `/save` | Save conversation |
| `/load` | Load conversation |
| `/quit` | Exit |

### File Locations

```
~/.versaai/
├── models/              # Downloaded AI models
├── cache/               # Completion cache
├── conversations/       # Saved chats
├── config.yaml          # Configuration
└── logs/               # Log files

VersaAI/
├── versaai/            # Python package
│   ├── core/
│   ├── models/
│   ├── agents/
│   ├── rag/
│   └── code_editor_bridge/
├── docs/               # Documentation
├── examples/           # Example code
└── scripts/            # Utility scripts
```

### Resources

- **Documentation:** `docs/`
- **Examples:** `examples/`
- **GitHub Issues:** [Report bugs](https://github.com/...)
- **Discussions:** [Ask questions](https://github.com/.../discussions)

---

**Version:** 1.0.0  
**Last Updated:** 2025-01-19  
**Status:** Production Ready

For more detailed technical documentation, see:
- [Development Roadmap](docs/Development_Roadmap.md)
- [Architecture Guide](docs/Architecture.md)
- [Code Editor Integration](CODE_EDITOR_INTEGRATION.md)
- [Model Router](docs/MODEL_ROUTER.md)
