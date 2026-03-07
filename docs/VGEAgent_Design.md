# VGEAgent Design: From Prompt to Game Engine Action

## Flow Overview
1. **Prompt Parsing**: VGEAgent uses `VGEIntentParser` to convert user prompts into structured tasks (`VGETask`).
2. **Task Execution**: VGEAgent interprets the task and calls the appropriate game engine APIs or scripts.
3. **Result Feedback**: The agent returns a result or status to the user/editor.

## Example
```cpp
std::string prompt = "generate forest level";
std::string result = VersaAICore::getInstance().invokeAgent("VersaGameEngine", prompt);
// result: [Agent] Forest level with 10 enemies generated.
```

## Extending
- Improve `VGEIntentParser` with NLP/ML for richer intent extraction.
- Expand `VGETask` to support more parameters and task types.
- Connect `executeTask` to real game engine APIs for actual content generation.
- Add error handling and feedback for unsupported or ambiguous prompts.

## Best Practices
- Keep parsing and execution logic modular.
- Document new task types and engine API integrations.
- Use context/session for multi-step workflows.
