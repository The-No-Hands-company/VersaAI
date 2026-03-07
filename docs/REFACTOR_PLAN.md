# VersaAI Complete Refactoring Plan

**Date:** 2026-03-06 (Revised)  
**Goal:** Consolidate and ship VersaAI as a working, production-grade AI ecosystem  

---

## 1. Honest Assessment: Where We Are

The project has TWO codebases that were never properly integrated:

### A) C++ Layer (~14,660 lines) — Infrastructure, No AI

| Component | Lines | Quality | Notes |
|-----------|-------|---------|-------|
| VersaAILogger | ~470 | **Production** | Async, batched, thread-safe, multi-sink |
| VersaAIException | ~610 | **Production** | Full hierarchy, stack traces, chaining |
| VersaAIErrorRecovery | ~600 | **Production** | Retry, fallback, circuit breaker |
| VersaAIMemoryPool | ~464 | **Production** | Arena/pool/slab allocators (header-only) |
| VersaAIDependencyInjection | ~542 | **Production** | IoC container, lifecycle management |
| VersaAIRegistry | ~529 | **Production** | Type-erased service registry |
| Model Loaders (GGUF/ONNX/SafeTensors) | ~1,750 | **80% Complete** | Parse metadata but never load for inference |
| VersaAITensor | ~695 | **Functional** | Basic ops, no SIMD/BLAS — testing only |
| C++ Chatbots/Agents | ~700 | **Stubs** | Hardcoded string matching, no model behind them |

### B) Python Layer (~15,170 lines) — Substantial, Partly Working

| Component | Lines | Quality | Notes |
|-----------|-------|---------|-------|
| CLI (`cli.py`) | 765 | **Production** | Full REPL with rich UI, commands, model selection |
| Model Providers (`code_llm.py`) | 711 | **Partial** | llama.cpp, HF, OpenAI, Anthropic — 2 bugs |
| GGUF Model (`gguf_model.py`) | 290 | **Production** | Full llama-cpp-python wrapper |
| HuggingFace Model (`huggingface_model.py`) | 328 | **Production** | Full HF wrapper with quantization |
| Model Router (`model_router.py`) | 639 | **Partial** | Task-based scoring, generation has fallback |
| Multi-Model Manager | 460 | **Partial** | GGUF auto-detection, RAM tracking |
| RAG Pipeline (`pipeline.py`) | 615 | **Production** | Full orchestration, NOT connected to `rag_system.py` |  
| RAG Embeddings | 259 | **Production** | sentence-transformers wrapper |
| RAG Retriever | 610 | **Partial** | Dense/sparse/hybrid, BM25 path broken |
| RAG Query Decomposer | 489 | **Production** | Heuristic + LLM modes |
| RAG Planner | 668 | **Production** | Heuristic + LLM modes |
| RAG Critic | 725 | **Production** | 7-dimension quality assessment |
| Memory: Conversation | 446 | **Partial** | Multi-turn, heuristic entity extraction |
| Memory: Vector DB | 450 | **Production** | ChromaDB + FAISS — **DUPLICATE** of `rag/vector_store.py` |
| Memory: Knowledge Graph | 539 | **Production** | Entity-relationship graph, temporal reasoning |
| Memory: Episodic | 559 | **Partial** | Integrates VectorDB + KG, placeholder embeddings |
| Memory: Context Window | 537 | **Partial** | Priority truncation, heuristic token counting |
| Memory: State | 431 | **Production** | Session persistence, auto-backup |
| Coding Agent | 285 | **Partial** | LLM + streaming + file tools, brittle parsing |
| Research Agent | 310 | **Partial** | RAG + self-correction, mock retrieval |
| Reasoning Engine | 420 | **Partial** | CoT, ReAct, ToT strategies — placeholder LLM |
| Planning System | 510 | **Partial** | Goal decomposition, template-based |
| Code Model (`code_model.py`) | 672 | **Partial** | Orchestration skeleton, many stub helpers |
| Editor Bridge Server | 290 | **Production** | WebSocket server, async message routing |
| Editor Chat Service | 404 | **Production** | Multi-session, file-context-aware |
| Editor Completion | 220 | **Partial** | FIM support, depends on model router |
| Flutter UI | ~2,900 | **Functional** | Full chat app, WebSocket client |

