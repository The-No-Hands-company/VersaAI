#pragma once

#include "ChatbotAI.hpp"
#include <string>

/**
 * @brief General VersaAI Chatbot for system-wide queries
 *
 * Handles general inquiries about VersaAI capabilities, routing,
 * and providing information about available modules and agents.
 */
class VersaAIChatbot : public ChatbotAI {
public:
  VersaAIChatbot() = default;
  ~VersaAIChatbot() override = default;

  std::string getResponse(const std::string& userInput) override;
};
