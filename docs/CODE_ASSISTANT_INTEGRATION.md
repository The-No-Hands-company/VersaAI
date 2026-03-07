# VersaAI Code Assistant - Real LLM Integration

**Date:** November 18, 2025  
**Status:** ✅ Production-Ready

---

## 🎯 Overview

VersaAI Code Assistant now has **full real LLM integration** supporting:
- ✅ **Local models** via llama.cpp (GGUF format)
- ✅ **HuggingFace models** (transformers)
- ✅ **OpenAI API** (GPT-4, GPT-3.5)
- ✅ **Anthropic Claude API** (Claude 3)

All integrated with VersaAI's:
- ✅ Memory systems (short-term + long-term)
- ✅ RAG system (code search & retrieval)
- ✅ Reasoning engine (Chain-of-Thought)
- ✅ Planning system (task decomposition)

---

## 🚀 Quick Start

### Option 1: OpenAI API (Easiest, Best Quality)

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Start CLI with GPT-4
versaai --provider openai --llm-model gpt-4-turbo

# Or GPT-3.5 (faster, cheaper)
versaai --provider openai --llm-model gpt-3.5-turbo
```

**Cost:** ~$0.01-0.03 per request  
**Quality:** Excellent  
**Speed:** Fast (1-3 seconds)

### Option 2: Local Model (Free, Private)

```bash
# Download a model (one-time, ~4-8GB)
wget https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf -P ./models/

# Start CLI with local model
versaai --provider local --llm-model ./models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf

# With GPU acceleration (recommended)
versaai --provider local --llm-model ./models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf --gpu-layers -1
```

**Cost:** Free (after download)  
**Quality:** Very Good  
**Speed:** Medium (3-10 seconds, faster with GPU)

### Option 3: HuggingFace Model

```bash
# Small model (runs on 8GB RAM)
versaai --provider huggingface --llm-model bigcode/starcoder2-7b

# With quantization (uses less memory)
versaai --provider huggingface --llm-model bigcode/starcoder2-7b --load-in-8bit

# Or 4-bit (even less memory)
versaai --provider huggingface --llm-model bigcode/starcoder2-7b --load-in-4bit
```

**Cost:** Free  
**Quality:** Very Good to Excellent  
**Speed:** Medium (depends on hardware)

### Option 4: Anthropic Claude

```bash
# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Start CLI
versaai --provider anthropic --llm-model claude-3-sonnet-20240229

# Or Claude Opus (highest quality)
versaai --provider anthropic --llm-model claude-3-opus-20240229
```

**Cost:** ~$0.01-0.08 per request  
**Quality:** Excellent  
**Speed:** Fast (1-3 seconds)

---

## 📦 Installation

### Base Requirements
```bash
pip install versaai rich
```

### For Local Models (llama.cpp)
```bash
# CPU only
pip install llama-cpp-python

# With GPU (CUDA)
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python

# With GPU (Metal on Mac)
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
```

### For HuggingFace Models
```bash
pip install transformers torch accelerate

# For quantization support
pip install bitsandbytes
```

### For API Providers
```bash
# OpenAI
pip install openai

# Anthropic
pip install anthropic
```

---

## 💻 CLI Usage

### Interactive Mode

```bash
# Start the CLI
versaai --provider openai --llm-model gpt-4-turbo

# Now you can use commands:
VersaAI [python]> Create a function to calculate fibonacci

VersaAI [python]> /explain <paste code here>

VersaAI [python]> /review <paste code here>

VersaAI [python]> /debug <paste code with error>

VersaAI [python]> /test <paste code to test>

VersaAI [python]> /refactor <paste code to improve>
```

### Available Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/generate <task>` | Generate code | `/generate Create a REST API` |
| `/explain <code>` | Explain code | `/explain <paste code>` |
| `/review <code>` | Review code quality | `/review <paste code>` |
| `/debug <code>` | Debug errors | `/debug <paste buggy code>` |
| `/test <code>` | Generate tests | `/test <paste code>` |
| `/refactor <code>` | Refactor code | `/refactor <paste code>` |
| `/lang <language>` | Set language | `/lang javascript` |
| `/help` | Show help | `/help` |
| `/quit` | Exit | `/quit` |

### Natural Language

You can also just type naturally:

```
VersaAI [python]> Create a binary search function with type hints

VersaAI [python]> How do I implement a singleton pattern in Python?

VersaAI [javascript]> Generate a React component for a todo list
```

---

## 🔧 Programmatic Usage