### Key Problems Preventing This From Working

1. **Two disconnected worlds**: C++ chatbots/agents exist alongside Python agents. Neither works end-to-end.
2. **Duplicate implementations**: `memory/vector_db.py` vs `rag/vector_store.py` (near-identical)
3. **Disconnected RAG**: `rag_system.py` (73-line stub) ≠ `rag/pipeline.py` (615-line production code)
4. **Bugs in `code_llm.py`**: Duplicate `@abstractmethod`, Anthropic `yield from` in non-generator
5. **`code_model.py` stubs**: `_extract_key_concepts` returns `["concept1", "concept2"]`, etc.
6. **No FastAPI server**: Only WebSocket bridge (editors) — no REST API for CLI/desktop/web
7. **`reasoning.py` placeholder LLM**: All reasoning strategies produce `"[LLM response to: ...]"`
8. **C++ infra underutilized**: Python has fallback for everything C++ provides — the .so binding barely used

---

## 2. The Vision: What VersaAI Should Be

VersaAI is an **AI orchestration platform** — not a model trainer, not a framework reimplementing PyTorch. It's the brain that:

1. **Routes** user requests to the right model (local or API-based)
2. **Orchestrates** multi-step tasks through specialized agents
3. **Remembers** context across sessions through RAG and memory
4. **Integrates** with development tools (IDEs, Blender, Unity, game engines)
5. **Serves** multiple interfaces (CLI, desktop app, web, API)

### What Makes VersaAI Different from Just Using ChatGPT

- **Local-first**: Run models on your hardware, no data leaves your machine unless you choose
- **Development-specialized**: Agents understand YOUR codebase, YOUR projects, YOUR workflows
- **Multi-model**: Route to the best model per task (code → CodeLlama, general → Mistral, images → SD)
- **Persistent memory**: Knows your project history, preferences, coding patterns
- **Tool-integrated**: Can actually execute code, manipulate files, control dev tools
- **No Hands Company ecosystem**: Native integration with VersaOS, VersaModeling, VersaGameEngine

### Industry Reality Check

What Google/Anthropic/OpenAI have that we leverage, not rebuild:
- **Foundation models**: We use open-source models (LLaMA, Mistral, Phi, Qwen) + API models
- **Inference engines**: We integrate llama.cpp + Ollama rather than rewrite inference
- **Tokenizers**: We use SentencePiece/tiktoken rather than rewrite BPE
- **Embeddings**: We use sentence-transformers or local embedding models
- **GPU kernels**: llama.cpp handles CUDA/ROCm/Metal/Vulkan

What we BUILD that makes VersaAI unique:
- **Orchestration layer**: Model routing, agent coordination, memory management
- **Agent framework**: Specialized agents with tool use and reasoning
- **RAG pipeline**: Project-aware retrieval over your codebase and docs
- **Integration layer**: Connects to your actual development tools
- **UI/UX**: Tailored interfaces for development workflows

### What We Already Have (Leverage!)
The Python codebase already includes functional implementations of:
- CLI with rich UI and REPL (765 lines)
- 4 model providers (llama.cpp, HuggingFace, OpenAI, Anthropic)
- RAG pipeline components (decomposer, planner, retriever, critic, embeddings)  
- Memory system (conversation, vector DB, knowledge graph, episodic, state)
- Agent framework (coding, research, reasoning, planning)
- Editor bridge (WebSocket server, chat, completions)

**The refactoring is NOT a rewrite — it's a consolidation and connection of existing parts.**

---

## 3. New Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌─────────┐  ┌──────────────┐  ┌──────────────────┐           │
│  │   CLI   │  │ Tauri Desktop│  │  Editor Plugins  │           │
│  │ (Python)│  │ (Rust + Web) │  │ (VS Code, NLPL)  │           │
│  └────┬────┘  └──────┬───────┘  └────────┬─────────┘           │
└───────┼──────────────┼───────────────────┼──────────────────────┘
        │              │                   │
        └──────────────┴────────┬──────────┘
                                │ HTTP/SSE/WebSocket
