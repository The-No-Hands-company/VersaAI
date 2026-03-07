# Model Router - Quick Reference Card

## 📥 Download Models

```bash
# Check what you need
python scripts/download_models.py check

# List available models
python scripts/download_models.py list

# Download recommended starter (4GB)
python scripts/download_models.py download deepseek

# Download all models (26.6GB)
python scripts/download_models.py download-all
```

## 🎯 Model Selection (Automatic)

```python
from versaai.models.model_router import ModelRouter

router = ModelRouter(available_ram_gb=16)

# Router automatically selects best model
model_id, spec = router.select_model(
    task="Your coding task",
    language="python"  # optional
)

print(f"Selected: {spec.name}")
```

## 🤖 Generation Modes

```python
from versaai.models.model_ensemble import ModelEnsemble

ensemble = ModelEnsemble(router, model_loader)

# Auto - Router decides (RECOMMENDED)
result = ensemble.generate(task, mode="auto")

# Fast - Quick responses
result = ensemble.generate(task, mode="fast")

# Quality - Best output
result = ensemble.generate(task, mode="quality")

# Consensus - Multiple models vote
result = ensemble.generate(task, mode="consensus")
```

## 📊 Model Comparison

| Model | Size | RAM | Speed | Quality | Use When |
|-------|------|-----|-------|---------|----------|
| **Phi-2** | 1.6GB | 4GB | ⚡⚡⚡ | ⭐⭐⭐ | Simple functions, quick tasks |
| **DeepSeek** | 4.0GB | 8GB | ⚡⚡ | ⭐⭐⭐⭐ | Python/JS, general coding |
| **StarCoder2** | 4.5GB | 8GB | ⚡⚡ | ⭐⭐⭐⭐ | Multi-language, enterprise |
| **CodeLlama** | 7.5GB | 16GB | ⚡ | ⭐⭐⭐⭐⭐ | Algorithms, optimization |
| **WizardCoder** | 9.0GB | 16GB | ⚡ | ⭐⭐⭐⭐⭐ | Debugging, refactoring |

## 🎓 Selection Examples

```python
# Simple task → Phi-2
"Create a function to add numbers"

# Medium task → DeepSeek/StarCoder2
"Build REST API with CRUD operations"

# Complex task → CodeLlama/WizardCoder
"Implement distributed cache with Redis"

# Debugging → WizardCoder
"Debug memory leaks in C++ app"

# Refactoring → WizardCoder
"Refactor code to modern patterns"
```

## 🔧 Advanced Options

```python
# Prefer speed
router.select_model(task, prefer_speed=True)

# Prefer quality
router.select_model(task, prefer_quality=True)

# Check model info
info = router.get_model_info("deepseek")
print(info)

# List all models
models = router.list_models()

# Get statistics
stats = ensemble.get_stats()
```

## 💾 Memory Management

```python
# Unload specific model
ensemble.unload_model("codellama")

# Unload all models
ensemble.unload_all()
```

## 🌐 For Limited Resources

### Low RAM (<8GB)
```bash
# Download only Phi-2
python scripts/download_models.py download phi2

# Or use APIs (no download)
export OPENAI_API_KEY="..."
```

### Medium RAM (8-16GB)
```bash
# Download 2-3 models
python scripts/download_models.py download phi2
python scripts/download_models.py download deepseek
```

### High RAM (16GB+)
```bash
# Download all for full capability
python scripts/download_models.py download-all
```

## ⚡ Quick Start (30 seconds)

```bash
# 1. Check system
python scripts/download_models.py check

# 2. Download one model
python scripts/download_models.py download deepseek

# 3. Use in Python
python3 << 'EOF'
from versaai.models.model_router import ModelRouter

router = ModelRouter(available_ram_gb=16)
model_id, spec = router.select_model("Create Python factorial function")
print(f"Selected: {spec.name} ({spec.tier.value})")
EOF
```

## 📚 Documentation

- **Full Guide:** `docs/MODEL_ROUTER_GUIDE.md`
- **Summary:** `docs/MODEL_ROUTER_SUMMARY.md`
- **Code:** `versaai/models/model_router.py`
- **Ensemble:** `versaai/models/model_ensemble.py`

---

**TL;DR:** Download models → Router selects automatically → You get best results!
