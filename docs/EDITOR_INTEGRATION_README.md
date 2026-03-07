# VersaAI Code Editor Integration - Quick Start

**Transform your code editor into an AI-powered development environment**

---

## 🚀 What You Get

✅ **Real-time Code Completion** - GitHub Copilot-style AI suggestions  
✅ **AI Chat Panel** - Ask questions about your code  
✅ **Code Actions** - Explain, refactor, debug, test generation  
✅ **Context-Aware** - Understands your project and files  
✅ **Multi-Model** - Automatically uses the best model for each task  
✅ **Privacy-First** - Local models keep your code private  

---

## 📋 Prerequisites

- **VersaAI installed** (see main README.md)
- **At least one model downloaded** (DeepSeek 1.3B recommended for testing)
- **Python 3.8+**
- **Code editor** (NLPL Editor, VS Code, or custom)

---

## ⚡ Quick Start (2 Steps)

### Step 1: Start VersaAI Bridge Server

```bash
cd VersaAI
python start_editor_bridge.py
```

You should see:
```
============================================================
🚀 VersaAI Editor Bridge Server
============================================================
WebSocket: ws://localhost:8765
Status: Ready for connections

Available features:
  - Code completion
  - AI chat assistant
  - Code explanation
  - Refactoring suggestions
  - Debugging assistance
  - Test generation

Press Ctrl+C to stop
============================================================
```

### Step 2: Connect Your Editor

#### For NLPL Editor:

```bash
# In a new terminal
cd /path/to/code_editor
npm run dev
```

The editor will automatically connect to VersaAI when you open it.

#### For Custom Integration:

See [`docs/CODE_EDITOR_INTEGRATION.md`](docs/CODE_EDITOR_INTEGRATION.md) for WebSocket API documentation.

---

## 🧪 Testing the Integration

### Test 1: Verify Server is Running

```bash
# In a new terminal
python test_editor_bridge.py
```

You should see:
```
🧪 VersaAI Editor Bridge - WebSocket Test
============================================================

Test 1: Ping
✅ Ping test passed

Test 2: Code Completion
✅ Completion test passed

Test 3: Chat
✅ Chat test passed

Test 4: Error Handling
✅ Error handling test passed

============================================================
✅ ALL TESTS PASSED!
============================================================
```

### Test 2: Manual WebSocket Test

```python
# test_websocket.py
import asyncio
import websockets
import json

async def test():
    async with websockets.connect('ws://localhost:8765') as ws:
        # Send chat message
        await ws.send(json.dumps({
            'id': '1',
            'type': 'chat',
            'session_id': 'my-session',
            'message': 'Hello VersaAI!',
            'file_context': {
                'path': 'test.py',
                'language': 'python'
            }
        }))
        
        # Get response
        response = await ws.recv()
        data = json.loads(response)
        print(f"VersaAI: {data['response']}")

asyncio.run(test())
```

---

## 🎯 Features in Editor

Once connected, you get:

### 1. Real-Time Code Completion

Start typing and VersaAI will suggest completions:

```python
def calculate_|  # ← AI suggests function completion
```

### 2. AI Chat Panel

Click 🤖 icon or press `Ctrl+Shift+I`:

- Ask questions about code
- Get explanations
- Request help with debugging
- Generate documentation

### 3. Code Actions (Right-Click)

Select code → Right-click → VersaAI:

- **Explain Code** - Get detailed explanation
- **Refactor** - Improvement suggestions
- **Generate Tests** - Auto-create unit tests
- **Debug** - Help finding bugs
- **Add Docs** - Generate comments/docstrings

### 4. Inline Chat

Press `Ctrl+K` / `Cmd+K`:

- Quick inline questions
- Fast refactoring
- Code transformations

---

## 🔧 Configuration

### Default Configuration

The server runs with these defaults:

```yaml
host: localhost
port: 8765
features:
  - code_completion: enabled
  - chat: enabled
  - explain: enabled
  - refactor: enabled
  - debug: enabled
  - test_generation: enabled
```

### Custom Configuration

Create `~/.versaai/editor_bridge.yaml`:

```yaml
server:
  host: localhost
  port: 8765
  
features:
  completion:
    enabled: true
    delay_ms: 100  # Delay before showing suggestions
    min_chars: 2   # Minimum characters to trigger
    
  chat:
    enabled: true
    max_history: 50  # Max messages in history
    
models:
  completion: deepseek-1.3b  # Fast model for completions
  chat: deepseek-6.7b        # Better model for chat
  
cache:
  enabled: true
  max_size: 1000
  ttl: 300  # 5 minutes
```

---

## 📡 WebSocket API

### Message Format

