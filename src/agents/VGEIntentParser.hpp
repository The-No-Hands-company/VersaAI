#pragma once
#include <algorithm>
#include <cctype>
#include <string>
#include <unordered_map>

struct VGETask {
    std::string type;
    std::unordered_map<std::string, std::string> params;
    std::string sessionId; // For context/session support
};

class VGEIntentParser {
public:
    // Very basic intent parsing for demo purposes
    VGETask parse(const std::string& prompt, const std::string& sessionId = "") {
        VGETask task;
        task.sessionId = sessionId;
        // Example: extract enemy count from prompt
        if (prompt.find("generate forest level") != std::string::npos) {
            task.type = "generate_level";
            task.params["theme"] = "forest";
            size_t pos = prompt.find("with ");
            if (pos != std::string::npos) {
                std::string rest = prompt.substr(pos + 5);
                size_t enemiesPos = rest.find("enemies");
                if (enemiesPos != std::string::npos) {
                    std::string num = rest.substr(0, enemiesPos);
                    num.erase(remove_if(num.begin(), num.end(), ::isspace), num.end());
                    task.params["enemies"] = num;
                } else {
                    task.params["enemies"] = "10";
                }
            } else {
                task.params["enemies"] = "10";
            }
        } else if (prompt.find("npc patrol") != std::string::npos) {
            task.type = "npc_behavior";
            task.params["behavior"] = "patrol";
        } else if (prompt.find("generate desert level") != std::string::npos) {
            task.type = "generate_level";
            task.params["theme"] = "desert";
            task.params["enemies"] = "5";
        } else if (prompt.find("show session info") != std::string::npos) {
            task.type = "session_info";
        } else {
            task.type = "unknown";
        }
        return task;
    }
};
