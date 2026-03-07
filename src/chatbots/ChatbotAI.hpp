#pragma once
#include <string>

class ChatbotAI {
public:
    ChatbotAI() = default;
    virtual ~ChatbotAI() = default;

    virtual std::string getResponse(const std::string& userInput);
};
