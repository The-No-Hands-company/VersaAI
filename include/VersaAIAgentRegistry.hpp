#pragma once
#include <string>
#include <unordered_map>
#include <memory>
#include "agents/AgentBase.hpp"

class VersaAIAgentRegistry {
public:
    void registerAgent(const std::string& appName, std::shared_ptr<AgentBase> agent) {
        agents_[appName] = agent;
    }
    std::shared_ptr<AgentBase> getAgent(const std::string& appName) const {
        auto it = agents_.find(appName);
        return it != agents_.end() ? it->second : nullptr;
    }
private:
    std::unordered_map<std::string, std::shared_ptr<AgentBase>> agents_;
};
