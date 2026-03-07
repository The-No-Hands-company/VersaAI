# VersaAI Architecture

VersaAI is a hierarchical, modular AI ecosystem providing chatbots, agents, and models for VersaOS, VersaModeling, and VersaGameEngine through a unified C++ core.

## 🏰 Architectural Hierarchy

VersaAI follows a **4-layer delegation pattern** from system coordination down to real-world execution:

### 1. The Core: VersaAICore (The System)

- **Role:** Overarching coordination platform managing all functionality across applications
- **Implementation:** Singleton (`VersaAICore::getInstance()`) managing three registries
- **Responsibility:** Routes user input to appropriate chatbots, coordinates agents, manages models

### 2. The Brain: Foundation Models (ModelBase)

- **Role:** Core intelligence providing reasoning and understanding capabilities
- **Implementation:** Models registered via `VersaAIModelRegistry` (see `Model/ModelBase.hpp`)
- **Responsibility:** High-level understanding, strategic planning, raw output generation
- **Note:** Currently infrastructure in place; actual model integration is extensible

### 3. The Workforce: Specialized Agents (AgentBase)

- **Role:** Autonomous entities that break down tasks into executable steps
- **Implementation:** Agent classes (`OSAgent`, `ModelingAgent`, `VGEAgent`) registered per app
- **Responsibility:** Tactical execution, tool selection, context management
- **Key Pattern:** Each agent has dedicated `performTask()` method for domain-specific logic

### 4. The Hands: Tools & Memory

- **Tools:** External capabilities through plugins (Blender, Unity, Unreal) via REST API
  - See `plugins/PLUGIN_API.md` for integration patterns
  - Each plugin in `plugins/` has README with supported commands
- **Memory:** Session/context storage via `VersaAIContext` (key-value store per session)
  - Access via `VersaAICore::getContext(sessionId)`
  - Used by agents to maintain state and retrieve past information

## Component Hierarchy

´´´
VersaAICore (singleton)
├── ModelBase (foundation models)
│   └── Registered via VersaAIModelRegistry
├── ChatbotAI (application interfaces)
│   ├── VersaOSChatbot, VersaModelingChatbot, VGEChatbot
├── AgentBase (specialized workers)
│   ├── OSAgent, ModelingAgent, VGEAgent
│   └── Use Tools + Memory to execute tasks
└── VersaAIContext (memory/session state)
---

## Data Flow

1. User input → `VersaAICore::processInput(appName, input)`
2. Core routes to appropriate `ChatbotAI::getResponse()`
3. Chatbot may invoke `AgentBase::performTask()` for complex operations
4. Agents use `VersaAIContext` (memory) and external Tools (plugins) to execute
5. Results bubble back up through the hierarchy to user

## Core Pattern - Singleton Registry System

- `VersaAICore` manages three registries: chatbots, agents, models
- Each application (VersaOS, VersaModeling, VersaGameEngine) has dedicated chatbot + agent pairs
- Registration happens in `VersaAICore` constructor; extend by adding new app pairs there
