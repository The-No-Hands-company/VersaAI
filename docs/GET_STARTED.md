# Get Started with VersaAI in 5 Minutes

**The fastest way to start coding with AI assistance.**

---

## 🚀 Option 1: CLI Assistant (Recommended for First-Time Users)

### Step 1: Install (1 minute)

```bash
cd VersaAI
pip install -e .
```

### Step 2: Launch (30 seconds)

```bash
versaai
```

### Step 3: Choose Model (1 minute)

You'll see this menu:

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

**Choose Option 1** (Local Model)

### Step 4: Download Model (2 minutes)

Select a model to download:

```
Download Options:

  1. deepseek-coder-1.3b-instruct (834MB) - FAST, Good for learning
  2. deepseek-coder-6.7b-instruct (4.1GB) - BEST BALANCE
  3. starcoder2-7b (4.3GB) - Great for code generation
  4. codellama-7b (4.0GB) - General purpose
  5. qwen2.5-coder-7b (4.4GB) - Latest, high quality

Recommended for first time: Option 1 or 2
```

**For fast setup:** Choose `1` (deepseek-1.3b, 834MB)  
**For best quality:** Choose `2` (deepseek-6.7b, 4.1GB)

Download will start automatically.

### Step 5: Start Coding with AI! (Now!)

Once downloaded, the assistant launches automatically:

```
✅ Model loaded successfully!

VersaAI Code Assistant
Type /help for commands, /exit to quit

💬 Chat Mode Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

> 
```

**Try these:**

```
> How do I read a CSV file in Python?

> Explain what list comprehensions are

> /code Write a function to validate email addresses

> /file mycode.py  # Analyze a specific file
```

**That's it! You're now coding with AI assistance!** 🎉

---

## 🎨 Option 2: Code Editor Integration (For Editor Users)

### Step 1: Install VersaAI Backend (1 minute)

```bash
cd VersaAI
pip install -e .
```

### Step 2: Install Code Editor (2 minutes)

```bash
cd ../code_editor
npm install
npx @electron/rebuild  # Rebuild native modules
```

### Step 3: Start VersaAI Backend (30 seconds)

Open a terminal:

```bash
cd VersaAI
python -m versaai.code_editor_bridge.server
```

You'll see:

```
🚀 VersaAI Code Editor Bridge Server
📡 WebSocket server running on ws://localhost:9001
✅ Ready for connections
```

**Keep this terminal open!**

### Step 4: Start Code Editor (30 seconds)

Open a NEW terminal:

```bash
cd code_editor
npm run dev
```

The editor will launch.

### Step 5: Use AI in Editor (Now!)

**Open AI Assistant:**
- Press `Ctrl+Alt+V`  
- OR click the 🤖 icon in the left Activity Bar

**The AI panel opens in the sidebar!**

**Try this:**
1. Open a code file (Python, JavaScript, etc.)
2. Press `Ctrl+Alt+V`
3. Ask: "Explain this code"
4. The AI responds with context about YOUR file!

**That's it! AI is now integrated in your editor!** 🎨

---

## 💡 Quick Tips

### For CLI Users

| Command | What it does |
|---------|-------------|
| `> Hello` | Chat with AI |
| `/code <description>` | Generate code |
| `/file <path>` | Analyze a file |
| `/help` | Show all commands |
| `/exit` or `Ctrl+D` | Exit |

### For Editor Users

| Shortcut | What it does |
|----------|-------------|
| `Ctrl+Alt+V` | Toggle AI panel |
| Type in AI panel | Chat with AI |
| `Ctrl+L` | Clear chat |
| Click ❌ | Close panel |

---

## 🆘 Troubleshooting

### "Model not found"

**Fix:** Download a model first

```bash
versaai
# Select "Download new model"
# Choose option 1 or 2
```

### "Can't connect to backend" (Editor)

**Fix:** Make sure backend is running

```bash
# Terminal 1: Start backend
python -m versaai.code_editor_bridge.server

# Terminal 2: Start editor
cd code_editor
npm run dev
```

### "Out of memory"

**Fix:** Use smaller model

```bash
versaai
# Select deepseek-1.3b instead of 6.7b
```

### "Model download failed"

**Fix:** Try manual download

```bash
cd ~/.versaai/models
wget https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf
```

---

## 📚 What's Next?

Once you're comfortable with the basics:

1. **Try different models** - Compare quality/speed
2. **Explore multi-model mode** - `versaai --multi-model`
3. **Read the full guide** - [COMPREHENSIVE_USER_GUIDE.md](COMPREHENSIVE_USER_GUIDE.md)
4. **Set up RAG** - Index your codebase for better context
5. **Customize configuration** - `~/.versaai/config/settings.yaml`

---

## 🎯 Common Use Cases

### Generate Code

```
> /code Create a Flask REST API with user authentication
```

### Explain Code

```
> Explain how decorators work in Python
```

### Analyze Files

```
> /file myproject/auth.py
> What security issues do you see?
```

### Refactor Code

```
> /file messy_code.py
> How can I make this more readable?
```

### Debug Issues

```
> /file broken.py
> Why am I getting a KeyError on line 42?
```

---

## ✅ Success Checklist

- [ ] Installed VersaAI
- [ ] Downloaded at least one model
- [ ] Launched CLI assistant successfully
- [ ] Asked a question and got a response
- [ ] (Optional) Integrated with code editor
- [ ] (Optional) Used AI in editor with Ctrl+Alt+V

**All checked?** Congratulations! You're ready to code with AI! 🎉

---

## 📖 Full Documentation

For everything VersaAI can do:

- **[README.md](README.md)** - Project overview
- **[COMPREHENSIVE_USER_GUIDE.md](COMPREHENSIVE_USER_GUIDE.md)** - Complete guide
- **[STATUS.md](STATUS.md)** - Current capabilities
- **[docs/](docs/)** - All documentation

---

**Questions?** Check the [troubleshooting section](#-troubleshooting) or open an issue on GitHub.

**Happy coding with AI!** 🚀

---

**Made with ❤️ by The No-hands Company**
