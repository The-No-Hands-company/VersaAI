# VersaAICore: Central AI System Manager

`VersaAICore` is the central manager for all AI components in VersaAI. It handles:

- Registration and management of chatbots for each application.
- Routing user input to the correct chatbot based on app context.
- Unified API for all VersaAI-enabled software.

## Usage
- Register new chatbots with `registerChatbot(appName, chatbot)`.
- Process input for any app with `processInput(appName, userInput)`.
- Easily extend to manage agents, models, and more.

## Example
```cpp
#include "VersaAICore.hpp"

std::string response = VersaAICore::getInstance().processInput("VersaModeling", "generate cube");
```

## Extending
- Add agent/model management as needed.
- Integrate with APIs or SDKs for your software ecosystem.

## Benefits
- Centralized control and configuration.
- Consistent AI experience across all applications.
- Easy to extend and maintain.
