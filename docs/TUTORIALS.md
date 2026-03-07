# 🎓 VersaAI Tutorials

**Step-by-step guides for mastering VersaAI**

---

## 📑 Table of Contents

1. [Tutorial 1: First Steps](#tutorial-1-first-steps)
2. [Tutorial 2: Code Generation](#tutorial-2-code-generation)
3. [Tutorial 3: Multi-Model Setup](#tutorial-3-multi-model-setup)
4. [Tutorial 4: RAG Pipeline](#tutorial-4-rag-pipeline)
5. [Tutorial 5: Custom Integration](#tutorial-5-custom-integration)
6. [Tutorial 6: Performance Optimization](#tutorial-6-performance-optimization)

---

## Tutorial 1: First Steps

**Goal:** Get VersaAI up and running in 10 minutes  
**Level:** Beginner  
**Time:** 10 minutes

### Step 1: Installation

```bash
# Clone repository
git clone https://github.com/yourusername/VersaAI.git
cd VersaAI

# Install dependencies
pip install -r requirements.txt

# Install VersaAI
pip install -e .
```

### Step 2: Verify Installation

```bash
# Run verification script
python verify_setup.py
```

Expected output:
```
✅ Python version: 3.10.x
✅ Dependencies installed
✅ VersaAI package found
✅ Configuration directory created
All checks passed!
```

### Step 3: Download Your First Model

```bash
# Download small model for testing
python scripts/download_code_models.py --model deepseek-coder-1.3b --install-deps
```

This will:
- Install llama-cpp-python
- Download the model (~900MB)
- Place it in ~/.versaai/models/

### Step 4: Launch VersaAI

```bash
# Launch interactive assistant
./scripts/launch_code_assistant.sh
```

Select option 1 (Local Model), then select the model you downloaded.

### Step 5: Your First Query

```
VersaAI> write a function to calculate factorial in Python

Assistant> Here's an efficient factorial function:

def factorial(n):
    """Calculate factorial of n."""
    if n < 0:
        raise ValueError("Factorial not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

# Example
print(factorial(5))  # Output: 120
```

### What You Learned

✅ Install VersaAI  
✅ Download a model  
✅ Launch the CLI  
✅ Generate code

**Next:** Try Tutorial 2 to explore more features!

---

## Tutorial 2: Code Generation

**Goal:** Master different types of code generation  
**Level:** Beginner  
**Time:** 20 minutes

### Generating Functions

**Task: Create a function to validate passwords**

```
You> write a Python function to validate passwords with these rules:
- At least 8 characters
- Contains uppercase and lowercase
- Contains at least one digit
- Contains at least one special character

Assistant> Here's a robust password validator:

import re

def validate_password(password: str) -> tuple[bool, list[str]]:
    """
    Validate password against security rules.
    
    Returns:
        (is_valid, errors): Boolean and list of validation errors
    """
    errors = []
    
    if len(password) < 8:
        errors.append("Password must be at least 8 characters")
    
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain uppercase letter")
    
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain lowercase letter")
    
    if not re.search(r'\d', password):
        errors.append("Password must contain digit")
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain special character")
    
    return len(errors) == 0, errors

# Example usage
valid, errors = validate_password("MyPass123!")
if valid:
    print("Password is valid!")
else:
    print("Errors:", errors)
```

### Generating Classes

**Task: Create a class for a bank account**

```
You> create a Python class for a bank account with deposit, withdraw, and balance methods. Include proper error handling.

Assistant> [Shows complete BankAccount class with error handling]
```

### Generating APIs

**Task: Create a REST API endpoint**

```
You> create a Flask REST API endpoint for user registration with email validation

Assistant> [Shows complete Flask app with validation]
```

### Best Practices for Prompts

**Good Prompts:**
```
✅ "Write a Python function to merge two sorted lists efficiently"
✅ "Create a React component for a todo list with add/remove functionality"
✅ "Generate a SQL query to find duplicate records in a users table"
```

**Bad Prompts:**
```
❌ "code"
❌ "help me"
❌ "make it work"
```

**Pro Tips:**
- Specify the language
- Describe the functionality clearly
- Mention any constraints or requirements
- Ask for error handling if needed

### Exercise

Try generating:
1. A function to find the nth Fibonacci number
2. A class for a shopping cart
3. An API endpoint for user authentication

---

## Tutorial 3: Multi-Model Setup

**Goal:** Configure and use multiple models  
**Level:** Intermediate  
**Time:** 30 minutes

### Step 1: Download Multiple Models

```bash
# Download different models for different tasks
python scripts/download_code_models.py --model deepseek-coder-1.3b
python scripts/download_code_models.py --model deepseek-coder-6.7b
```

### Step 2: Create Model Router Configuration

Create `~/.versaai/config/model_router.json`:

```json
{
  "models": [
    {
      "name": "fast-model",
      "provider": "llama-cpp",
      "path": "~/.versaai/models/deepseek-coder-1.3b-instruct.Q4_K_M.gguf",
      "specialization": "simple_code",
      "cost_per_1k_tokens": 0,
      "priority": 1
    },
    {
      "name": "quality-model",
      "provider": "llama-cpp",
      "path": "~/.versaai/models/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
      "specialization": "complex_code",
      "cost_per_1k_tokens": 0,
      "priority": 2
    }
  ],
  "routing_rules": {
    "simple_function": "fast-model",
    "complex_algorithm": "quality-model",
    "explanation": "quality-model",
    "default": "quality-model"
  },
  "auto_routing": {
    "enabled": true,
    "criteria": {
      "query_length_threshold": 50
    }
  }
}
```

### Step 3: Use Model Router in Python

```python
from versaai.models import ModelRouter

# Initialize router
router = ModelRouter("~/.versaai/config/model_router.json")

# Simple query → fast model
response1 = router.query("write a hello world function")

# Complex query → quality model
response2 = router.query("implement a binary search tree with insert, delete, and search operations")

# Manual selection
response3 = router.query("your prompt", model="quality-model")
```

### Step 4: Add Cloud API (Optional)

```bash
# Set API key
export OPENAI_API_KEY="sk-your-key-here"
```

Update `model_router.json`:

```json
{
  "models": [
    {
      "name": "local-fast",
      "provider": "llama-cpp",
      "path": "~/.versaai/models/deepseek-coder-1.3b.gguf",
      "cost_per_1k_tokens": 0,
      "priority": 1
    },
    {
      "name": "cloud-best",
      "provider": "openai",
      "model_id": "gpt-4-turbo",
      "cost_per_1k_tokens": 10,
      "priority": 3
    }
  ],
  "routing_rules": {
    "simple": "local-fast",
    "complex_reasoning": "cloud-best",
    "default": "local-fast"
  }
}
```

### Step 5: Cost-Aware Routing

```python
from versaai.models import ModelRouter

router = ModelRouter("~/.versaai/config/model_router.json")

# Set budget
router.set_daily_budget(dollars=5.0)

# Router automatically picks cheapest suitable model
response = router.query("your prompt")

# Check usage
print(f"Cost today: ${router.get_daily_cost():.4f}")
```

### What You Learned

✅ Configure multiple models  
✅ Set up routing rules  
✅ Use automatic model selection  
✅ Manage costs

---

## Tutorial 4: RAG Pipeline

**Goal:** Build a document Q&A system  
**Level:** Intermediate  
**Time:** 30 minutes

### Step 1: Prepare Documents

```bash
# Create a docs directory
mkdir -p ~/my_docs

# Add some markdown files
echo "# API Reference\n\nOur API uses REST..." > ~/my_docs/api.md
echo "# User Guide\n\nTo get started..." > ~/my_docs/guide.md
```

### Step 2: Initialize RAG Pipeline

```python
from versaai.rag import RAGPipeline

# Create RAG instance
rag = RAGPipeline(
    vector_db_path="~/.versaai/my_project_db",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)
```

### Step 3: Index Documents

```python
# Index single file
rag.index_documents(["~/my_docs/api.md"])

# Index directory
rag.index_documents(["~/my_docs/"])

# Index with metadata
rag.index_documents([
    {
        "path": "~/my_docs/api.md",
        "metadata": {"type": "reference", "version": "1.0"}
    }
])
```

### Step 4: Query the System

```python
# Simple query
answer = rag.query("How do I authenticate with the API?")
print(answer)

# Query with sources
result = rag.query(
    "What are the system requirements?",
    return_sources=True,
    top_k=3
)

print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
print(f"Confidence: {result['confidence']}")
```

### Step 5: Advanced Features

**Filter by metadata:**
```python
# Only search API docs
answer = rag.query(
    "authentication methods",
    filters={"type": "reference"}
)
```

**Adjust retrieval:**
```python
# Get more context
answer = rag.query(
    "your question",
    top_k=5,          # Retrieve top 5 chunks
    similarity_threshold=0.7  # Minimum similarity
)
```

**Hybrid search:**
```python
# Combine keyword and semantic search
answer = rag.query(
    "your question",
    hybrid_search=True,
    keyword_weight=0.3,
    semantic_weight=0.7
)
```

### Step 6: Build a Chat Interface

```python
from versaai.rag import RAGPipeline
from versaai import VersaAI

# Initialize
rag = RAGPipeline(vector_db_path="~/.versaai/docs_db")
ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")

# Index documentation
rag.index_documents(["docs/"])

# Chat loop
print("Documentation Q&A System")
print("Ask questions about the docs (or 'quit' to exit)\n")

while True:
    question = input("You: ")
    if question.lower() == 'quit':
        break
    
    # Retrieve relevant context
    context = rag.retrieve(question, top_k=3)
    
    # Generate answer with context
    prompt = f"""Based on this context:
{context}

Answer this question: {question}
"""
    
    answer = ai.generate(prompt)
    print(f"Assistant: {answer}\n")
```

### What You Learned

✅ Set up RAG pipeline  
✅ Index documents  
✅ Query with context  
✅ Build Q&A system

---

## Tutorial 5: Custom Integration

**Goal:** Integrate VersaAI into your application  
**Level:** Advanced  
**Time:** 45 minutes

### Step 1: Basic Integration

```python
# myapp.py
from versaai import VersaAI

class MyApplication:
    def __init__(self):
        self.ai = VersaAI(
            provider="llama-cpp",
            model="~/.versaai/models/deepseek-coder-6.7b.gguf"
        )
    
    def generate_documentation(self, code: str) -> str:
        """Generate docs for code."""
        prompt = f"Generate Python docstrings for:\n{code}"
        return self.ai.generate(prompt)
    
    def review_code(self, code: str) -> str:
        """Review code for issues."""
        prompt = f"Review this code for bugs and improvements:\n{code}"
        return self.ai.generate(prompt)
    
    def generate_tests(self, code: str) -> str:
        """Generate unit tests."""
        prompt = f"Generate pytest tests for:\n{code}"
        return self.ai.generate(prompt)

# Usage
app = MyApplication()

code = """
def divide(a, b):
    return a / b
"""

docs = app.generate_documentation(code)
review = app.review_code(code)
tests = app.generate_tests(code)

print(docs)
```

### Step 2: Add Caching

```python
from versaai import VersaAI
from functools import lru_cache
import hashlib

class CachedAI:
    def __init__(self):
        self.ai = VersaAI(
            provider="llama-cpp",
            model="deepseek-coder-6.7b.gguf"
        )
        self.cache = {}
    
    def generate(self, prompt: str) -> str:
        """Generate with caching."""
        # Create cache key
        key = hashlib.md5(prompt.encode()).hexdigest()
        
        # Check cache
        if key in self.cache:
            print("Cache hit!")
            return self.cache[key]
        
        # Generate
        response = self.ai.generate(prompt)
        
        # Cache result
        self.cache[key] = response
        
        return response
```

### Step 3: Add Error Handling

```python
from versaai import VersaAI
import logging

class RobustAI:
    def __init__(self):
        self.ai = VersaAI(
            provider="llama-cpp",
            model="deepseek-coder-6.7b.gguf"
        )
        self.logger = logging.getLogger(__name__)
    
    def generate_safe(self, prompt: str, max_retries: int = 3) -> str:
        """Generate with error handling."""
        for attempt in range(max_retries):
            try:
                response = self.ai.generate(prompt)
                return response
            except Exception as e:
                self.logger.warning(
                    f"Attempt {attempt + 1} failed: {e}"
                )
                if attempt == max_retries - 1:
                    self.logger.error("All retries exhausted")
                    raise
        
        return None
```

### Step 4: Build a Web API

```python
# api_server.py
from flask import Flask, request, jsonify
from versaai import VersaAI

app = Flask(__name__)
ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")

@app.route('/api/generate', methods=['POST'])
def generate():
    """Generate code endpoint."""
    data = request.json
    prompt = data.get('prompt')
    
    if not prompt:
        return jsonify({"error": "Missing prompt"}), 400
    
    try:
        response = ai.generate(prompt)
        return jsonify({
            "success": True,
            "response": response
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
```

Run the server:
```bash
python api_server.py
```

Use the API:
```bash
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "write a hello world function"}'
```

### Step 5: Async Processing

```python
import asyncio
from versaai import VersaAI

class AsyncAI:
    def __init__(self):
        self.ai = VersaAI(
            provider="llama-cpp",
            model="deepseek-coder-6.7b.gguf"
        )
    
    async def generate_async(self, prompt: str) -> str:
        """Async generation."""
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            self.ai.generate,
            prompt
        )
        return response
    
    async def batch_generate(self, prompts: list[str]) -> list[str]:
        """Generate for multiple prompts concurrently."""
        tasks = [
            self.generate_async(prompt)
            for prompt in prompts
        ]
        return await asyncio.gather(*tasks)

# Usage
async def main():
    ai = AsyncAI()
    
    prompts = [
        "write a hello world function",
        "write a factorial function",
        "write a fibonacci function"
    ]
    
    responses = await ai.batch_generate(prompts)
    for prompt, response in zip(prompts, responses):
        print(f"Prompt: {prompt}")
        print(f"Response: {response}\n")

asyncio.run(main())
```

### What You Learned

✅ Integrate VersaAI in applications  
✅ Add caching  
✅ Handle errors robustly  
✅ Build web APIs  
✅ Use async processing

---

## Tutorial 6: Performance Optimization

**Goal:** Maximize VersaAI performance  
**Level:** Advanced  
**Time:** 30 minutes

### Step 1: Benchmark Baseline

```python
import time
from versaai import VersaAI

ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")

# Benchmark
prompts = [
    "write a hello world function",
    "explain quick sort",
    "create a binary tree class"
]

start = time.time()
for prompt in prompts:
    response = ai.generate(prompt)
end = time.time()

print(f"Baseline: {end - start:.2f}s for {len(prompts)} queries")
print(f"Average: {(end - start) / len(prompts):.2f}s per query")
```

### Step 2: Enable GPU Acceleration

```python
from versaai import VersaAI

# Use GPU
ai = VersaAI(
    provider="llama-cpp",
    model="deepseek-coder-6.7b.gguf",
    n_gpu_layers=-1  # Use all GPU layers
)

# Benchmark again
# Expected: 5-10x speedup
```

Check GPU usage:
```bash
nvidia-smi -l 1  # Monitor GPU every second
```

### Step 3: Optimize Model Loading

```python
from versaai import VersaAI

# Optimized configuration
ai = VersaAI(
    provider="llama-cpp",
    model="deepseek-coder-6.7b.gguf",
    n_gpu_layers=-1,
    n_ctx=2048,           # Smaller context window
    n_batch=512,          # Larger batch size
    n_threads=8,          # Match CPU cores
    use_mlock=True,       # Lock model in RAM
    use_mmap=True,        # Memory-map model file
    verbose=False         # Disable verbose logging
)
```

### Step 4: Use Smaller/Quantized Models

```bash
# Q4_K_M is 2-3x faster than Q8_0
python scripts/download_code_models.py \
  --model deepseek-coder-6.7b \
  --quantization Q4_K_M  # vs Q8_0 or Q5_K_M
```

Quality vs Speed trade-off:
- Q8_0: Best quality, slowest
- Q5_K_M: Balanced
- Q4_K_M: Good quality, fastest

### Step 5: Implement Request Batching

```python
from versaai import VersaAI
from queue import Queue
from threading import Thread
import time

class BatchedAI:
    def __init__(self, batch_size=4, max_wait=1.0):
        self.ai = VersaAI(
            provider="llama-cpp",
            model="deepseek-coder-6.7b.gguf",
            n_gpu_layers=-1
        )
        self.batch_size = batch_size
        self.max_wait = max_wait
        self.queue = Queue()
        self.worker = Thread(target=self._process_batches, daemon=True)
        self.worker.start()
    
    def _process_batches(self):
        """Process requests in batches."""
        while True:
            batch = []
            deadline = time.time() + self.max_wait
            
            # Collect batch
            while len(batch) < self.batch_size and time.time() < deadline:
                try:
                    item = self.queue.get(timeout=0.1)
                    batch.append(item)
                except:
                    pass
            
            # Process batch
            if batch:
                for prompt, result_queue in batch:
                    response = self.ai.generate(prompt)
                    result_queue.put(response)
    
    def generate(self, prompt: str) -> str:
        """Submit request and wait for response."""
        result_queue = Queue()
        self.queue.put((prompt, result_queue))
        return result_queue.get()
```

### Step 6: Profile and Monitor

```python
import cProfile
import pstats
from versaai import VersaAI

def profile_generation():
    ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")
    
    # Generate
    for i in range(10):
        ai.generate("write a hello world function")

# Profile
profiler = cProfile.Profile()
profiler.enable()
profile_generation()
profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(10)
```

Monitor memory:
```python
import tracemalloc

tracemalloc.start()

# Your code here
ai = VersaAI(provider="llama-cpp", model="deepseek-coder-6.7b.gguf")
response = ai.generate("write a function")

# Check memory
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.2f} MB")
print(f"Peak: {peak / 1024 / 1024:.2f} MB")
tracemalloc.stop()
```

### Performance Checklist

✅ Use GPU if available (`--n-gpu-layers -1`)  
✅ Use quantized models (Q4_K_M)  
✅ Optimize context window size  
✅ Increase batch size  
✅ Enable model memory locking  
✅ Use appropriate thread count  
✅ Implement caching for repeated queries  
✅ Batch requests when possible  

---

## 🎓 Next Steps

After completing these tutorials:

1. **Explore Examples** - Check `examples/` directory
2. **Read User Guide** - [docs/USER_GUIDE.md](USER_GUIDE.md)
3. **Join Community** - Share your projects
4. **Contribute** - Help improve VersaAI

---

## 📚 Additional Resources

- [User Guide](USER_GUIDE.md) - Complete reference
- [Quick Reference](QUICK_REFERENCE.md) - Cheat sheet
- [API Reference](API_REFERENCE.md) - API docs
- [GitHub Issues](https://github.com/yourusername/VersaAI/issues) - Get help

---

**Happy Learning!** 🚀

**VersaAI - Production-Grade AI for Everyone**
