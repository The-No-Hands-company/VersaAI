#pragma once
#include <string>

class ApiInterface {
public:
    virtual ~ApiInterface() = default;
    virtual std::string handleChatbotRequest(const std::string& userInput) = 0;
};
