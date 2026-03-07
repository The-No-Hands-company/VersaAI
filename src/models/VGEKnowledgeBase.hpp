#pragma once
#include <string>
#include <unordered_map>

class VGEKnowledgeBase {
public:
    VGEKnowledgeBase() {
        templates_["fps"] = "First-person shooter template with basic controls.";
        templates_["multiplayer"] = "Multiplayer networking template.";
        templates_["building"] = "Building mechanics template.";
    }
    std::string getTemplate(const std::string& key) const {
        auto it = templates_.find(key);
        return it != templates_.end() ? it->second : "No template found.";
    }
private:
    std::unordered_map<std::string, std::string> templates_;
};