### Example 1: Generate Code

```python
from versaai.models import CodeModel, CodeContext

# Initialize with LLM
model = CodeModel(
    llm_provider="openai",
    llm_model="gpt-4-turbo"
)

# Generate code
context = CodeContext(
    language="python",
    framework="FastAPI",
    requirements=["Add type hints", "Include error handling"]
)

result = model.generate_code(
    task="Create a REST API endpoint for user registration",
    context=context,
    use_reasoning=True  # Enable chain-of-thought
)

print(result["code"])
print(result["explanation"])
```

### Example 2: Multiple Providers

```python
from versaai.models.code_llm import create_code_llm, GenerationConfig

# Local model
local_llm = create_code_llm(
    provider="local",
    model_id="./models/deepseek-coder.gguf",
    n_gpu_layers=32
)

# HuggingFace model
hf_llm = create_code_llm(
    provider="huggingface",
    model_id="bigcode/starcoder2-7b",
    load_in_8bit=True
)

# OpenAI
openai_llm = create_code_llm(
    provider="openai",
    model_id="gpt-4-turbo"
)

# Use any of them
prompt = "def fibonacci(n):\n    # TODO: implement"
config = GenerationConfig(max_tokens=512, temperature=0.7)

code = local_llm.generate(prompt, config)
```

### Example 3: With RAG & Memory

```python
from versaai.models import CodeModel, CodeContext

# Full VersaAI integration
model = CodeModel(
    model_id="my-assistant",
    llm_provider="anthropic",
    llm_model="claude-3-sonnet-20240229",
    enable_memory=True,    # Conversation tracking
    enable_rag=True         # Code search & retrieval
)

# First task - stored in memory
result1 = model.generate_code(
    "Create a User model with SQLAlchemy",
    CodeContext(language="python", framework="SQLAlchemy")
)

# Second task - uses memory from first task
result2 = model.generate_code(
    "Now create an API endpoint to get all users",
    CodeContext(language="python", framework="FastAPI")
)
# ^ Knows about the User model from previous conversation

# RAG automatically retrieves relevant code examples
```

---

## 📊 Recommended Models

### For Code Generation

#### Best Overall Quality (API)
1. **GPT-4 Turbo** - Excellent at complex tasks
2. **Claude 3 Opus** - Great at following instructions
3. **Claude 3 Sonnet** - Good balance of quality/cost
4. **GPT-3.5 Turbo** - Fast and cheap for simple tasks

#### Best Local Models (Free)
1. **DeepSeek-Coder 33B** - Best quality (needs 24GB+ VRAM)
   ```bash
   wget https://huggingface.co/TheBloke/deepseek-coder-33B-instruct-GGUF/resolve/main/deepseek-coder-33b-instruct.Q4_K_M.gguf
   ```

2. **DeepSeek-Coder 6.7B** - Good quality (needs 8GB VRAM)
   ```bash
   wget https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf
   ```

3. **StarCoder2 15B** - Multi-language expert
   ```bash
   wget https://huggingface.co/TheBloke/starcoder2-15B-GGUF/resolve/main/starcoder2-15b.Q4_K_M.gguf
   ```

4. **CodeLlama 13B** - Meta's code model
   ```bash
   wget https://huggingface.co/TheBloke/CodeLlama-13B-Instruct-GGUF/resolve/main/codellama-13b-instruct.Q4_K_M.gguf
   ```

### For Explanation & Review
- **Claude 3** - Best at clear explanations
- **GPT-4** - Detailed and comprehensive
- **DeepSeek-Coder** - Good local option

### For Fast Prototyping
- **GPT-3.5 Turbo** - Fast API calls
- **Phi-2** (local) - Small and fast
- **StarCoder 1B** (local) - Very fast

---

## 🎛️ Advanced Configuration

### Custom Generation Settings

```python
from versaai.models.code_llm import GenerationConfig

config = GenerationConfig(
    max_tokens=2048,        # Max length
    temperature=0.7,        # Creativity (0.0-1.0)
    top_p=0.95,            # Nucleus sampling
    top_k=50,              # Top-k sampling
    stop_sequences=["```\n", "\n\n\n"]  # Stop generation
)

code = llm.generate(prompt, config)
```

### Memory & Context Management

```python
from versaai.models import CodeModel

model = CodeModel(
    llm_provider="openai",
    llm_model="gpt-4-turbo",
    max_context_tokens=8192,  # Context window size
    enable_memory=True,
    enable_rag=True
)

