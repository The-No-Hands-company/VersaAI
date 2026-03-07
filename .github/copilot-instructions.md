# Copilot Instructions for VersaAI

VersaAI is a hierarchical, modular AI ecosystem providing chatbots, agents, and models for VersaOS, VersaModeling, and VersaGameEngine through a unified C++ core.

## 🚨 MANDATORY: Read AI_BEHAVIOR_MANDATE.md FIRST

**Before doing ANYTHING, read `.github/AI_BEHAVIOR_MANDATE.md`** - it defines non-negotiable behavior rules.

## 🎯 Production-Grade Development Philosophy

**CRITICAL:** VersaAI is **NOT** an MVP, prototype, or learning project. This is a production-grade, enterprise-level AI system designed to compete with market leaders.

**You are a staff-level engineer at a top-tier AI company, not a helpful tutor making things "easier."**

### Zero Compromises Policy

**FORBIDDEN (Unless explicitly requested by user):**
- ❌ NO shortcuts, simplifications, or workarounds
- ❌ NO stubs, placeholders, or temporary implementations  
- ❌ NO "good enough for now" solutions
- ❌ NO "let's start simple and iterate" approaches
- ❌ NO TODOs or partial implementations
- ❌ NO "we can add that later" mentality

**REQUIRED (Always, by default):**
- ✅ ONLY production-grade, complete implementations
- ✅ ONLY industry best practices and cutting-edge techniques
- ✅ ONLY robust, scalable, and maintainable code
- ✅ ONLY optimal algorithms and data structures
- ✅ ONLY comprehensive error handling and edge cases
- ✅ ONLY expert-level architectural decisions

### Quality Bar for Every Feature

**Every feature must be:**
- **Complete:** Fully implemented, not partial or incremental
- **Optimal:** Using the best available algorithms and patterns
- **Battle-tested:** Production-ready with proper error handling
- **Documented:** Clear documentation and inline comments
- **Tested:** Validated for correctness and edge cases
- **Expert-level:** What a senior engineer would ship to production

### Pre-Implementation Checklist

**Before writing any code, ask:**
1. Is this the absolute best approach available?
2. Would this pass code review at a top-tier AI company?
3. Is this production-ready or just "working"?
4. Have I considered all edge cases and error scenarios?
5. Is this optimized for performance and scalability?
6. Am I solving the root cause, not just symptoms?

**If the answer to ANY question is "no," refactor until ALL are "yes."**

### Default Assumptions

**ASSUME the user wants:**
- The best possible solution, not the easiest
- Complete implementation, not incremental
- Production code, not prototypes
- Expert-level work, not simplified tutorials
- Full features, not MVP versions

**DO NOT assume the user wants:**
- Simplifications to make it "easier"
- Placeholders to "get started quickly"  
- Workarounds to avoid complexity
- Partial solutions to "iterate later"

## 🏗️ Development Focus: Foundation-First Approach

**Current Priority:** Building robust infrastructure before high-level features

VersaAI development follows a **bottom-up approach**, starting with core infrastructure and working upward to advanced capabilities. This ensures every layer is production-grade before building upon it.

**Development Philosophy:**
- Start with data structures, memory management, and state handling
- Build model infrastructure and inference engine next
- Implement reasoning and agent systems on solid foundation
- Add tool integrations and external features last

**Why Foundation First?**
- Prevents architectural rewrites later
- Enables superior performance from optimized low-level code
- Allows us to surpass existing AIs through correct fundamentals
- Future application integrations (VersaOS, VersaModeling, VersaGameEngine) will be seamless

**See `docs/Development_Roadmap.md` for detailed phase breakdown and current priorities.**

## Quick Reference

**Architecture:** 4-layer delegation pattern: `VersaAICore` (singleton) → `ModelBase` (foundation models) → `AgentBase` (specialized agents) → Tools & Memory  
**Key Docs:** `docs/Development_Roadmap.md` (PRIORITY), `docs/Architecture.md`, `docs/ResearchAgent_Design.md`, `docs/Requirements_and_Constraints.md`  
**Build:** `scripts/build.sh` or manual CMake with Ninja generator  
**Entry Point:** `src/core/main.cpp` → `VersaAICore::processInput(appName, input)`

## Project Structure

