# VersaGameEngine (VGE) Integration with VersaAI

## Overview
VersaAI provides both chatbot and agent support for VGE, enabling intelligent assistance for game development tasks.

## Components
- **VGEChatbot**: Handles conversational prompts related to game development (e.g., level generation, NPC management).
- **VGEAgent**: Executes specialized tasks (e.g., procedural content generation, scripting behaviors).
- **VGE Models**: (Optional) ML models for advanced tasks (e.g., procedural generation, NPC AI).

## How to Integrate
1. **Register VGEChatbot and VGEAgent** in `VersaAICore` under the "VersaGameEngine" context.
2. **Route user/editor prompts** from VGE to VersaAI using the core API.
3. **Invoke agents** for complex tasks (e.g., `invokeAgent("VersaGameEngine", "generate forest level")`).
4. **Extend** with custom models or additional agents as needed.

## Example Usage
```cpp
// In VGE, to get a conversational response:
std::string response = VersaAICore::getInstance().processInput("VersaGameEngine", "generate level");

// To invoke an agent for a specific task:
std::string result = VersaAICore::getInstance().invokeAgent("VersaGameEngine", "npc patrol");
```

## Best Practices
- Keep VGEChatbot focused on conversational UI, and VGEAgent on task execution.
- Register new models/agents as VGE features expand.
- Document new commands and agent capabilities in the docs folder.
- Use the context/session system for personalized or multi-turn interactions.
