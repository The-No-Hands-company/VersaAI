# VersaAI Hybrid C++/Python Architecture

**Status:** Architecture Pivot (November 2025)  
**Rationale:** Leverage C++ for performance, Python for ML ecosystem access and rapid development

## 🎯 Design Philosophy

VersaAI adopts a **hybrid architecture** that combines the strengths of both C++ and Python:

- **C++ Core:** Performance-critical infrastructure (logging, error handling, inference engine)
- **Python ML Layer:** Model management, agents, RAG, tool integration
- **pybind11 Bridge:** Seamless interop between C++ and Python components

This matches industry practices from **vLLM, TensorRT-LLM, llama.cpp**, and other production AI systems.

---

## 🏗️ Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
│  (VersaOS, VersaModeling, VersaGameEngine Integration)      │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│               Python: Agent & Orchestration Layer           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ResearchAgent│  │ ModelingAgent│  │   OSAgent    │      │
│  │  - Planning  │  │  - 3D Tasks  │  │ - Commands   │      │
│  │  - Tools     │  │  - Validation│  │ - Automation │      │
│  │  - RAG       │  │  - Workflow  │  │ - Monitoring │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │           Tool Integration & RAG                   │     │
│  │  - Web Search  - Code Execution  - Vector DB       │     │
│  │  - File Access - API Calls       - Knowledge Graph │     │
│  └────────────────────────────────────────────────────┘     │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Python: Model Management Layer                 │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              ModelRegistry (Python)                 │    │
│  │  - HuggingFace Integration (transformers)           │    │
│  │  - GGUF Support (llama-cpp-python)                  │    │
│  │  - Local Model Loading (PyTorch, ONNX)             │    │
│  │  - Model Selection & Routing                        │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ GPT Models   │  │ LLaMA Models │  │ Embeddings   │      │
│  │ (HF/OpenAI)  │  │ (GGUF/HF)    │  │ (Sentence-T) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────────┬────────────────────────────────────┘
                         │ pybind11
┌────────────────────────▼────────────────────────────────────┐
│           C++: Performance & Infrastructure Layer           │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              Inference Engine (C++)                 │    │
│  │  - Flash Attention Kernels                          │    │
│  │  - KV-Cache Management                              │    │
│  │  - Batching & Request Scheduling                    │    │
│  │  - Memory-Mapped Model Loading                      │    │
│  │  - Custom CUDA/ROCm Kernels                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │           Core Infrastructure (C++)                 │    │
│  │  - Logger (VersaAILogger)                           │    │
│  │  - Exception Handling (VersaAIException)            │    │
│  │  - Error Recovery (VersaAIErrorRecovery)            │    │
│  │  - Context Management (VersaAIContext)              │    │
│  │  - Core Registry (VersaAICore)                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Component Breakdown

### C++ Components (Keep & Enhance)

**Status:** ✅ **Already Implemented** (Phase 1.3 Complete)

1. **VersaAILogger** (`src/core/VersaAILogger.{hpp,cpp}`)
   - Structured logging with levels, context, metadata
   - Thread-safe operations
   - **Exposed to Python:** `versaai.core.Logger`

2. **VersaAIException** (`include/VersaAIException.hpp`, `src/core/VersaAIException.cpp`)
   - Hierarchical exception types
   - Error codes, context, stack traces
   - **Exposed to Python:** Python exceptions map to C++ hierarchy

3. **VersaAIErrorRecovery** (`include/VersaAIErrorRecovery.hpp`, `src/core/VersaAIErrorRecovery.cpp`)
   - Retry policies, circuit breakers, fallback strategies
   - **Exposed to Python:** Decorators for error handling

4. **VersaAICore** (`src/core/VersaAICore.{hpp,cpp}`)
   - Central registry for chatbots, agents, models
   - Session management
   - **Exposed to Python:** Core initialization and registration

5. **Inference Engine** (To Be Implemented in C++)
   - Tokenization (fast C++ implementation)
   - Attention mechanisms (Flash Attention, custom kernels)
   - KV-cache management
   - Request batching and scheduling
   - Memory-mapped model loading
   - **Called from Python:** Via pybind11 bindings

### Python Components (New Implementation)

**Status:** 🔄 **To Be Implemented** (Phase 2 Revised)

