#include "ModelingAgent.hpp"

std::string ModelingAgent::executeTask(const std::string& input) {
    if (input == "generate cube") {
        return "[Agent] Generated a 3D cube.";
    }
    return "[Agent] Unknown modeling task.";
}
