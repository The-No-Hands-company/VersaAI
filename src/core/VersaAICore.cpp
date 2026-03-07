#include "core/VersaAICore.hpp"
#include "agents/ModelingAgent.hpp"
#include "agents/OSAgent.hpp"
#include "agents/VGEAgent.hpp"
#include "agents/DevelopmentAgent.hpp"
#include "chatbots/VersaAIChatbot.hpp"
#include "chatbots/VGEChatbot.hpp"
#include "chatbots/DevelopmentChatbot.hpp"
#include "VersaAILogger.hpp"
#include "VersaAIException.hpp"
#include "BehaviorPolicy.hpp"

VersaAICore& VersaAICore::getInstance() {
    static VersaAICore instance;
    return instance;
}

VersaAICore::VersaAICore() {
    // Initialize logger
    VersaAI::LoggerConfig logConfig;
    logConfig.minLevel = VersaAI::LogLevel::INFO;  // Production default: INFO level
    logConfig.enableConsole = true;
    logConfig.enableFile = true;
    logConfig.logFilePath = "versaai.log";
    VersaAI::Logger::getInstance().initialize(logConfig);

    VersaAI::Logger::getInstance().info("VersaAICore initializing", "VersaAICore");

    // Initialize Behavior Policy with mandate
    std::string mandate_path = ".github/AI_BEHAVIOR_MANDATE.md";
    if (!VersaAI::BehaviorPolicy::getInstance().loadMandate(mandate_path)) {
        VersaAI::Logger::getInstance().warning(
            "Could not load AI Behavior Mandate from " + mandate_path +
            " - using built-in defaults",
            "VersaAICore"
        );
    } else {
        VersaAI::Logger::getInstance().info(
            "AI Behavior Mandate loaded and enforced system-wide",
            "VersaAICore"
        );
    }

    // Register default chatbots
    registerChatbot("VersaAI", std::make_unique<VersaAIChatbot>());
    registerChatbot("VersaOS", std::make_unique<VersaOSChatbot>());
    registerChatbot("VersaModeling", std::make_unique<VersaModelingChatbot>());
    registerChatbot("VersaGameEngine", std::make_unique<VGEChatbot>());
    registerChatbot("Development", std::make_unique<DevelopmentChatbot>());

    // Register default agents
    registerAgent("VersaModeling", std::make_shared<ModelingAgent>());
    registerAgent("VersaOS", std::make_shared<OSAgent>());
    registerAgent("VersaGameEngine", std::make_shared<VGEAgent>());

    // Register Development Agent for code generation tasks
    registerAgent("Development", std::make_shared<DevelopmentAgent>());

    VersaAI::Logger::getInstance().info("VersaAICore initialization complete", "VersaAICore");
}

void VersaAICore::registerChatbot(const std::string& appName, std::unique_ptr<ChatbotAI> chatbot) {
    VersaAI::Logger::getInstance().debug("Registering chatbot: " + appName, "VersaAICore");
    chatbots_[appName] = std::move(chatbot);
}

void VersaAICore::registerAgent(const std::string& appName, std::shared_ptr<AgentBase> agent) {
    VersaAI::Logger::getInstance().debug("Registering agent: " + appName, "VersaAICore");
    agentRegistry_.registerAgent(appName, agent);
}

std::string VersaAICore::processInput(const std::string& appName, const std::string& userInput) {
    VersaAI::LogEntry entry(VersaAI::LogLevel::DEBUG, "Processing input", "VersaAICore");
    entry.addContext("app", appName).addContext("input_length", std::to_string(userInput.length()));
    VersaAI::Logger::getInstance().log(entry);

    auto it = chatbots_.find(appName);
    if (it == chatbots_.end()) {
        throw VersaAI::RegistryException(
            "No chatbot registered for application: " + appName,
            VersaAI::ErrorCode::REGISTRY_KEY_NOT_FOUND
        ).setRegistryType("ChatbotRegistry").setKey(appName);
    }

    try {
        return it->second->getResponse(userInput);
    } catch (const VersaAI::Exception& ex) {
        VersaAI::logException(ex, "Error processing user input");
        throw;  // Re-throw for caller to handle
    } catch (const std::exception& ex) {
        VersaAI::Exception wrapped(
            "Unexpected error in chatbot: " + std::string(ex.what()),
            VersaAI::ErrorCode::UNKNOWN
        );
        wrapped.setComponent("VersaAICore");
        wrapped.addContext("app", appName);
        VersaAI::logException(wrapped);
        throw wrapped;
    }
}

std::string VersaAICore::invokeAgent(const std::string& appName, const std::string& input) {
    VersaAI::LogEntry entry(VersaAI::LogLevel::DEBUG, "Invoking agent", "VersaAICore");
    entry.addContext("agent", appName).addContext("input_length", std::to_string(input.length()));
    VersaAI::Logger::getInstance().log(entry);

    auto agent = agentRegistry_.getAgent(appName);
    if (!agent) {
        throw VersaAI::Exception(
            "No agent registered for: " + appName,
            VersaAI::ErrorCode::UNKNOWN
        );
    }

    try {
        return agent->performTask(input);
    } catch (const VersaAI::Exception& ex) {
        VersaAI::logException(ex, "Error invoking agent");
        throw;
    } catch (const std::exception& ex) {
        VersaAI::Exception wrapped(
            "Unexpected error in agent: " + std::string(ex.what()),
            VersaAI::ErrorCode::UNKNOWN
        );
        wrapped.setComponent("VersaAICore");
        wrapped.addContext("agent", appName);
        VersaAI::logException(wrapped);
        throw wrapped;
    }
}
