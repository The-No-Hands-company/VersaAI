#include "VersaOSChatbot.hpp"

std::string VersaOSChatbot::getResponse(const std::string& userInput) {
    if (userInput == "open versamodeling") {
        return "Opening VersaModeling...";
    } else if (userInput == "list apps") {
        return "Available apps: VersaModeling, VersaGameEngine, VersaOS.";
    } else if (userInput == "help") {
        return "Commands: open versamodeling, list apps, help, exit.";
    } else if (userInput == "exit") {
        return "Exiting VersaOS. Goodbye!";
    }
    return ChatbotAI::getResponse(userInput);
}
