#pragma once
#include "AgentBase.hpp"

// Forward declaration
struct VGETask;
class VGEIntentParser;

class VGEAgent : public AgentBase {
public:
    VGEAgent();

protected:
    std::string executeTask(const std::string& input) override;

private:
    VGEIntentParser* intentParser_;
    // Here you would add references to your game engine API, etc.
    std::string executeTask(const VGETask& task);
};