1. **Model Management** (`versaai/models/`)
   ```python
   # versaai/models/model_registry.py
   from transformers import AutoModelForCausalLM, AutoTokenizer
   from llama_cpp import Llama
   
   class ModelRegistry:
       def load_huggingface(self, model_id: str):
           """Load any HuggingFace model"""
           return AutoModelForCausalLM.from_pretrained(model_id)
       
       def load_gguf(self, path: str):
           """Load GGUF model via llama-cpp-python"""
           return Llama(model_path=path)
       
       def load_local(self, path: str, format: str):
           """Load local PyTorch/ONNX/SafeTensors"""
           # Auto-detect and load
   ```

2. **Agent System** (`versaai/agents/`)
   ```python
   # versaai/agents/research_agent.py
   from langchain.agents import AgentExecutor
   from langchain.tools import Tool
   
   class ResearchAgent:
       def __init__(self, model, tools):
           self.model = model
           self.tools = tools  # Web search, calculator, etc.
           self.memory = ConversationBufferMemory()
       
       def plan_and_execute(self, query: str):
           # Decompose → Search → Synthesize → Validate
           pass
   ```

3. **RAG Pipeline** (`versaai/rag/`)
   ```python
   # versaai/rag/retrieval.py
   from langchain.vectorstores import Chroma
   from langchain.embeddings import HuggingFaceEmbeddings
   
   class RAGSystem:
       def __init__(self, embedding_model):
           self.embeddings = HuggingFaceEmbeddings(model_name=embedding_model)
           self.vectordb = Chroma(embedding_function=self.embeddings)
       
       def retrieve(self, query: str, k: int = 5):
           return self.vectordb.similarity_search(query, k=k)
   ```

4. **Tool Integration** (`versaai/tools/`)
   ```python
   # versaai/tools/web_search.py
   from langchain.tools import BaseTool
   
   class WebSearchTool(BaseTool):
       name = "web_search"
       description = "Search the web for current information"
       
       def _run(self, query: str):
           # Integration with search API
           pass
   ```

### pybind11 Bridge (`bindings/`)

**Status:** 🔄 **To Be Implemented**

```cpp
// bindings/versaai_core.cpp
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include "VersaAILogger.hpp"
#include "VersaAIException.hpp"

namespace py = pybind11;
using namespace VersaAI;

PYBIND11_MODULE(versaai_core, m) {
    m.doc() = "VersaAI C++ Core Bindings";
    
    // Logger bindings
    py::class_<Logger>(m, "Logger")
        .def_static("get_instance", &Logger::getInstance, py::return_value_policy::reference)
        .def("info", &Logger::info)
        .def("warning", &Logger::warning)
        .def("error", &Logger::error)
        .def("debug", &Logger::debug);
    
    // Exception bindings
    py::register_exception<VersaAIException>(m, "VersaAIException");
    py::register_exception<ModelException>(m, "ModelException");
    py::register_exception<RegistryException>(m, "RegistryException");
    
    // Core registry bindings
    // ... expose necessary C++ functionality to Python
}
```

---

## 🔄 Data Flow Examples

### Example 1: User Query → Research Agent → Web Search → Response

```
User: "What are the latest developments in Flash Attention?"
  │
  ▼
┌─────────────────────────────────────────┐
│ Python: ResearchAgent.process(query)    │
│  1. Use C++ Logger for operation start  │
│  2. Decompose query into sub-questions  │
│  3. Call WebSearchTool (Python)         │
│  4. Retrieve from VectorDB (Python)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Python: ModelRegistry.generate()        │
│  - Select appropriate model             │
│  - Tokenize input (via HF tokenizer)    │
│  - Call inference                       │
└──────────────┬──────────────────────────┘
               │ (Optional: Use C++ inference for speed)
               ▼
┌─────────────────────────────────────────┐
│ C++: InferenceEngine.forward()          │
│  - Flash Attention kernels              │
│  - KV-cache management                  │
│  - Return logits to Python              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Python: ResearchAgent.synthesize()      │
│  - Combine search results + generation  │
│  - Format with citations                │
│  - Use C++ Logger for completion        │
└──────────────┬──────────────────────────┘
               │
               ▼
            Response to User
```

### Example 2: VersaModeling 3D Command

