#pragma once
#include <string>
#include <unordered_map>

class VersaAIContext {
public:
    void set(const std::string& key, const std::string& value) {
        data_[key] = value;
    }
    std::string get(const std::string& key) const {
        auto it = data_.find(key);
        return it != data_.end() ? it->second : "";
    }
private:
    std::unordered_map<std::string, std::string> data_;
};