# Access conversation history
history = model.get_conversation_history()

# Clear memory
model.clear_conversation()

# Save/load state
model.save_state("./my_session.json")
model.load_state("./my_session.json")
```

### RAG Configuration

```python
from versaai.models import CodeModel

model = CodeModel(
    llm_provider="openai",
    llm_model="gpt-4-turbo",
    enable_rag=True,
    knowledge_base_path="./my_code_kb"  # Custom knowledge base
)

# Add code to knowledge base
model.add_to_knowledge_base(
    code="def hello(): return 'world'",
    language="python",
    description="Simple hello world function"
)
```

---

## 🔍 Troubleshooting

### Issue: "Model not found"
**Solution:** Check the model path or model ID is correct.

```bash
# Local: Verify file exists
ls -lh ./models/deepseek-coder.gguf

# HuggingFace: Try the full model ID
versaai --provider hf --llm-model bigcode/starcoder2-7b
```

### Issue: "Out of memory"
**Solution:** Use quantization or a smaller model.

```bash
# 8-bit quantization (halves memory)
versaai --provider hf --llm-model bigcode/starcoder2-7b --load-in-8bit

# 4-bit quantization (1/4 memory)
versaai --provider hf --llm-model bigcode/starcoder2-7b --load-in-4bit

# Or use a smaller GGUF model
versaai --provider local --llm-model ./models/starcoder-1b.Q4_K_M.gguf
```

### Issue: "Slow generation"
**Solution:** Use GPU acceleration or API.

```bash
# Enable GPU for local models
versaai --provider local --llm-model ./models/model.gguf --gpu-layers -1

# Or use API (much faster)
versaai --provider openai --llm-model gpt-3.5-turbo
```

### Issue: "API key errors"
**Solution:** Set environment variables.

```bash
# OpenAI
export OPENAI_API_KEY="sk-..."

# Anthropic
export ANTHROPIC_API_KEY="sk-ant-..."

# Verify
echo $OPENAI_API_KEY
```

---

## 📈 Performance Comparison

| Provider | Quality | Speed | Cost | Privacy |
|----------|---------|-------|------|---------|
| GPT-4 Turbo | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $$$ | ❌ |
| Claude 3 Opus | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | $$$$ | ❌ |
| Claude 3 Sonnet | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $$ | ❌ |
| GPT-3.5 Turbo | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | $ | ❌ |
| DeepSeek 33B | ⭐⭐⭐⭐ | ⭐⭐ | Free | ✅ |
| DeepSeek 6.7B | ⭐⭐⭐ | ⭐⭐⭐ | Free | ✅ |
| StarCoder2 15B | ⭐⭐⭐⭐ | ⭐⭐ | Free | ✅ |
| StarCoder2 7B | ⭐⭐⭐ | ⭐⭐⭐ | Free | ✅ |

---

## 🎯 Next Steps

### Week 3: Enhancement
- [ ] Add embeddings for better RAG
- [ ] Implement code execution sandbox
- [ ] Add multi-language syntax validation
- [ ] Create specialized agents (debug agent, refactor agent)

### Week 4: Advanced Features
- [ ] Fine-tune models on VersaAI codebase
- [ ] Add collaborative coding features
- [ ] Implement code diff visualization
- [ ] Create VS Code extension

---

## 📚 Resources

### Model Downloads
- **Hugging Face:** https://huggingface.co/models?pipeline_tag=text-generation&other=code
- **TheBloke GGUF:** https://huggingface.co/TheBloke
- **LM Studio:** https://lmstudio.ai/ (GUI for GGUF models)

### Documentation
- **llama.cpp:** https://github.com/ggerganov/llama.cpp
- **Transformers:** https://huggingface.co/docs/transformers
- **OpenAI API:** https://platform.openai.com/docs
- **Anthropic API:** https://docs.anthropic.com/

---

## ✅ Summary

VersaAI Code Assistant now has **production-grade LLM integration**:

✅ **4 providers supported** (local, HuggingFace, OpenAI, Anthropic)  
✅ **Easy CLI** with rich formatting  
✅ **Full programmatic API** for custom integrations  
✅ **Memory & RAG** for context-aware assistance  
✅ **Reasoning & Planning** for complex tasks  
✅ **Production-ready** with proper error handling

**Start coding with AI assistance today!** 🚀

```bash
# Quick start
pip install versaai openai
export OPENAI_API_KEY="sk-..."
versaai --provider openai --llm-model gpt-4-turbo
```