```
User: "Create a cube with dimensions 2x2x2"
  │
  ▼
┌─────────────────────────────────────────┐
│ Python: ModelingAgent.parse_command()   │
│  - Use C++ Logger for intent parsing    │
│  - Extract parameters (shape, size)     │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Python: ModelRegistry.get_model()       │
│  - Select specialized modeling model    │
│  - Generate Blender Python script       │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ C++: VersaAICore.validateCommand()      │
│  - C++ error recovery for safety        │
│  - Return validation result             │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│ Python: BlenderAPI.execute()            │
│  - Execute generated script             │
│  - Use C++ Logger for execution status  │
└──────────────┬──────────────────────────┘
               │
               ▼
         Cube created in Blender
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Current - Keep As-Is)
- ✅ C++ Core Infrastructure (Logger, Exceptions, ErrorRecovery, Context)
- ✅ Basic registry system (VersaAICore)

### Phase 2: Python Integration (Immediate Priority)
1. **Setup Python environment** (`pyproject.toml`, virtual env)
2. **Create pybind11 bindings** for existing C++ core
3. **Implement Python ModelRegistry** with HuggingFace support
4. **Port one agent to Python** (e.g., ResearchAgent) as proof-of-concept
5. **Test hybrid workflow**: Python agent → C++ logging → Python model

### Phase 3: Agent Migration (Short-term)
1. **Rewrite agents in Python** (ResearchAgent, ModelingAgent, OSAgent)
2. **Implement tool system** (WebSearch, Calculator, FileAccess)
3. **Build RAG pipeline** (VectorDB, embeddings, retrieval)
4. **Integrate with existing applications** (VersaOS, VersaModeling, VGE)

### Phase 4: Inference Optimization (Medium-term)
1. **C++ tokenization** (fast BPE/WordPiece implementation)
2. **C++ inference engine** (Flash Attention, KV-cache)
3. **CUDA/ROCm kernels** for GPU acceleration
4. **Batching & scheduling** for multi-request handling
5. **Expose to Python** via pybind11

### Phase 5: Production Hardening (Long-term)
1. **Performance profiling** (identify bottlenecks)
2. **Memory optimization** (minimize Python/C++ boundary crossings)
3. **Deployment packaging** (Docker, compiled wheels)
4. **Monitoring & observability** (metrics, tracing)

---

## 📚 Technology Stack

### C++ Layer
- **Build System:** CMake + Ninja
- **Compiler:** C++23 (GCC/Clang)
- **Bindings:** pybind11
- **Logging:** Custom VersaAILogger
- **GPU:** CUDA 12+ / ROCm (future)

### Python Layer
- **Version:** Python 3.10+
- **Package Manager:** uv (modern, fast)
- **Core ML:** PyTorch 2.0+, transformers
- **GGUF Support:** llama-cpp-python
- **Agents:** LangChain / LlamaIndex
- **Vector DB:** ChromaDB / FAISS
- **API:** FastAPI (if needed for serving)

### Development Tools
- **Formatting:** clang-format (C++), black (Python)
- **Linting:** clang-tidy (C++), ruff (Python)
- **Testing:** Catch2 (C++), pytest (Python)
- **CI/CD:** GitHub Actions

---

## 🎯 Design Decisions & Rationale

### Why Hybrid vs Pure Python?

| Aspect | Pure Python | Hybrid C++/Python | Pure C++ |
|--------|-------------|-------------------|----------|
| **Development Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |
| **ML Ecosystem Access** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ |
| **Performance** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Deployment Size** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Maintenance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

**Verdict:** Hybrid gives us **best of both worlds**

### Component Placement Guidelines

**Choose C++ when:**
- Tight loop performance critical (> 1M ops/sec)
- Direct memory management needed
- GPU kernel integration required
- Binary size matters
- Real-time constraints (< 10ms)

**Choose Python when:**
- Rapid prototyping needed
- ML library integration required
- Agent logic and reasoning
- Tool integration (APIs, web, files)
- RAG pipelines and vector search

---

## 🔧 Development Workflow

### Setting Up the Hybrid Environment

```bash
# 1. Build C++ core
cd /path/to/VersaAI
./scripts/build.sh

# 2. Setup Python environment
uv venv .venv
source .venv/bin/activate
uv pip install -e ".[dev]"  # Install in editable mode

# 3. Build Python bindings
cd bindings
mkdir build && cd build
cmake .. -G Ninja
ninja

