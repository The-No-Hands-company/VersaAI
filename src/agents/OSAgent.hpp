#pragma once
#include "AgentBase.hpp"

class OSAgent : public AgentBase {
public:
    OSAgent() : AgentBase("OSAgent") {}

protected:
    std::string executeTask(const std::string& input) override;
};
