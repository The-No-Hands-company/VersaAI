#pragma once

#include "ChatbotAI.hpp"
#include <string>

class DevelopmentChatbot : public ChatbotAI {
public:
  DevelopmentChatbot() = default;
  ~DevelopmentChatbot() override = default;

  std::string getResponse(const std::string& userInput) override;
};
