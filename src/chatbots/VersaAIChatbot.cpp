#include "chatbots/VersaAIChatbot.hpp"
#include "VersaAILogger.hpp"
#include <algorithm>
#include <cctype>

std::string VersaAIChatbot::getResponse(const std::string& userInput) {
  VersaAI::Logger::getInstance().info("VersaAI general chatbot processing: " + userInput, "VersaAIChatbot");

  // Convert input to lowercase for case-insensitive matching
  std::string lowerInput = userInput;
  std::transform(lowerInput.begin(), lowerInput.end(), lowerInput.begin(),
                 [](unsigned char c) { return std::tolower(c); });

  // Help and information queries
  if (lowerInput.find("help") != std::string::npos ||
      lowerInput.find("what can you do") != std::string::npos ||
      lowerInput.find("capabilities") != std::string::npos) {
    return "VersaAI is a hierarchical, modular AI ecosystem. Available modules:\n"
           "- VersaOS: Operating system integration and automation\n"
           "- VersaModeling: 3D modeling and design assistance\n"
           "- VersaGameEngine: Game development and VGE integration\n"
           "- Development: Code generation and development assistance\n\n"
           "To use a specific module, select it at startup or use module-specific commands.";
  }

  // Version and about queries
  if (lowerInput.find("version") != std::string::npos ||
      lowerInput.find("about") != std::string::npos) {
    return "VersaAI v1.0 - Production-Grade AI Ecosystem\n"
           "A hierarchical, modular AI system providing specialized agents for:\n"
           "- Operating Systems (VersaOS)\n"
           "- 3D Modeling (VersaModeling)\n"
           "- Game Development (VersaGameEngine)\n"
           "- Software Development (Development)\n\n"
           "Built with C++, following enterprise-level architecture patterns.";
  }

  // Module information
  if (lowerInput.find("module") != std::string::npos ||
      lowerInput.find("agent") != std::string::npos) {
    return "VersaAI uses a 4-layer delegation pattern:\n"
           "1. VersaAICore - Central coordinator (singleton)\n"
           "2. ModelBase - Foundation models\n"
           "3. AgentBase - Specialized agents\n"
           "4. Tools & Memory - External integrations\n\n"
           "Each application has dedicated chatbots and agents for specialized tasks.";
  }

  // Default response for general queries
  return "I'm VersaAI, your general AI assistant. I can help you understand the system and route you to specialized modules.\n\n"
         "Available commands:\n"
         "- 'help' - View available modules and capabilities\n"
         "- 'about' or 'version' - Learn about VersaAI\n"
         "- 'modules' or 'agents' - Learn about the architecture\n\n"
         "For specialized tasks, please select a specific module (VersaOS, VersaModeling, VersaGameEngine, or Development).";
}