┌───────────────────────────────▼─────────────────────────────────┐
│                      API GATEWAY (FastAPI)                        │
│  /v1/chat/completions (OpenAI-compatible)                        │
│  /v1/models, /v1/agents, /v1/rag, /v1/memory                   │
│  SSE streaming, auth, rate limiting, middleware logging          │
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                  ORCHESTRATION (Python — existing + cleaned up)   │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Router / Dispatcher                      │ │
│  │  model_router.py + multi_model_manager.py (existing)       │ │
│  └────────────────────────────┬───────────────────────────────┘ │
│                               │                                  │
│  ┌──────────────┐  ┌─────────▼────────┐  ┌──────────────────┐  │
│  │ Conversation │  │   Agent Engine   │  │   RAG Pipeline   │  │
│  │ (existing)   │  │   (existing)     │  │   (existing)     │  │
│  │              │  │                   │  │                   │  │
│  │ conversation │  │ CodingAgent      │  │ pipeline.py      │  │
│  │ context_win  │  │ ResearchAgent    │  │ retriever.py     │  │
│  │ state.py     │  │ reasoning.py     │  │ embeddings.py    │  │
│  │              │  │ planning.py      │  │ critic.py        │  │
│  └──────────────┘  └──────────────────┘  │ decomposer.py   │  │
│                                           │ planner.py       │  │
│  ┌─────────────────────────────────────┐  └──────────────────┘  │
│  │            Memory Layer             │                         │
│  │ vector_db.py (MERGED), knowledge_   │                         │
│  │ graph.py, episodic.py, state.py     │                         │
│  └─────────────────────────────────────┘                         │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    Tool Framework (NEW)                      ││
│  │ file_ops, shell, web_search, code_exec, git_ops             ││
│  └─────────────────────────────────────────────────────────────┘│
└───────────────────────────────┬─────────────────────────────────┘
                                │
┌───────────────────────────────▼─────────────────────────────────┐
│                    MODEL LAYER (existing + Ollama)                │
│                                                                  │
│  ┌──────────────────┐┌────────────────┐┌──────────────────────┐ │
│  │  Local Models    ││  API Models    ││  Embedding Models    │ │
│  │                  ││                ││                       │ │
│  │ gguf_model.py    ││ code_llm.py   ││ embeddings.py         │ │
│  │ (llama-cpp-py)   ││ (OpenAI)      ││ (sentence-transform.) │ │
│  │ + NEW: Ollama    ││ (Anthropic)   ││                       │ │
│  │ huggingface.py   ││ (HuggingFace) ││                       │ │
│  └──────────────────┘└────────────────┘└──────────────────────┘ │
└───────────────────────────────┬─────────────────────────────────┘
                                │ (optional pybind11)
┌───────────────────────────────▼─────────────────────────────────┐
│              C++ INFRASTRUCTURE (existing, archived)              │
│  Logger, Exceptions, ErrorRecovery, MemoryPool, DI, ModelLoaders │
│  (Available via pybind11 but Python has fallbacks for everything) │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. New Project Structure

