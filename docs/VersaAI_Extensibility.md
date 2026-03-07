# VersaAI Extensibility Guide

This document explains how to extend VersaAI with new agents, models, and context/session features.

## Adding a New Agent
1. Create a new class inheriting from `AgentBase` in the `Agents` folder.
2. Implement the `performTask` method.
3. Register the agent in `VersaAICore` using `registerAgent(appName, agent)`.

## Adding a New Model
1. Create a new class inheriting from `ModelBase` in the `Model` folder.
2. Register the model in `VersaAICore` using `registerModel(name, model)`.
3. Retrieve and use models as needed in chatbots or agents.

## Using Context/Session
- Use `VersaAIContext` to store and retrieve session/user data.
- Access context via `VersaAICore::getContext(sessionId)`.

## API Layer
- Expose C++ interfaces for all core features.
- For REST/gRPC, wrap core APIs in a service layer (see IntegrationLayer/APIs).

## Example
```cpp
// Registering an agent
VersaAICore::getInstance().registerAgent("VersaModeling", std::make_shared<ModelingAgent>());

// Registering a model
VersaAICore::getInstance().registerModel("MyModel", std::make_shared<MyModel>());

// Using context
VersaAICore::getInstance().getContext("user123").set("lastCommand", "help");
```