# 4. Test integration
python -c "import versaai_core; logger = versaai_core.Logger.get_instance()"
```

### Typical Development Cycle

1. **Design in Python** (fast iteration)
2. **Profile** (find bottlenecks)
3. **Optimize critical paths in C++** (if needed)
4. **Expose via pybind11**
5. **Use from Python**

---

## 📖 Migration Plan for Existing Code

### Current C++ Model Infrastructure → Python

**Current (C++):**
```cpp
// include/VersaAIModel.hpp
class ModelBase {
    virtual void load() = 0;
    virtual std::string generate(const std::string& prompt) = 0;
};
```

**Migrated (Python):**
```python
# versaai/models/model_base.py
from abc import ABC, abstractmethod

class ModelBase(ABC):
    @abstractmethod
    def load(self) -> None:
        pass
    
    @abstractmethod
    def generate(self, prompt: str) -> str:
        pass

# versaai/models/huggingface_model.py
class HuggingFaceModel(ModelBase):
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.model = None
        self.tokenizer = None
    
    def load(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer
        self.model = AutoModelForCausalLM.from_pretrained(self.model_id)
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
    
    def generate(self, prompt: str) -> str:
        inputs = self.tokenizer(prompt, return_tensors="pt")
        outputs = self.model.generate(**inputs, max_length=100)
        return self.tokenizer.decode(outputs[0])
```

### Agent Migration Example

**Current (C++):**
```cpp
// agents/AgentBase.cpp
class AgentBase {
    virtual std::string performTask(const std::string& input) = 0;
};
```

**Migrated (Python):**
```python
# versaai/agents/agent_base.py
from abc import ABC, abstractmethod
from versaai_core import Logger  # Use C++ logger!

class AgentBase(ABC):
    def __init__(self):
        self.logger = Logger.get_instance()
    
    @abstractmethod
    def perform_task(self, input: str) -> str:
        pass
    
    def log_operation(self, message: str):
        self.logger.info(message, "Agent")

# versaai/agents/research_agent.py
from langchain.agents import AgentExecutor
from langchain.tools import Tool

class ResearchAgent(AgentBase):
    def __init__(self, model, tools):
        super().__init__()
        self.model = model
        self.tools = tools
    
    def perform_task(self, query: str) -> str:
        self.log_operation(f"ResearchAgent processing: {query}")
        # Use LangChain agent executor
        result = self.agent_executor.run(query)
        self.log_operation(f"ResearchAgent completed: {len(result)} chars")
        return result
```

---

## 🎓 Best Practices

### Python/C++ Boundary

1. **Minimize crossings:** Batch operations when possible
2. **Use native types:** std::string, std::vector map cleanly to Python
3. **Handle exceptions:** Python exceptions should map to C++ exception hierarchy
4. **Memory management:** Use smart pointers (std::shared_ptr) for shared objects

### Performance Optimization

1. **Profile first:** Don't optimize prematurely
2. **Batch operations:** Group multiple calls to reduce overhead
3. **Use C++ for loops:** If iterating millions of times, do it in C++
4. **Release GIL:** Use `py::call_guard<py::gil_scoped_release>()` for long C++ operations

### Code Organization

```
VersaAI/
├── src/core/           # C++ core infrastructure
├── include/            # C++ public headers
├── bindings/           # pybind11 bindings
├── versaai/            # Python package
│   ├── __init__.py
│   ├── models/         # Python model management
│   ├── agents/         # Python agents
│   ├── rag/            # Python RAG system
│   └── tools/          # Python tool integrations
├── scripts/            # Build scripts
└── docs/               # Documentation
```

---

## ✅ Success Criteria

The hybrid architecture is successful when:

1. ✅ Can load **any HuggingFace model** in < 10 lines of Python
2. ✅ Agent development takes **hours, not days**
3. ✅ Performance-critical paths run **within 10% of pure C++**
4. ✅ New team members can contribute **without C++ knowledge** (for agents/models)
5. ✅ Deployment remains **simple** (single binary + Python package)

---

## 🚦 Next Steps

1. **Create pyproject.toml** for Python package management
2. **Implement pybind11 bindings** for existing C++ core
3. **Build proof-of-concept**: Python agent using C++ logger and HuggingFace model
4. **Validate approach** before full migration
5. **Document hybrid development workflow**

---

**Last Updated:** November 14, 2025  
**Status:** Architecture designed, implementation pending  
**Decision:** Pivot to hybrid C++/Python for optimal development velocity and ML ecosystem access