```
VersaAI/
├── pyproject.toml              ← Python project config (uv)
├── README.md
├── .env.example                ← Configuration template
├── Makefile                    ← Top-level orchestration (dev, test, serve, build)
│
├── versaai/                    ← Main Python package (EXISTING, reorganized)
│   ├── __init__.py
│   │
│   ├── api/                    ← API Gateway (NEW — FastAPI)
│   │   ├── __init__.py
│   │   ├── app.py              ← FastAPI app, CORS, middleware, lifespan
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py         ← /v1/chat/completions (OpenAI-compatible, SSE)
│   │   │   ├── models.py       ← /v1/models (list, load, unload, info)
│   │   │   ├── agents.py       ← /v1/agents (execute tasks)
│   │   │   └── health.py       ← /health, /version
│   │   └── schemas.py          ← Pydantic request/response models
│   │
│   ├── core/                   ← Core Orchestration (EXISTING core.py → expanded)
│   │   ├── __init__.py
│   │   ├── config.py           ← Centralized config (YAML + env + Pydantic)
│   │   ├── router.py           ← Intent → model/agent dispatch
│   │   ├── conversation.py     ← conversation.py (from memory/, MOVED)
│   │   └── events.py           ← Event bus for component communication
│   │
│   ├── models/                 ← Model Management (EXISTING, cleaned up)
│   │   ├── __init__.py
│   │   ├── registry.py         ← model_registry.py (EXISTING, fixed)
│   │   ├── router.py           ← model_router.py (EXISTING)
│   │   ├── multi_model.py      ← multi_model_manager.py (EXISTING)
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py         ← CodeLLMBase from code_llm.py (EXISTING, fixed)
│   │   │   ├── llamacpp.py     ← LlamaCppCodeLLM (EXISTING)
│   │   │   ├── huggingface.py  ← huggingface_model.py (EXISTING)
│   │   │   ├── openai.py       ← OpenAICodeLLM (EXISTING, fixed)
│   │   │   ├── anthropic.py    ← AnthropicCodeLLM (EXISTING, fixed)
│   │   │   └── ollama.py       ← NEW — Ollama HTTP API client
│   │   └── gguf.py             ← gguf_model.py (EXISTING)
│   │
│   ├── agents/                 ← Agent Framework (EXISTING, wired to real LLMs)
│   │   ├── __init__.py
│   │   ├── base.py             ← agent_base.py (EXISTING)
│   │   ├── engine.py           ← Agent execution engine (NEW)
│   │   ├── coding.py           ← coding_agent.py (EXISTING, improved)
│   │   ├── research.py         ← research_agent.py (EXISTING, connected to RAG)
│   │   ├── reasoning.py        ← reasoning.py (EXISTING, wired to LLMs)
│   │   ├── planning.py         ← planning.py (EXISTING)
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── base.py         ← Tool interface (NEW)
│   │       ├── file_ops.py     ← File read/write/search (NEW)
│   │       ├── shell.py        ← Command execution (NEW)
│   │       └── web_search.py   ← Web search (NEW)
│   │
│   ├── memory/                 ← Memory & RAG (EXISTING, consolidated)
│   │   ├── __init__.py
│   │   ├── vector_store.py     ← MERGED vector_db.py + rag/vector_store.py
│   │   ├── knowledge_graph.py  ← knowledge_graph.py (EXISTING)
│   │   ├── episodic.py         ← episodic.py (EXISTING)
│   │   ├── state.py            ← state.py (EXISTING)
│   │   └── context_window.py   ← context_window.py (EXISTING)
│   │
│   ├── rag/                    ← RAG Pipeline (EXISTING, connected)
│   │   ├── __init__.py
│   │   ├── pipeline.py         ← pipeline.py (EXISTING — THE REAL ONE)
│   │   ├── embeddings.py       ← embeddings.py (EXISTING)
│   │   ├── retriever.py        ← retriever.py (EXISTING)
│   │   ├── decomposer.py       ← query_decomposer.py (EXISTING)
│   │   ├── planner.py          ← planner.py (EXISTING)
│   │   └── critic.py           ← critic.py (EXISTING)
│   │
│   ├── cli/                    ← CLI Client (EXISTING cli.py → package)
│   │   ├── __init__.py
│   │   └── main.py             ← cli.py (EXISTING, updated to use FastAPI)
│   │
│   └── editor/                 ← Editor Bridge (EXISTING, kept)
│       ├── __init__.py
│       ├── server.py           ← WebSocket server (EXISTING)
│       ├── chat.py             ← chat_service.py (EXISTING)
│       └── completions.py      ← completion_service.py (EXISTING)
│
├── ui/                         ← Desktop Application
│   └── tauri/                  ← Tauri app (NEW — replaces Flutter)
│       ├── src-tauri/          ← Rust backend
│       ├── src/                ← Web frontend (React/SvelteKit)
│       └── package.json
│
├── infra/                      ← C++ Infrastructure (EXISTING, archived)
│   ├── CMakeLists.txt
│   ├── include/                ← Headers (existing, cleaned filenames)
│   ├── src/                    ← Implementations (existing)
│   └── bindings/               ← Single pybind11 module
│       └── py_infra.cpp
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── models/                     ← Local model storage (gitignored)
├── data/                       ← Vector DB, caches (gitignored)
│
├── config/
│   ├── default.yaml            ← Default configuration
│   └── models.yaml             ← Model catalog
│
├── docs/
│   ├── REFACTOR_PLAN.md        ← This document
│   ├── architecture.md
│   └── api_reference.md
│
└── scripts/
    ├── setup.sh                ← One-command project setup
    ├── dev.sh                  ← Start development environment
    └── download_model.sh       ← Download recommended models
```

