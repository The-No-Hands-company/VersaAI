#pragma once
#include <string>
#include <memory>
#include <unordered_map>
#include "chatbots/ChatbotAI.hpp"
#include "chatbots/VersaOSChatbot.hpp"
#include "chatbots/VersaModelingChatbot.hpp"
#include "VersaAIAgentRegistry.hpp"
#include "VersaAIModel.hpp"
#include "VersaAIModelRegistry.hpp"
#include "VersaAIContext.hpp"

class VersaAICore {
public:
    static VersaAICore& getInstance();

    // Register a chatbot for an app
    void registerChatbot(const std::string& appName, std::unique_ptr<ChatbotAI> chatbot);

    // Process input for a given app
    std::string processInput(const std::string& appName, const std::string& userInput);

    // Agent management
    void registerAgent(const std::string& appName, std::shared_ptr<AgentBase> agent);
    std::string invokeAgent(const std::string& appName, const std::string& input);

    // Model management
    void registerModel(const std::string& name, std::shared_ptr<VersaAI::ModelBase> model);
    std::shared_ptr<VersaAI::ModelBase> getModel(const std::string& name) const;

    // Context management
    VersaAIContext& getContext(const std::string& sessionId);

private:
    VersaAICore();
    std::unordered_map<std::string, std::unique_ptr<ChatbotAI>> chatbots_;
    VersaAIAgentRegistry agentRegistry_;
    std::unordered_map<std::string, VersaAIContext> contexts_;
};
