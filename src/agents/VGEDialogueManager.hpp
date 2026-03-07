#pragma once
#include <string>

class VGEDialogueManager {
public:
    std::string getClarification(const std::string& prompt) {
        if (prompt.find("fortnite") != std::string::npos || prompt.find("fps game") != std::string::npos) {
            return "To help you, I need more details. Do you want multiplayer? Building mechanics? What art style?";
        }
        return "Could you provide more details about your request?";
    }
};