**Key insight: ~80% of the files ALREADY EXIST.** The refactoring is mostly:
1. Moving files to cleaner locations
2. Fixing bugs in existing code
3. Merging duplicates
4. Adding FastAPI server (NEW)
5. Adding Ollama provider (NEW)
6. Adding Tauri desktop app (NEW)
7. Connecting disconnected components

---

## 5. Technology Decisions

### Why This Stack

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Primary Language** | Python | ML ecosystem, rapid development, 90% of AI tooling is Python |
| **Performance Layer** | C++ (existing) | Keep the good infrastructure, expose via pybind11 |
| **API Framework** | FastAPI | Async, streaming SSE, auto-docs, type-safe |
| **Local Inference** | llama.cpp (via llama-cpp-python or server mode) | Best GGUF performance, active community, GPU support |
| **Vector DB** | ChromaDB (start) → Qdrant (scale) | ChromaDB is simple + embedded; Qdrant for production |
| **Embeddings** | sentence-transformers or local GGUF | Local-first for privacy |
| **Configuration** | YAML + Pydantic | Human-readable config, validated at startup |
| **CLI** | Rich + Textual (Python) | Beautiful terminal UI, streaming support |
| **Testing** | pytest + pytest-asyncio | Standard Python testing |
| **Package Manager** | uv | Fast, reliable, modern Python packaging |

