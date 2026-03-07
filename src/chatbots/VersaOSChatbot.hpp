#pragma once
#include "ChatbotAI.hpp"

class VersaOSChatbot : public ChatbotAI {
public:
    VersaOSChatbot() = default;
    ~VersaOSChatbot() override = default;

    std::string getResponse(const std::string& userInput) override;
};
