#pragma once
#include "AgentBase.hpp"

class ModelingAgent : public AgentBase {
public:
    ModelingAgent() : AgentBase("ModelingAgent") {}

protected:
    std::string executeTask(const std::string& input) override;
};
