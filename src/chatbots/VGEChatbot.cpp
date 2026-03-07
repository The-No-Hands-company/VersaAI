#include "VGEChatbot.hpp"

std::string VGEChatbot::getResponse(const std::string& userInput) {
    if (userInput == "generate level") {
        return "Generating a new game level...";
    } else if (userInput == "add npc") {
        return "Adding a new NPC to the scene.";
    } else if (userInput == "help") {
        return "Commands: generate level, add npc, help, exit.";
    } else if (userInput == "exit") {
        return "Exiting VGE assistant. Goodbye!";
    }
    return ChatbotAI::getResponse(userInput);
}
