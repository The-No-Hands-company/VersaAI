# 📘 VersaAI User Guide

**Complete Guide to Using VersaAI - Production-Grade AI Assistant**

**Version:** 1.0  
**Date:** 2025-11-19  
**Status:** ✅ Ready for Production

---

## 📑 Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Getting Started](#getting-started)
4. [Core Features](#core-features)
5. [Code Assistant](#code-assistant)
6. [Model Management](#model-management)
7. [Configuration](#configuration)
8. [Advanced Usage](#advanced-usage)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)
11. [FAQ](#faq)

---

## 🎯 Introduction

### What is VersaAI?

VersaAI is a production-grade, modular AI ecosystem that provides:

- **Code Assistant**: AI-powered coding help with local or cloud models
- **RAG System**: Retrieval-Augmented Generation for knowledge-based tasks
- **Multi-Model Support**: Use multiple AI models simultaneously
- **Hybrid Architecture**: High-performance C++ core with Python flexibility
- **Privacy-First**: Run completely offline with local models

### Who is VersaAI For?

- **Developers**: Get coding assistance without sharing code with cloud providers
- **Teams**: Deploy private AI infrastructure for your organization
- **Researchers**: Experiment with different models and configurations
- **Power Users**: Maximize productivity with AI-powered workflows

### Key Features

✅ **Local & Cloud Models**: Choose between privacy (local) or power (cloud)  
✅ **Multi-Model Router**: Automatically select the best model for each task  
✅ **Conversation Memory**: Context-aware conversations with history  
✅ **RAG Pipeline**: Search and answer questions from your documents  
✅ **Production-Ready**: Enterprise-grade architecture and error handling  

---

## 🚀 Installation

### System Requirements

**Minimum Requirements:**
- **OS**: Linux (Ubuntu 20.04+), macOS (11+), Windows 10+
- **RAM**: 4GB (8GB recommended for local models)
- **Storage**: 5GB for VersaAI + 1-10GB per model
- **Python**: 3.9 or higher
- **C++ Compiler**: GCC 9+, Clang 10+, or MSVC 2019+

**Recommended for Local Models:**
- **RAM**: 16GB+
- **GPU**: NVIDIA GPU with CUDA support (optional, for faster inference)
- **Storage**: SSD for better model loading times

### Quick Installation

**Option 1: Automated Install (Recommended)**

```bash
# Clone the repository
git clone https://github.com/yourusername/VersaAI.git
cd VersaAI

# Run installation script
./scripts/install.sh

# Verify installation
python verify_setup.py
```

**Option 2: Manual Installation**

```bash
# 1. Install Python dependencies
pip install -r requirements.txt

# 2. Build C++ core (optional, for performance)
./scripts/build.sh --auto

# 3. Install VersaAI package
pip install -e .

# 4. Verify installation
python verify_setup.py
```

**Option 3: Docker (Isolated Environment)**

```bash
# Pull pre-built image
docker pull versaai/versaai:latest

# Or build from source
docker build -t versaai .

# Run container
docker run -it --rm -v $(pwd):/workspace versaai
```

### Post-Installation Setup

```bash
# Create configuration directory
mkdir -p ~/.versaai/models ~/.versaai/config

# Set up environment variables (optional)
export VERSAAI_HOME="$HOME/.versaai"
export VERSAAI_LOG_LEVEL="INFO"

# Download your first model (optional)
python scripts/download_code_models.py --model deepseek-coder-1.3b
```

---

## 🏁 Getting Started

### Your First Session

**1. Launch VersaAI Code Assistant:**

```bash
# Launch interactive assistant
./scripts/launch_code_assistant.sh
```

**2. Select a Model:**

```
Select Model Type:
  1. Local Model (GGUF via llama.cpp) - Free, Private
  2. OpenAI API (GPT-4, GPT-3.5) - Paid, Powerful
  3. Anthropic API (Claude) - Paid, Powerful
  4. Placeholder Mode (No LLM) - Testing Only

Choice [1-4]: 1
```

**3. Start Coding:**

```
VersaAI Code Assistant v1.0 [deepseek-coder-1.3b-instruct]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You> write a function to calculate fibonacci numbers

Assistant> Here's an efficient Fibonacci function:

def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

# Example usage
print(fibonacci(10))  # Output: 55

This implementation uses O(n) time and O(1) space.
```

### Basic Workflows

**Code Generation:**
```
You> create a REST API endpoint in Python using Flask
```

**Code Explanation:**
```
You> explain what this code does: [paste your code]
```

**Bug Fixing:**
```
You> I'm getting this error: [paste error]. Here's my code: [paste code]
```

**Code Review:**
```
You> review this code for improvements: [paste code]
```

---

## 🎨 Core Features

### 1. Code Assistant

Your AI-powered coding companion.

**Launch:**
```bash
# Quick launch with default settings
./scripts/launch_code_assistant.sh

# Launch with specific model
python -m versaai.cli --provider llama-cpp \
  --model ~/.versaai/models/deepseek-coder-6.7b.gguf

# Launch with GPU acceleration
python -m versaai.cli --provider llama-cpp \
  --model ~/.versaai/models/model.gguf \
  --n-gpu-layers -1
```

**Features:**
- Code generation in 50+ languages
- Code explanation and documentation
- Bug detection and fixing
- Code review and optimization
- Test generation
- Refactoring suggestions

**Example Session:**
```python
# Generate a class
You> create a Python class for a bank account with deposit and withdraw methods

# Explain code
You> what does this regex do: ^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$

# Fix a bug
You> why is this crashing: def divide(a, b): return a / b

# Optimize code
You> make this faster: [paste nested loops code]
```

### 2. Multi-Model Router

Automatically route queries to the best model.

**Configuration:**
```python
# ~/.versaai/config/model_router.json
{
  "models": [
    {
      "name": "deepseek-coder-6.7b",
      "provider": "llama-cpp",
      "path": "~/.versaai/models/deepseek-coder-6.7b.gguf",
      "specialization": "code",
      "cost": 0
    },
    {
      "name": "gpt-4-turbo",
      "provider": "openai",
      "specialization": "general",
      "cost": 10
    }
  ],
  "routing_rules": {
    "code_generation": "deepseek-coder-6.7b",
    "complex_reasoning": "gpt-4-turbo",
    "default": "deepseek-coder-6.7b"
  }
}
```

**Usage:**
```python
from versaai.models import ModelRouter

router = ModelRouter("~/.versaai/config/model_router.json")

# Automatic routing based on query
response = router.query("write a binary search function")  # → DeepSeek
response = router.query("explain quantum entanglement")    # → GPT-4

# Manual model selection
response = router.query("generate code", model="deepseek-coder-6.7b")
```

### 3. RAG Pipeline

Search and answer questions from your documents.

**Setup:**
```python
from versaai.rag import RAGPipeline

# Initialize RAG
rag = RAGPipeline(
    vector_db_path="~/.versaai/vectordb",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)

# Index documents
rag.index_documents([
    "docs/api_reference.md",
    "docs/architecture.md",
    "docs/",  # Index entire directory
])
```

**Query:**
```python
# Ask questions
answer = rag.query("How do I configure the model router?")
print(answer)

# Get source citations
answer_with_sources = rag.query(
    "What are the system requirements?",
    return_sources=True
)
print(f"Answer: {answer_with_sources['answer']}")
print(f"Sources: {answer_with_sources['sources']}")
```

### 4. Conversation Memory

Maintain context across conversations.

**Usage:**
```python
from versaai.memory import ConversationManager

# Create conversation
conv_mgr = ConversationManager()
conv_id = conv_mgr.create_conversation("Code Review Session")

# Add messages
conv_mgr.add_message(conv_id, "user", "Review this function: def add(a, b): return a + b")
conv_mgr.add_message(conv_id, "assistant", "The function looks good but lacks type hints...")

# Retrieve history
history = conv_mgr.get_conversation_history(conv_id)

# Resume later
conv_mgr.resume_conversation(conv_id)
```

---

## 💻 Code Assistant

### Supported Languages

| Language | Code Gen | Explain | Debug | Test Gen | Refactor |
|----------|----------|---------|-------|----------|----------|
| Python | ✅ | ✅ | ✅ | ✅ | ✅ |
| JavaScript/TypeScript | ✅ | ✅ | ✅ | ✅ | ✅ |
| Java | ✅ | ✅ | ✅ | ✅ | ✅ |
| C/C++ | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Rust | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Go | ✅ | ✅ | ✅ | ✅ | ✅ |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ |
| PHP | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Ruby | ✅ | ✅ | ✅ | ⚠️ | ✅ |
| Swift | ✅ | ✅ | ✅ | ⚠️ | ✅ |

✅ Full support | ⚠️ Partial support

### Common Use Cases

**1. Generate Functions:**
```
You> write a function to validate email addresses in Python

Assistant> Here's a robust email validator:

import re

def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None
```

**2. Explain Complex Code:**
```
You> explain: async def fetch(session, url): async with session.get(url) as resp: return await resp.json()

Assistant> This is an asynchronous function that:
1. Takes an aiohttp session and URL
2. Makes a GET request asynchronously
3. Waits for the response and parses JSON
4. Returns the parsed JSON data
The 'async with' ensures proper resource cleanup.
```

**3. Debug Errors:**
```
You> I'm getting "list index out of range" with: data = [1, 2, 3]; print(data[5])

Assistant> The error occurs because you're trying to access index 5,
but the list only has 3 elements (indices 0-2).

Fix:
# Check index before accessing
if 5 < len(data):
    print(data[5])
else:
    print("Index out of range")

Or use .get() with default for dicts, or try/except for lists.
```

**4. Generate Tests:**
```
You> generate pytest tests for: def add(a, b): return a + b

Assistant> Here are comprehensive tests:

import pytest
from mymodule import add

def test_add_positive_numbers():
    assert add(2, 3) == 5
    assert add(10, 20) == 30

def test_add_negative_numbers():
    assert add(-5, -3) == -8
    assert add(-10, 5) == -5

def test_add_zero():
    assert add(0, 0) == 0
    assert add(5, 0) == 5

def test_add_floats():
    assert add(1.5, 2.5) == 4.0
    assert add(0.1, 0.2) == pytest.approx(0.3)
```

**5. Refactor Code:**
```
You> refactor this to be more pythonic: 
result = []
for i in range(len(items)):
    if items[i] % 2 == 0:
        result.append(items[i] * 2)

Assistant> Here's a more Pythonic version:

# Using list comprehension
result = [item * 2 for item in items if item % 2 == 0]

# Or using filter and map (functional approach)
result = list(map(lambda x: x * 2, filter(lambda x: x % 2 == 0, items)))

The first version is preferred for readability.
```

### CLI Commands

```bash
# Basic usage
python -m versaai.cli

# Specify provider
python -m versaai.cli --provider openai --model gpt-4-turbo

# GPU acceleration
python -m versaai.cli --provider llama-cpp --n-gpu-layers -1

# Custom temperature
python -m versaai.cli --temperature 0.7

# Save conversation
python -m versaai.cli --save-conversation my_session.json

# Load conversation
python -m versaai.cli --load-conversation my_session.json

# Verbose logging
python -m versaai.cli --verbose

# Help
python -m versaai.cli --help
```

---

## 📦 Model Management

### Local Models

**Advantages:**
- ✅ Completely private - no data leaves your machine
- ✅ No internet required
- ✅ No usage costs
- ✅ No rate limits

**Disadvantages:**
- ⚠️ Requires disk space (1-10GB per model)
- ⚠️ Requires RAM (4-16GB)
- ⚠️ Slower than cloud APIs (unless using GPU)

**Download Models:**

```bash
# List available models
python scripts/download_code_models.py --list

# Download specific model
python scripts/download_code_models.py --model deepseek-coder-6.7b

# Download and install dependencies
python scripts/download_code_models.py --model starcoder2-7b --install-deps

# Download multiple models
python scripts/download_code_models.py \
  --model deepseek-coder-1.3b \
  --model deepseek-coder-6.7b \
  --model starcoder2-7b
```

**Recommended Local Models:**

| Model | Size | RAM | Quality | Best For |
|-------|------|-----|---------|----------|
| deepseek-coder-1.3b | 0.9GB | 2GB | ⭐⭐⭐ | Quick tasks, low resources |
| **deepseek-coder-6.7b** ⭐ | 4.1GB | 8GB | ⭐⭐⭐⭐⭐ | Best all-around choice |
| starcoder2-7b | 5.0GB | 8GB | ⭐⭐⭐⭐⭐ | Code completion |
| codellama-13b | 8.0GB | 16GB | ⭐⭐⭐⭐⭐⭐ | Advanced tasks |
| wizardcoder-15b | 9.5GB | 16GB | ⭐⭐⭐⭐⭐⭐ | Best quality local |

### Cloud APIs

**Advantages:**
- ✅ Most powerful models (GPT-4, Claude 3)
- ✅ No local resources needed
- ✅ Always up-to-date
- ✅ Fast responses

**Disadvantages:**
- ⚠️ Requires internet connection
- ⚠️ Costs money per use
- ⚠️ Your code is sent to the provider
- ⚠️ Rate limits apply

**Setup OpenAI:**

```bash
# Set API key
export OPENAI_API_KEY="sk-your-key-here"

# Or save to config
echo "OPENAI_API_KEY=sk-your-key-here" >> ~/.versaai/config/api_keys.env

# Use in CLI
python -m versaai.cli --provider openai --model gpt-4-turbo
```

**Setup Anthropic (Claude):**

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-your-key-here"

# Use in CLI
python -m versaai.cli --provider anthropic --model claude-3-sonnet-20240229
```

**Available Cloud Models:**

| Provider | Model | Quality | Cost/1K tokens | Best For |
|----------|-------|---------|----------------|----------|
| OpenAI | gpt-4-turbo | ⭐⭐⭐⭐⭐⭐ | $0.01 | Complex reasoning |
| OpenAI | gpt-3.5-turbo | ⭐⭐⭐⭐ | $0.0005 | General coding |
| Anthropic | claude-3-opus | ⭐⭐⭐⭐⭐⭐ | $0.015 | Advanced tasks |
| Anthropic | claude-3-sonnet | ⭐⭐⭐⭐⭐ | $0.003 | Balanced |
| Anthropic | claude-3-haiku | ⭐⭐⭐⭐ | $0.0004 | Fast responses |

### Model Comparison

**When to use Local:**
- Working on proprietary/sensitive code
- No internet connection
- High-frequency usage (cost-effective)
- Learning/experimenting

**When to use Cloud:**
- Need best possible quality
- Complex reasoning tasks
- Occasional use (cost not a factor)
- Don't want to manage models

### GPU Acceleration

**Check GPU Support:**
```bash
# NVIDIA GPU
nvidia-smi

# Check CUDA
nvcc --version
```

**Install CUDA Support:**
```bash
# Install llama-cpp-python with CUDA
pip uninstall llama-cpp-python
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

# Verify
python -c "from llama_cpp import Llama; print('GPU support enabled!')"
```

**Use GPU:**
```bash
# Use all GPU layers
python -m versaai.cli --n-gpu-layers -1

# Use specific number of layers
python -m versaai.cli --n-gpu-layers 32

# Check GPU usage
nvidia-smi -l 1  # Update every second
```

---

## ⚙️ Configuration

### Configuration Files

VersaAI uses configuration files in `~/.versaai/config/`:

```
~/.versaai/
├── config/
│   ├── versaai.json          # Main configuration
│   ├── model_router.json     # Model routing rules
│   ├── api_keys.env          # API keys (gitignored)
│   └── logging.json          # Logging configuration
└── models/                    # Downloaded models
    ├── deepseek-coder-1.3b.gguf
    └── deepseek-coder-6.7b.gguf
```

### Main Configuration

**~/.versaai/config/versaai.json:**
```json
{
  "version": "1.0",
  "default_provider": "llama-cpp",
  "default_model": "~/.versaai/models/deepseek-coder-6.7b.gguf",
  "temperature": 0.7,
  "max_tokens": 2048,
  "conversation_history_limit": 10,
  "enable_rag": true,
  "rag_config": {
    "vector_db_path": "~/.versaai/vectordb",
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "chunk_size": 512,
    "chunk_overlap": 50
  },
  "memory_config": {
    "enable_short_term": true,
    "enable_long_term": true,
    "max_short_term_messages": 20,
    "context_window_size": 4096
  },
  "gpu_config": {
    "enable_gpu": true,
    "n_gpu_layers": -1,
    "main_gpu": 0
  },
  "logging": {
    "level": "INFO",
    "file": "~/.versaai/logs/versaai.log",
    "max_size_mb": 100,
    "backup_count": 5
  }
}
```

### Model Router Configuration

**~/.versaai/config/model_router.json:**
```json
{
  "models": [
    {
      "name": "deepseek-coder-small",
      "provider": "llama-cpp",
      "path": "~/.versaai/models/deepseek-coder-1.3b.gguf",
      "specialization": "code",
      "max_tokens": 2048,
      "cost_per_1k_tokens": 0,
      "priority": 1
    },
    {
      "name": "deepseek-coder-large",
      "provider": "llama-cpp",
      "path": "~/.versaai/models/deepseek-coder-6.7b.gguf",
      "specialization": "code",
      "max_tokens": 4096,
      "cost_per_1k_tokens": 0,
      "priority": 2
    },
    {
      "name": "gpt-4-turbo",
      "provider": "openai",
      "model_id": "gpt-4-turbo-preview",
      "specialization": "general",
      "max_tokens": 4096,
      "cost_per_1k_tokens": 10,
      "priority": 3
    }
  ],
  "routing_rules": {
    "simple_code": "deepseek-coder-small",
    "complex_code": "deepseek-coder-large",
    "explanation": "deepseek-coder-large",
    "debugging": "deepseek-coder-large",
    "reasoning": "gpt-4-turbo",
    "default": "deepseek-coder-large"
  },
  "auto_routing": {
    "enabled": true,
    "criteria": {
      "query_length": {
        "short": "deepseek-coder-small",
        "long": "deepseek-coder-large"
      },
      "complexity": {
        "low": "deepseek-coder-small",
        "high": "gpt-4-turbo"
      }
    }
  }
}
```

### Environment Variables

```bash
# VersaAI home directory
export VERSAAI_HOME="$HOME/.versaai"

# Log level (DEBUG, INFO, WARNING, ERROR)
export VERSAAI_LOG_LEVEL="INFO"

# API keys
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# GPU settings
export VERSAAI_GPU_LAYERS="-1"  # -1 = all layers

# Model cache directory
export VERSAAI_MODEL_CACHE="$HOME/.cache/versaai"
```

---

## 🔬 Advanced Usage

### Custom Model Integration

**Add a new model:**

```python
from versaai.models import ModelLoader

# Register custom model
loader = ModelLoader()
loader.register_model(
    name="my-custom-model",
    provider="llama-cpp",
    path="/path/to/model.gguf",
    config={
        "temperature": 0.8,
        "max_tokens": 4096,
        "n_gpu_layers": -1
    }
)

# Use custom model
response = loader.generate(
    model="my-custom-model",
    prompt="Write a hello world program"
)
```

### Fine-Tuning Workflows

**Prepare dataset:**
```python
from versaai.training import DatasetPreparation

# Prepare code dataset
prep = DatasetPreparation()
dataset = prep.prepare_code_dataset(
    source_files=[
        "src/**/*.py",
        "examples/**/*.py"
    ],
    output_path="training_data.jsonl",
    format="instruction"
)
```

**Fine-tune model:**
```bash
# Using provided training script
python scripts/finetune_model.py \
  --base-model deepseek-coder-6.7b \
  --dataset training_data.jsonl \
  --output fine-tuned-model \
  --epochs 3 \
  --batch-size 4 \
  --learning-rate 2e-5
```

### Plugin System

**Create a plugin:**

```python
# ~/.versaai/plugins/my_plugin.py
from versaai.plugins import PluginBase

class MyPlugin(PluginBase):
    name = "my_plugin"
    version = "1.0.0"
    
    def on_query(self, query: str) -> str:
        """Preprocess query before sending to model."""
        # Add custom preprocessing
        return query.upper()
    
    def on_response(self, response: str) -> str:
        """Postprocess response from model."""
        # Add custom postprocessing
        return f"[PLUGIN] {response}"

# Register plugin
def register():
    return MyPlugin()
```

**Use plugin:**
```bash
python -m versaai.cli --plugins my_plugin
```

### Batch Processing

**Process multiple files:**

```python
from versaai import VersaAI
import glob

ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")

# Process all Python files
for filepath in glob.glob("src/**/*.py", recursive=True):
    with open(filepath, 'r') as f:
        code = f.read()
    
    # Generate documentation
    docs = ai.generate(f"Generate docstrings for this code:\n{code}")
    
    # Save to output
    with open(f"{filepath}.docs.md", 'w') as f:
        f.write(docs)
```

### API Server

**Run as web service:**

```bash
# Start server
python -m versaai.server --host 0.0.0.0 --port 8000

# Use API
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "write a hello world function", "model": "deepseek-coder"}'
```

**API endpoints:**
- `POST /api/generate` - Generate code
- `POST /api/explain` - Explain code
- `POST /api/debug` - Debug code
- `GET /api/models` - List available models
- `GET /api/health` - Health check

---

## 🔧 Troubleshooting

### Common Issues

**Issue: "Model not found"**
```bash
# Solution 1: Check model path
ls -lh ~/.versaai/models/

# Solution 2: Download model
python scripts/download_code_models.py --model deepseek-coder-6.7b

# Solution 3: Use absolute path
python -m versaai.cli --model /absolute/path/to/model.gguf
```

**Issue: "Out of memory"**
```bash
# Solution 1: Use smaller model
python scripts/download_code_models.py --model deepseek-coder-1.3b

# Solution 2: Reduce GPU layers
python -m versaai.cli --n-gpu-layers 16

# Solution 3: Reduce context window
python -m versaai.cli --max-tokens 1024
```

**Issue: "Slow inference"**
```bash
# Solution 1: Enable GPU
python -m versaai.cli --n-gpu-layers -1

# Solution 2: Use quantized model (Q4_K_M instead of Q8_0)
python scripts/download_code_models.py --model deepseek-coder-6.7b --quantization Q4_K_M

# Solution 3: Reduce batch size
python -m versaai.cli --batch-size 128
```

**Issue: "API key not working"**
```bash
# Solution 1: Check key is set
echo $OPENAI_API_KEY

# Solution 2: Set key directly
export OPENAI_API_KEY="sk-your-actual-key"

# Solution 3: Save to config
echo "OPENAI_API_KEY=sk-your-key" >> ~/.versaai/config/api_keys.env
source ~/.versaai/config/api_keys.env
```

**Issue: "Import errors"**
```bash
# Solution 1: Reinstall package
pip uninstall versaai
pip install -e .

# Solution 2: Check Python version
python --version  # Should be 3.9+

# Solution 3: Install missing dependencies
pip install -r requirements.txt
```

### Debug Mode

**Enable verbose logging:**
```bash
# CLI
python -m versaai.cli --verbose

# Or set environment variable
export VERSAAI_LOG_LEVEL="DEBUG"
python -m versaai.cli
```

**Check logs:**
```bash
# View real-time logs
tail -f ~/.versaai/logs/versaai.log

# Search for errors
grep ERROR ~/.versaai/logs/versaai.log

# View specific time range
grep "2025-11-19 01:" ~/.versaai/logs/versaai.log
```

### Performance Profiling

**Profile inference time:**
```python
from versaai import VersaAI
import time

ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")

start = time.time()
response = ai.generate("write a hello world function")
end = time.time()

print(f"Inference time: {end - start:.2f}s")
print(f"Tokens per second: {len(response.split()) / (end - start):.2f}")
```

**Profile memory usage:**
```bash
# Install memory profiler
pip install memory_profiler

# Profile script
python -m memory_profiler your_script.py
```

### Getting Help

**1. Check documentation:**
- User Guide (this document)
- [FAQ](#faq)
- API Reference: `docs/API_REFERENCE.md`
- Architecture: `docs/Architecture.md`

**2. Enable debug logging:**
```bash
export VERSAAI_LOG_LEVEL="DEBUG"
python -m versaai.cli --verbose 2>&1 | tee debug.log
```

**3. Run diagnostics:**
```bash
python verify_setup.py --verbose
```

**4. Report issue:**
```bash
# Create bug report with diagnostics
python scripts/generate_bug_report.py > bug_report.txt
```

---

## 🎯 Best Practices

### Model Selection

**Choose based on your needs:**

- **Quick tasks** (snippets, simple functions): `deepseek-coder-1.3b`
- **General coding** (most use cases): `deepseek-coder-6.7b` ⭐
- **Complex reasoning**: `gpt-4-turbo` (cloud API)
- **Sensitive code**: Any local model (privacy)
- **High volume**: Local models (cost-effective)

### Prompt Engineering

**Good prompts:**
```
✅ "Write a Python function to validate email addresses using regex"
✅ "Explain what this code does: [code]"
✅ "Fix this bug: [error message] in [code]"
✅ "Optimize this function for better time complexity: [code]"
```

**Bad prompts:**
```
❌ "code"  (too vague)
❌ "help"  (not specific)
❌ "make it better"  (unclear what to improve)
```

**Prompt tips:**
1. Be specific about language and requirements
2. Provide context (error messages, desired output)
3. Include relevant code when asking for fixes/reviews
4. Specify constraints (e.g., "without using libraries")

### Resource Management

**Optimize for your hardware:**

```python
# Low RAM (4-8GB)
config = {
    "model": "deepseek-coder-1.3b",
    "n_gpu_layers": 0,  # CPU only
    "max_tokens": 1024,
    "batch_size": 64
}

# Medium RAM (8-16GB)
config = {
    "model": "deepseek-coder-6.7b",
    "n_gpu_layers": 16,  # Partial GPU
    "max_tokens": 2048,
    "batch_size": 128
}

# High RAM (16GB+) with GPU
config = {
    "model": "starcoder2-7b",
    "n_gpu_layers": -1,  # Full GPU
    "max_tokens": 4096,
    "batch_size": 512
}
```

### Privacy & Security

**Best practices:**

1. **Use local models for sensitive code**
   ```bash
   # Never send proprietary code to cloud APIs
   python -m versaai.cli --provider llama-cpp --model local-model.gguf
   ```

2. **Sanitize outputs**
   ```python
   # Remove sensitive information from logs
   response = ai.generate(prompt)
   # Redact before logging
   safe_response = redact_sensitive_info(response)
   ```

3. **Secure API keys**
   ```bash
   # Use environment variables, not hardcoded keys
   export OPENAI_API_KEY="sk-..."
   
   # Or secure config file with restricted permissions
   chmod 600 ~/.versaai/config/api_keys.env
   ```

4. **Review generated code**
   ```python
   # Always review AI-generated code before use
   # Check for:
   # - Security vulnerabilities
   # - Logic errors
   # - Performance issues
   ```

### Conversation Management

**Effective context management:**

```python
from versaai.memory import ConversationManager

conv_mgr = ConversationManager()

# Create session for related queries
session_id = conv_mgr.create_conversation("Refactoring Project X")

# Keep conversations focused
# ✅ Good: One conversation per topic
# ❌ Bad: Mix multiple unrelated topics

# Clear context when changing topics
conv_mgr.clear_conversation(session_id)

# Save important conversations
conv_mgr.export_conversation(session_id, "important_session.json")
```

---

## ❓ FAQ

### General

**Q: Is VersaAI free?**  
A: Yes! VersaAI is open-source. Local models are completely free. Cloud APIs (OpenAI, Anthropic) cost money per use.

**Q: Can I use VersaAI commercially?**  
A: Yes, VersaAI is licensed under MIT. However, check the licenses of specific models you use.

**Q: Does VersaAI require internet?**  
A: No, if using local models. Cloud APIs require internet.

**Q: Is my code sent to OpenAI/Anthropic?**  
A: Only if you use their cloud APIs. Local models keep everything on your machine.

### Models

**Q: Which model should I use?**  
A: For most users: `deepseek-coder-6.7b` (best balance of quality and performance).

**Q: Can I use multiple models?**  
A: Yes! Use the Model Router to automatically select the best model for each task.

**Q: How much disk space do I need?**  
A: 
- VersaAI: ~1GB
- Small model (1.3B): ~1GB
- Medium model (6.7B): ~4GB
- Large model (15B+): ~10GB+

**Q: How much RAM do I need?**  
A:
- Minimum: 4GB (for 1.3B model)
- Recommended: 8GB (for 6.7B model)
- Optimal: 16GB+ (for 13B+ models)

**Q: Do I need a GPU?**  
A: No, but it speeds up inference significantly (5-10x faster).

### Usage

**Q: Can VersaAI write entire applications?**  
A: It can help with components, but you should review and integrate. AI is best for assistance, not full automation.

**Q: How accurate is the generated code?**  
A: Generally high quality, but always review:
- Small tasks (functions): 90%+ accuracy
- Medium tasks (classes): 70-80% accuracy
- Large tasks (modules): 50-70% accuracy

**Q: Can I fine-tune models?**  
A: Yes! See [Advanced Usage](#advanced-usage) section.

**Q: How do I report bugs?**  
A: Use `python scripts/generate_bug_report.py` and open a GitHub issue.

### Performance

**Q: Why is inference slow?**  
A:
1. Enable GPU: `--n-gpu-layers -1`
2. Use smaller model: `deepseek-coder-1.3b`
3. Reduce max tokens: `--max-tokens 1024`

**Q: How can I speed up VersaAI?**  
A:
1. Use GPU acceleration
2. Use quantized models (Q4_K_M)
3. Increase batch size
4. Use SSD for model storage

**Q: What's the difference between quantizations?**  
A:
- Q4_K_M: Smallest, fastest, good quality
- Q5_K_M: Balanced
- Q8_0: Larger, slower, best quality

### Troubleshooting

**Q: Model download failed. What do I do?**  
A: 
1. Check internet connection
2. Try manual download from Hugging Face
3. Use `--resume` flag to continue

**Q: I get "CUDA out of memory" errors.**  
A:
1. Reduce GPU layers: `--n-gpu-layers 16`
2. Use smaller model
3. Reduce batch size

**Q: API key doesn't work.**  
A:
1. Check key is valid
2. Verify correct environment variable
3. Check API quota/billing

---

## 📚 Additional Resources

### Documentation

- **Quick Start**: `QUICKSTART.md`
- **Code Model Guide**: `QUICKSTART_CODE_MODEL.md`
- **Model Router**: `QUICKSTART_MODEL_ROUTER.md`
- **API Reference**: `docs/API_REFERENCE.md`
- **Architecture**: `docs/Architecture.md`
- **Development**: `docs/Development_Roadmap.md`

### Examples

```
examples/
├── basic_usage.py          # Simple code generation
├── rag_example.py          # RAG pipeline usage
├── multi_model.py          # Model routing
├── batch_processing.py     # Process multiple files
├── api_server.py           # Web API server
└── plugin_example.py       # Custom plugin
```

### Community

- **GitHub**: https://github.com/yourusername/VersaAI
- **Discussions**: https://github.com/yourusername/VersaAI/discussions
- **Issues**: https://github.com/yourusername/VersaAI/issues
- **Discord**: [Join our community](https://discord.gg/versaai)

### Contributing

We welcome contributions! See `CONTRIBUTING.md` for:
- Development setup
- Coding standards
- Pull request process
- Testing guidelines

---

## 📄 License

VersaAI is licensed under the MIT License. See `LICENSE` file for details.

**Note:** Individual models may have different licenses. Check model-specific licenses before commercial use.

---

## 🙏 Acknowledgments

VersaAI builds upon excellent work from:
- **DeepSeek**: DeepSeek-Coder models
- **BigCode**: StarCoder models
- **llama.cpp**: Local inference engine
- **OpenAI**: GPT models and API
- **Anthropic**: Claude models
- **Hugging Face**: Model hosting and transformers

---

**Made with ❤️ by The No-hands Company**

**Version 1.0** | **Last Updated: 2025-11-19**

---

## 📞 Support

Need help? We're here for you!

1. **Check FAQ** (this document)
2. **Read troubleshooting** section
3. **Run diagnostics**: `python verify_setup.py --verbose`
4. **Generate bug report**: `python scripts/generate_bug_report.py`
5. **Open GitHub issue** with bug report attached

**Happy coding with VersaAI!** 🚀
