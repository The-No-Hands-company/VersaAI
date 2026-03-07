# VersaAI - Quick Reference Card

## 🚀 Quick Commands

### Start Services
```bash
# Code Assistant CLI
python versaai_cli.py

# Editor Bridge Server
python start_editor_bridge.py

# Test Bridge
python test_editor_bridge.py
```

### Download Models
```bash
# Single model
python -m versaai.cli.download_models --model deepseek-1.3b

# Recommended set
python -m versaai.cli.download_models --preset recommended

# All models
python -m versaai.cli.download_models --preset all
```

## 💬 CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/models` | List models |
| `/switch MODEL` | Change model |
| `/load FILE` | Load file context |
| `/clear` | Clear history |
| `/save FILE` | Save conversation |
| `/explain` | Explain code |
| `/refactor` | Refactor code |
| `/test` | Generate tests |
| `/debug` | Debug help |
| `/exit` | Quit |

## 🤖 Available Models

### Local Models (Free)
- **DeepSeek 1.3B** - Fast (834MB, 2-4GB RAM)
- **DeepSeek 6.7B** - Balanced (3.9GB, 8-12GB RAM)
- **StarCoder2 7B** - Quality (4.1GB, 8-16GB RAM)
- **CodeLlama 7/13/34B** - Best (4-19GB, 8-32GB+ RAM)
- **Qwen2.5 7/14B** - Multilingual (4-8GB, 8-24GB RAM)

### API Models (Paid)
- **GPT-4** - Best reasoning
- **GPT-3.5** - Fast & cheap
- **Claude 3** - Long context

## 🔌 WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8765');
```

### Message Types
```javascript
// Code completion
{type: 'completion', context: {...}}

// Chat
{type: 'chat', message: '...', session_id: '...'}

// Explain code
{type: 'explain', code: '...', language: '...'}

// Refactor
{type: 'refactor', code: '...', language: '...'}

// Debug
{type: 'debug', code: '...', error_message: '...'}

// Generate tests
{type: 'test', code: '...', language: '...'}

// Health check
{type: 'ping'}
```

## ⚙️ Configuration

### Config File
Location: `~/.versaai/config.yaml`

```yaml
models:
  default: deepseek-6.7b
  
preferences:
  temperature: 0.7
  max_tokens: 2048
  
editor_bridge:
  host: localhost
  port: 8765
```

### Environment Variables
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export VERSAAI_MODELS_DIR="~/.versaai/models"
```

## 📁 File Locations

| Type | Location |
|------|----------|
| Models | `~/.versaai/models/` |
| Config | `~/.versaai/config.yaml` |
| Logs | `~/.versaai/versaai.log` |
| RAG Index | `~/.versaai/rag_index/` |

## 🐛 Troubleshooting

### Server won't start
```bash
# Check port
lsof -i :8765

# Kill process
kill -9 <PID>

# Use different port
python start_editor_bridge.py --port 8766
```

### Out of memory
- Use smaller model (1.3B)
- Close other apps
- Reduce `max_tokens`

### Slow responses
- Use DeepSeek 1.3B
- Enable caching
- Use GPU if available

### No models found
```bash
# Download model
python -m versaai.cli.download_models --model deepseek-1.3b

# Verify
ls ~/.versaai/models/
```

## 📖 Documentation

| Document | Purpose |
|----------|---------|
| `docs/USER_GUIDE.md` | Complete user manual |
| `docs/CODE_EDITOR_INTEGRATION.md` | Integration guide |
| `EDITOR_INTEGRATION_README.md` | Quick start |
| `QUICKSTART.md` | 5-minute start |

## 🔗 Python API

```python
from versaai import VersaAI

# Initialize
ai = VersaAI(model='deepseek-6.7b')

# Chat
response = ai.chat("How do I use async in Python?")

# Generate code
code = ai.generate_code("Create a REST API with FastAPI")

# Explain code
explanation = ai.explain_code(code, language='python')

# Generate tests
tests = ai.generate_tests(code, language='python')

# Load file context
ai.load_file('main.py')
ai.chat("How can I optimize this?")
```

## 🎯 Common Tasks

### Generate Function
```
You: Create a function to validate email addresses

VersaAI: [Generates complete function with validation]
```

### Explain Code
```
You: /explain
[Paste code]

VersaAI: [Detailed explanation]
```

### Optimize Code
```
You: /load myfile.py
You: Optimize the process_data function

VersaAI: [Optimization suggestions]
```

### Generate Tests
```
You: /test
[Paste function]

VersaAI: [Complete unit tests]
```

### Debug Error
```
You: /debug
[Paste code and error]

VersaAI: [Root cause + fix]
```

## 🚀 Getting Started (3 Steps)

1. **Install VersaAI**
   ```bash
   cd VersaAI
   pip install -e .
   ```

2. **Download Model**
   ```bash
   python -m versaai.cli.download_models --model deepseek-1.3b
   ```

3. **Start Using**
   ```bash
   # CLI
   python versaai_cli.py
   
   # Or Editor Bridge
   python start_editor_bridge.py
   ```

## 💡 Pro Tips

- **Use `auto` mode** for intelligent model selection
- **Load files** for context-aware help: `/load file.py`
- **Cache responses** - ask similar questions for speed
- **Try different models** - use `/switch` to compare
- **Save conversations** - `/save` for future reference
- **Local models** for privacy, API for quality

## 📞 Support

- **Docs:** `docs/` directory
- **Examples:** `examples/` directory
- **Issues:** GitHub Issues
- **Logs:** `~/.versaai/versaai.log`

---

**🎓 Learn More**
- Complete Guide: `docs/USER_GUIDE.md`
- Integration: `docs/CODE_EDITOR_INTEGRATION.md`
- Quick Start: `QUICKSTART.md`

**🚀 Happy Coding with VersaAI!**
