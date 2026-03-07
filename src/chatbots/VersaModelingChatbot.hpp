#pragma once
#include "ChatbotAI.hpp"

class VersaModelingChatbot : public ChatbotAI {
public:
    VersaModelingChatbot() = default;
    ~VersaModelingChatbot() override = default;

    std::string getResponse(const std::string& userInput) override;
};
