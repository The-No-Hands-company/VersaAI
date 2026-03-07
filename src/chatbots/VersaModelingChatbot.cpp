#include "VersaModelingChatbot.hpp"

std::string VersaModelingChatbot::getResponse(const std::string& userInput) {
    if (userInput == "generate cube") {
        return "Generating a 3D cube in VersaModeling...";
    } else if (userInput == "list tools") {
        return "Available tools: Extrude, Bevel, Sculpt, Paint.";
    } else if (userInput == "help") {
        return "Commands: generate cube, list tools, help, exit.";
    } else if (userInput == "exit") {
        return "Exiting VersaModeling. Goodbye!";
    }
    return ChatbotAI::getResponse(userInput);
}