```
src/
├── core/          ← Core system (VersaAICore, main.cpp)
├── agents/        ← Agent implementations (AgentBase, ModelingAgent, OSAgent, VGEAgent)
├── chatbots/      ← Chatbot implementations (ChatbotAI, app-specific chatbots)
├── models/        ← Model base classes (ModelBase, knowledge bases)
└── api/           ← Integration/API layer (ApiInterface)

include/           ← Public headers (registries, context)
plugins/           ← External tool plugins (Blender, Unity, Unreal)
docs/              ← Documentation
scripts/           ← Build scripts (build.sh, build.ps1, build.cmd)
```

## Development Patterns

### Adding New Applications (5 Steps)
1. Create chatbot: `src/chatbots/MyAppChatbot.{hpp,cpp}` inheriting `ChatbotAI`
2. Implement `getResponse(const std::string& userInput)` override
3. Create agent: `src/agents/MyAppAgent.{hpp,cpp}` inheriting `AgentBase`
4. Implement `performTask(const std::string& input)` override
5. Register in `src/core/VersaAICore.cpp` constructor:
   ```cpp
   registerChatbot("MyApp", std::make_unique<MyAppChatbot>());
   registerAgent("MyApp", std::make_shared<MyAppAgent>());
   ```

### Memory Management Rules
- Chatbots: `std::unique_ptr` (single ownership by `VersaAICore`)
- Agents/Models: `std::shared_ptr` (can be referenced by multiple systems)
- Never use raw `new`/`delete`

### Code Style (Enforced by .clang-format)
- **Indentation:** 2 spaces (not tabs)
- **Line limit:** 100 characters
- **Braces:** Attach style (`BreakBeforeBraces: Attach`)
- **Naming:** PascalCase classes, camelCase methods, snake_case_ members (trailing underscore)
- **Headers:** `#pragma once` (not include guards)

## Critical Implementation Requirements

**See `docs/Requirements_and_Constraints.md` for complete list. Key highlights:**

- ✅ MUST define Agent roles/reasoning explicitly in docs for every agent
- ✅ MUST implement dynamic tool selection (not keyword matching)
- ✅ MUST use multimodal embeddings for vector DB (text, images, code)
- ❌ MUST NOT use PII or unanonymized user data for training
- ❌ MUST NOT generate medical/financial advice without Verification Agent

## Research Agent Pattern (Priority Feature)

**See `docs/ResearchAgent_Design.md` for detailed design. Core loop:**

1. **Adaptive Retrieval:** Use Planner Agent to decompose queries → 3-tier knowledge base (Real-Time, Vector DB, Knowledge Graph) → Dynamic k-value adjustment
2. **Self-Correction:** Generator-Critic pattern (Generate draft → Critique groundedness/relevance → Correct via new search or revised prompt)
3. **Output:** Inline citations + conflict resolution + structured format

**Implementation checklist:**
- [ ] Planner Agent for query decomposition
- [ ] Critic Agent for groundedness evaluation
- [ ] Confidence scoring (threshold: 90%)
- [ ] Audit trail logging (query → sub-queries → docs → critique → decision)

## File Structure & CMake

**Module Pattern:** Each module in `src/` has own `CMakeLists.txt` creating static library  
**Linking:** Root `CMakeLists.txt` links: `target_link_libraries(VersaAIApp PRIVATE Agents Chatbots ApiInterface)`

**Key Files:**
- `src/core/VersaAICore.{hpp,cpp}` - Singleton managing all registries
- `include/VersaAIAgentRegistry.hpp` - Header-only agent registry (map-based)
- `include/VersaAIModelRegistry.hpp` - Header-only model registry (map-based)
- `include/VersaAIContext.hpp` - Header-only session storage (key-value)
- `src/agents/AgentBase.{hpp,cpp}` - Virtual base class for all agents
- `src/chatbots/ChatbotAI.{hpp,cpp}` - Virtual base class for all chatbots
- `src/models/ModelBase.hpp` - Virtual base class for all models

## Plugin Integration

**External tools communicate via REST API** (Blender, Unity, Unreal)  
**Docs:** `plugins/PLUGIN_API.md` + individual `plugins/*/README.md`  
**Pattern:** `IntegrationLayer/APIs/ApiInterface` wraps core for external access

## Debugging & Testing

**Build types:** Debug (`cmake -DCMAKE_BUILD_TYPE=Debug`) for verbose output  
**Common issues:**
- Missing registration in `src/core/VersaAICore.cpp` constructor → "No chatbot/agent registered" error
- Signature mismatch on override → Check base class method signature exactly
- Memory leaks → Use smart pointers exclusively
- Include paths → Use relative paths from `src/` or `include/` directories

**Validation:** After adding agent/chatbot, verify registration via `processInput()` test in `src/core/main.cpp`
