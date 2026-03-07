#pragma once
#include <string>

class ModelBase {
public:
    virtual ~ModelBase() = default;
    virtual std::string getName() const = 0;
};
