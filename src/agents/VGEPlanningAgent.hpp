#pragma once
#include <string>
#include <vector>

struct VGEPlanStep {
    std::string description;
    bool completed = false;
};

class VGEPlanningAgent {
public:
    std::vector<VGEPlanStep> decompose(const std::string& prompt) {
        std::vector<VGEPlanStep> steps;
        if (prompt.find("fortnite") != std::string::npos || prompt.find("fps game") != std::string::npos) {
            steps.push_back({"Set up multiplayer FPS project"});
            steps.push_back({"Add building mechanics"});
            steps.push_back({"Import realistic assets"});
            steps.push_back({"Create map layout"});
        } else {
            steps.push_back({"Analyze requirements"});
        }
        return steps;
    }
};
