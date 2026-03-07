#pragma once
#include "ChatbotAI.hpp"

class VGEChatbot : public ChatbotAI {
public:
    VGEChatbot() = default;
    ~VGEChatbot() override = default;
    std::string getResponse(const std::string& userInput) override;
};
