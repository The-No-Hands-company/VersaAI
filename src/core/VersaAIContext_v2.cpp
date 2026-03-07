#include "../../include/VersaAIContext_v2.hpp"
#include <algorithm>
#include <mutex>
#include <sstream>

namespace VersaAI {

void VersaAIContextV2::set(const std::string& key,
                            const ContextValue& value,
                            const std::string& namespace_path,
                            bool persistent) {
    std::unique_lock lock(mutex_);

    auto& namespace_data = data_[namespace_path];
    auto it = namespace_data.find(key);

    if (it != namespace_data.end()) {
        // Update existing entry
        it->second.value = value;
        it->second.recordModification();
        it->second.metadata.persistent = persistent;
    } else {
        // Create new entry
        ContextEntry entry;
        entry.value = value;
        entry.metadata.persistent = persistent;
        namespace_data[key] = std::move(entry);
    }
}

std::optional<ContextValue> VersaAIContextV2::get(const std::string& key,
                                                    const std::string& namespace_path) {
    std::shared_lock lock(mutex_);

    auto ns_it = data_.find(namespace_path);
    if (ns_it == data_.end()) {
        return std::nullopt;
    }

    auto key_it = ns_it->second.find(key);
    if (key_it == ns_it->second.end()) {
        return std::nullopt;
    }

    // Record access (requires upgrade to unique lock)
    lock.unlock();
    std::unique_lock write_lock(mutex_);
    key_it->second.recordAccess();

    return key_it->second.value;
}

bool VersaAIContextV2::exists(const std::string& key,
                               const std::string& namespace_path) {
    std::shared_lock lock(mutex_);

    auto ns_it = data_.find(namespace_path);
    if (ns_it == data_.end()) {
        return false;
    }

    return ns_it->second.find(key) != ns_it->second.end();
}

bool VersaAIContextV2::remove(const std::string& key,
                               const std::string& namespace_path) {
    std::unique_lock lock(mutex_);

    auto ns_it = data_.find(namespace_path);
    if (ns_it == data_.end()) {
        return false;
    }

    return ns_it->second.erase(key) > 0;
}

void VersaAIContextV2::clear() {
    std::unique_lock lock(mutex_);

    for (auto& [namespace_path, namespace_data] : data_) {
        // Remove non-persistent entries
        for (auto it = namespace_data.begin(); it != namespace_data.end();) {
            if (!it->second.metadata.persistent) {
                it = namespace_data.erase(it);
            } else {
                ++it;
            }
        }
    }

    // Remove empty namespaces
    for (auto it = data_.begin(); it != data_.end();) {
        if (it->second.empty()) {
            it = data_.erase(it);
        } else {
            ++it;
        }
    }
}

void VersaAIContextV2::clearAll() {
    std::unique_lock lock(mutex_);
    data_.clear();
    snapshots_.clear();
}

std::optional<ContextMetadata> VersaAIContextV2::getMetadata(
    const std::string& key,
    const std::string& namespace_path) {
    std::shared_lock lock(mutex_);

    auto ns_it = data_.find(namespace_path);
    if (ns_it == data_.end()) {
        return std::nullopt;
    }

    auto key_it = ns_it->second.find(key);
    if (key_it == ns_it->second.end()) {
        return std::nullopt;
    }

    return key_it->second.metadata;
}

uint64_t VersaAIContextV2::createSnapshot() {
    std::unique_lock lock(mutex_);

    Snapshot snapshot;
    snapshot.id = nextSnapshotId_++;
    snapshot.timestamp = std::chrono::system_clock::now();
    snapshot.data = data_;  // Deep copy

    snapshots_.push_back(std::move(snapshot));

    return snapshot.id;
}

bool VersaAIContextV2::rollbackToSnapshot(uint64_t snapshotId) {
    std::unique_lock lock(mutex_);

    auto it = std::find_if(snapshots_.begin(), snapshots_.end(),
                          [snapshotId](const Snapshot& s) { return s.id == snapshotId; });

    if (it == snapshots_.end()) {
        return false;
    }

    data_ = it->data;  // Restore snapshot

    // Remove snapshots newer than the one we're rolling back to
    snapshots_.erase(std::next(it), snapshots_.end());

    return true;
}

std::vector<std::string> VersaAIContextV2::getKeysInNamespace(
    const std::string& namespace_path) {
    std::shared_lock lock(mutex_);

    std::vector<std::string> keys;

    auto ns_it = data_.find(namespace_path);
    if (ns_it == data_.end()) {
        return keys;
    }

    keys.reserve(ns_it->second.size());
    for (const auto& [key, _] : ns_it->second) {
        keys.push_back(key);
    }

    return keys;
}

VersaAIContextV2::ContextStats VersaAIContextV2::getStats() const {
    std::shared_lock lock(mutex_);

    ContextStats stats{};
    stats.totalEntries = 0;
    stats.persistentEntries = 0;
    stats.totalNamespaces = data_.size();
    stats.totalSnapshots = snapshots_.size();
    stats.totalAccesses = 0;

    auto now = std::chrono::system_clock::now();
    stats.oldestEntry = now;
    stats.newestEntry = std::chrono::system_clock::time_point::min();

    for (const auto& [namespace_path, namespace_data] : data_) {
        stats.totalEntries += namespace_data.size();

        for (const auto& [key, entry] : namespace_data) {
            if (entry.metadata.persistent) {
                stats.persistentEntries++;
            }

            stats.totalAccesses += entry.metadata.accessCount;

            if (entry.metadata.created < stats.oldestEntry) {
                stats.oldestEntry = entry.metadata.created;
            }

            if (entry.metadata.created > stats.newestEntry) {
                stats.newestEntry = entry.metadata.created;
            }
        }
    }

    return stats;
}

std::string VersaAIContextV2::serializeToJson() const {
    std::shared_lock lock(mutex_);

    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"version\": \"2.0\",\n";
    oss << "  \"namespaces\": {\n";

    bool first_ns = true;
    for (const auto& [namespace_path, namespace_data] : data_) {
        if (!first_ns) oss << ",\n";
        first_ns = false;

        oss << "    \"" << namespace_path << "\": {\n";

        bool first_key = true;
        for (const auto& [key, entry] : namespace_data) {
            if (!first_key) oss << ",\n";
            first_key = false;

            oss << "      \"" << key << "\": ";

            // Serialize value based on type
            std::visit([&oss](const auto& val) {
                using T = std::decay_t<decltype(val)>;
                if constexpr (std::is_same_v<T, std::string>) {
                    oss << "\"" << val << "\"";
                } else if constexpr (std::is_same_v<T, bool>) {
                    oss << (val ? "true" : "false");
                } else if constexpr (std::is_same_v<T, std::vector<std::string>>) {
                    oss << "[";
                    for (size_t i = 0; i < val.size(); ++i) {
                        if (i > 0) oss << ", ";
                        oss << "\"" << val[i] << "\"";
                    }
                    oss << "]";
                } else {
                    oss << val;
                }
            }, entry.value);
        }

        oss << "\n    }";
    }

    oss << "\n  }\n";
    oss << "}\n";

    return oss.str();
}

bool VersaAIContextV2::deserializeFromJson(const std::string& /*json*/) {
    // TODO: Implement proper JSON parsing (use rapidjson or nlohmann/json)
    // For now, return false to indicate not implemented
    return false;
}

std::vector<uint8_t> VersaAIContextV2::serializeToBinary() const {
    // TODO: Implement binary serialization
    // Use protocol buffers or custom binary format
    return {};
}

bool VersaAIContextV2::deserializeFromBinary(const std::vector<uint8_t>& /*data*/) {
    // TODO: Implement binary deserialization
    return false;
}

} // namespace VersaAI
