#include "VGEAgent.hpp"
#include "VGEIntentParser.hpp"

VGEAgent::VGEAgent() : AgentBase("VGEAgent") {
    intentParser_ = new VGEIntentParser();
}

std::string VGEAgent::executeTask(const std::string& input) {
    VGETask task = intentParser_->parse(input);
    return executeTask(task);
}

std::string VGEAgent::executeTask(const VGETask& task) {
    if (task.type == "generate_level" && task.params.at("theme") == "forest") {
        // Here you would call your game engine's API to generate the level
        return "[Agent] Forest level with " + task.params.at("enemies") + " enemies generated.";
    } else if (task.type == "npc_behavior" && task.params.at("behavior") == "patrol") {
        // Here you would call your engine's scripting API
        return "[Agent] NPC patrol behavior script created.";
    }
    return "[Agent] Unknown or unsupported task.";
}