All messages are JSON:

```json
{
  "id": "unique-id",
  "type": "message_type",
  ...message_data
}
```

### Message Types

#### 1. Code Completion

**Request:**
```json
{
  "id": "1",
  "type": "completion",
  "context": {
    "file_path": "src/main.py",
    "language": "python",
    "prefix": "def calculate_",
    "suffix": ":\n    pass",
    "line": 10,
    "column": 15
  }
}
```

**Response:**
```json
{
  "id": "1",
  "status": "ok",
  "completions": ["fibonacci(n: int) -> int"],
  "model": "deepseek-1.3b",
  "cached": false
}
```

#### 2. Chat

**Request:**
```json
{
  "id": "2",
  "type": "chat",
  "session_id": "editor-session",
  "message": "How do I optimize this function?",
  "file_context": {
    "path": "src/main.py",
    "language": "python",
    "selected_code": "def slow_function():\n    ..."
  }
}
```

**Response:**
```json
{
  "id": "2",
  "status": "ok",
  "response": "Here are optimization suggestions...",
  "model": "deepseek-6.7b",
  "session_id": "editor-session"
}
```

#### 3. Explain Code

**Request:**
```json
{
  "id": "3",
  "type": "explain",
  "session_id": "editor-session",
  "code": "def fibonacci(n):\n    return n if n <= 1 else fibonacci(n-1) + fibonacci(n-2)",
  "language": "python",
  "file_path": "algorithms.py"
}
```

**Response:**
```json
{
  "id": "3",
  "status": "ok",
  "response": "This is a recursive Fibonacci implementation...",
  "model": "deepseek-6.7b"
}
```

#### 4. Other Operations

- **refactor** - Code refactoring suggestions
- **debug** - Debugging assistance
- **test** - Test generation
- **index_project** - Index project for RAG
- **ping** - Health check

See [`docs/CODE_EDITOR_INTEGRATION.md`](docs/CODE_EDITOR_INTEGRATION.md) for complete API documentation.

---

## 🐛 Troubleshooting

### Server Won't Start

**Problem:** `Address already in use`

```bash
# Check if something is using port 8765
lsof -i :8765

# Kill the process
kill -9 <PID>

# Or use different port
python start_editor_bridge.py --port 8766
```

### Connection Refused

**Problem:** Editor can't connect

**Solution:**
1. Check server is running: `lsof -i :8765`
2. Check firewall: `sudo ufw allow 8765`
3. Try `127.0.0.1` instead of `localhost`

### Slow Responses

**Problem:** Completions/chat are slow

**Solutions:**
- Use faster model (DeepSeek 1.3B)
- Enable caching
- Reduce context size
- Use GPU acceleration

### No Model Responses

**Problem:** Fallback mode messages

**Solution:**
```bash
# Download models
python -m versaai.cli.download_models --model deepseek-1.3b

# Verify models
ls ~/.versaai/models/

# Restart server
```

---

## 📚 Additional Resources

- **Complete Guide:** [`docs/CODE_EDITOR_INTEGRATION.md`](docs/CODE_EDITOR_INTEGRATION.md)
- **User Manual:** [`docs/USER_GUIDE.md`](docs/USER_GUIDE.md)
- **API Reference:** [`docs/API_REFERENCE.md`](docs/API_REFERENCE.md)
- **Examples:** `examples/editor_integration/`

---

## 🎓 Next Steps

1. ✅ **Start the server** - `python start_editor_bridge.py`
2. ✅ **Run tests** - `python test_editor_bridge.py`
3. ✅ **Connect editor** - See editor-specific instructions
4. 📖 **Read full guide** - `docs/CODE_EDITOR_INTEGRATION.md`
5. 🔧 **Customize** - Create `~/.versaai/editor_bridge.yaml`

---

## 💡 Tips & Tricks

### Performance Optimization

```yaml
# Use fast model for completions
models:
  completion: deepseek-1.3b
  chat: deepseek-6.7b

# Enable aggressive caching
cache:
  enabled: true
  max_size: 5000
  ttl: 600
```

### Privacy Mode

```yaml
# Local models only (no API calls)
models:
  allowed: [deepseek-1.3b, deepseek-6.7b, starcoder2-7b]
  block_apis: true
```

### Development Mode

```bash
# Verbose logging
python start_editor_bridge.py --verbose

# Custom port
python start_editor_bridge.py --port 9000
```

---

## 📞 Support

- **Documentation:** `docs/` directory
- **Examples:** `examples/` directory
- **Issues:** [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-repo/discussions)

---

**🚀 Happy Coding with VersaAI!**

*Making AI-powered development accessible to everyone*
