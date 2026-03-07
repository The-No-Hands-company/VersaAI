#include "ApiInterface.hpp"
#include "chatbots/VersaOSChatbot.hpp"

class VersaOSApi : public ApiInterface {
public:
    VersaOSApi() : chatbot_() {}
    std::string handleChatbotRequest(const std::string& userInput) override {
        return chatbot_.getResponse(userInput);
    }
private:
    VersaOSChatbot chatbot_;
};