### What We DON'T Build
- ❌ Custom inference engine (use llama.cpp / vLLM / Ollama)
- ❌ Custom tokenizer (use model's built-in via llama.cpp)
- ❌ Custom GPU kernels (llama.cpp handles CUDA/ROCm/Metal/Vulkan)
- ❌ Custom tensor library (use existing inference backends)
- ❌ Model training pipeline (use existing tools, fine-tune with LoRA externally)

### What We DO Build
- ✅ Intelligent model routing (task → best available model)
- ✅ Agent framework with tool use and reasoning
- ✅ RAG pipeline over codebases and documentation
- ✅ Conversation memory and context management
- ✅ Multi-provider model support (local + API)
- ✅ Beautiful CLI and desktop interfaces
- ✅ Development-focused tools and integrations
- ✅ Plugin system for external tool integration

---

## 6. Phased Implementation Roadmap

### Phase 0: Consolidation & E2E Chat (Week 1-2)
**Goal:** Clean project structure + working chat via FastAPI

- [ ] Reorganize `versaai/` package to new structure (move files, update imports)
- [ ] Fix `code_llm.py` bugs (duplicate @abstractmethod, Anthropic yield)
- [ ] Merge `memory/vector_db.py` + `rag/vector_store.py` into single `memory/vector_store.py`
- [ ] Delete `rag/rag_system.py` stub — `rag/pipeline.py` IS the RAG system
- [ ] Replace stubs in `code_model.py` with real implementations
- [ ] Create `config/default.yaml` + `versaai/core/config.py` (Pydantic Settings)
- [ ] Add Ollama provider (`versaai/models/providers/ollama.py`)
- [ ] Create FastAPI server with `/v1/chat/completions` (OpenAI-compatible, SSE streaming)
- [ ] Update `pyproject.toml` with proper deps (drop unused, add FastAPI/uvicorn)
- [ ] Wire CLI to use FastAPI server (or direct model providers for offline mode)
- [ ] Create `Makefile` with `dev`, `serve`, `test`, `setup` targets
- [ ] **Milestone:** `make serve` + `curl /v1/chat/completions` returns streamed AI response

### Phase 1: Wire Agents to Real LLMs (Week 3-4)
**Goal:** Agents that use actual models, not placeholder strings

- [ ] Wire `reasoning.py` to use real LLM via model providers
- [ ] Connect `research_agent.py` to `rag/pipeline.py` (not stub `rag_system.py`)
- [ ] Improve `coding_agent.py` file parsing (use AST, not fragile regex)
- [ ] Build tool framework base (`agents/tools/base.py`)
- [ ] Implement file operations tool
- [ ] Implement shell execution tool (sandboxed)
- [ ] Add agent endpoints to FastAPI (`/v1/agents`)
- [ ] **Milestone:** Ask "refactor this function" → agent reads file, generates improved code

### Phase 2: RAG & Project Understanding (Week 5-6)
**Goal:** VersaAI understands YOUR codebase

- [ ] Build codebase indexer (walks project, chunks files, generates embeddings)
- [ ] Fix BM25 retriever path (maintain separate document index)
- [ ] Connect episodic memory to real embedding function
- [ ] Add `/v1/rag/index` endpoint (index a project directory)
- [ ] Add `/v1/rag/query` endpoint (query indexed codebase)
- [ ] Integrate RAG context into chat completions automatically
- [ ] **Milestone:** Ask "how does authentication work?" in your project → accurate answer with file references

### Phase 3: Tauri Desktop App (Week 7-9)
**Goal:** Native desktop AI assistant

- [ ] Initialize Tauri project with SvelteKit frontend
- [ ] Chat interface with streaming markdown rendering
- [ ] Model selection and download UI
- [ ] Conversation history sidebar
- [ ] System tray with quick-chat popup
- [ ] Settings panel (model config, API keys, appearance)
- [ ] Connect to FastAPI backend
- [ ] **Milestone:** Beautiful desktop app with full chat + model management

### Phase 4: Development Integration (Week 10-12)
**Goal:** Deep integration with development workflows

- [ ] VS Code extension (chat panel, inline suggestions)
- [ ] Git-aware context (current branch, recent changes)
- [ ] Project-aware agents (understands project type, build system, deps)
- [ ] Code review agent (git diff → review comments)
- [ ] Web search tool integration
- [ ] **Milestone:** VersaAI is actively useful in daily development

### Phase 5: Ecosystem & Scale (Week 13+)
**Goal:** Full ecosystem integration

- [ ] Image generation model support (Stable Diffusion, FLUX)
- [ ] Blender/Unity/Unreal plugin integration
- [ ] Multi-user support
- [ ] Fine-tuning pipeline (LoRA on your code/data)
- [ ] VersaOS, VersaModeling, VersaGameEngine integration

---

## 7. What Happens to Existing Code

### Python — Keep & Reorganize (~90% of files stay)
| File(s) | Action | Notes |
|---------|--------|-------|
| `versaai/cli.py` | Move to `versaai/cli/main.py` | Update imports |
| `versaai/models/*.py` | Move to `versaai/models/providers/` | Split `code_llm.py` into separate providers |
| `versaai/agents/*.py` | Keep, rename | Wire to real LLMs |
| `versaai/memory/*.py` | Keep | Merge `vector_db.py` into `vector_store.py` |
| `versaai/rag/*.py` | Keep | Delete `rag_system.py` stub |
| `versaai/code_editor_bridge/` | Move to `versaai/editor/` | Keep content |
| `versaai/core.py` | Expand into `versaai/core/` package | Add config, router, events |

### Python — Delete
| File(s) | Reason |
|---------|--------|
| `versaai/rag/rag_system.py` | 73-line stub; `pipeline.py` is the real implementation |
| `versaai/memory/vector_db.py` | Duplicate of `rag/vector_store.py` — merge into one |
| `versaai/models/code_model.py` | 672 lines of orchestration with stub helpers — functionality distributed to agents/core |
| `versaai/models/model_ensemble.py` | Placeholder generation — revisit when needed |
| Root test/verify scripts | Move useful ones to `tests/`, delete rest |

### C++ — Archive
| File(s) | Action |
|---------|--------|
| `src/core/VersaAILogger.*` | Move to `infra/` |
| `src/core/VersaAIException.*` | Move to `infra/` |
| `src/core/VersaAIErrorRecovery.*` | Move to `infra/` |
| `include/VersaAIMemoryPool.hpp` | Move to `infra/include/` |
| `include/VersaAIDependencyInjection.hpp` | Move to `infra/include/` |
| `src/models/*Loader*` | Move to `infra/src/` |
| `src/agents/` (C++) | Delete — replaced by Python agents |
| `src/chatbots/` (C++) | Delete — replaced by Python API |
| `src/api/` (C++) | Delete (20 lines, useless) |
| `src/core/main.cpp` | Delete — replaced by Python CLI + FastAPI |
| `src/core/BehaviorPolicy.*` | Delete — regex text linter, not needed |
| `src/core/VersaAITensor.*` | Delete — not needed with llama.cpp inference |
| `bindings/` (6+ redundant files) | Consolidate to single `infra/bindings/py_infra.cpp` |
| `include/VersaAIInferenceEngine.hpp` | Delete — empty interface |
| `include/VersaAITokenizer.hpp` | Delete — empty interface |
| `include/VersaAIGPUAccelerator.hpp` | Delete — empty interface |

### Other
| Item | Action |
|------|--------|
| `ui/` (Flutter) | Archive — replaced by Tauri |
| `docs/` (60+ files) | Keep relevant ones, archive the rest |
| Root-level test/verify scripts | Consolidate into `tests/` |

---

## 8. Key Architectural Principles

1. **End-to-End First:** Get one complete path working before expanding
2. **Orchestrate, Don't Reinvent:** Use existing inference engines, don't build one
3. **Local-First, Cloud-Optional:** Everything works offline; API models are optional
4. **Python for Logic, C++ for Speed:** Python orchestration, C++ only where measurably needed
5. **Configuration-Driven:** Models, agents, tools defined in YAML, not hardcoded
6. **Streaming by Default:** All responses stream, never block waiting for full completion
7. **Test from Day One:** Every component has tests, E2E tests validate the full pipeline
8. **Single Source of Truth:** One model registry, one config system, no duplicate definitions

---

## 9. Success Metrics

### Phase 0 Complete When:
- `versa chat "Hello"` returns a streamed response from a local model
- Response time < 500ms to first token
- Works completely offline

### Phase 2 Complete When:
- Can ask "refactor this function" and get working, improved code back
- Agent correctly uses file system tools to read/write code

### Phase 3 Complete When:
- Can ask "how does the authentication system work?" about YOUR project
- Gets accurate answer with file references

### Phase 5 Complete When:
- VersaAI is the primary AI assistant used in daily development
- Replaces manual ChatGPT/Claude usage for development tasks

---

## 10. Decision Points Needed

Before starting implementation, we need alignment on:

1. **Package manager:** uv (recommended) vs poetry vs pip
2. **Local inference:** llama.cpp server (recommended) vs Ollama vs direct binding
3. **Starting model:** Qwen2.5-Coder-7B (recommended for code) + Mistral-7B (general)
4. **Vector DB:** ChromaDB (recommended, embedded) vs Qdrant vs Milvus
5. **Keep Flutter UI?** Or switch to Tauri/Electron for tighter Python integration?
6. **Archive strategy:** Git branch vs separate archive folder vs delete

This plan transforms VersaAI from "14,660 lines of mostly infrastructure with no AI" into "a working AI assistant that grows into a full ecosystem."
