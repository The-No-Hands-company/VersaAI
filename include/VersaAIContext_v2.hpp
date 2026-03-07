#pragma once

#include <algorithm>
#include <chrono>
#include <cstdint>
#include <optional>
#include <shared_mutex>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

namespace VersaAI {

/// Value types supported in the context system
using ContextValue = std::variant<
    std::string,
    int64_t,
    double,
    bool,
    std::vector<std::string>
>;

/// Metadata for context entries
struct ContextMetadata {
    std::chrono::system_clock::time_point created;
    std::chrono::system_clock::time_point lastAccessed;
    std::chrono::system_clock::time_point lastModified;
    uint64_t accessCount = 0;
    std::string description;
    bool persistent = false;  // Should this survive context resets?
};

/// Individual context entry with value and metadata
struct ContextEntry {
    ContextValue value;
    ContextMetadata metadata;

    ContextEntry() {
        auto now = std::chrono::system_clock::now();
        metadata.created = now;
        metadata.lastAccessed = now;
        metadata.lastModified = now;
    }

    void recordAccess() {
        metadata.lastAccessed = std::chrono::system_clock::now();
        metadata.accessCount++;
    }

    void recordModification() {
        metadata.lastModified = std::chrono::system_clock::now();
    }
};

/// Hierarchical context system with namespaces and versioning
class VersaAIContextV2 {
public:
    VersaAIContextV2() = default;
    ~VersaAIContextV2() = default;

    // Prevent copying, allow moving
    VersaAIContextV2(const VersaAIContextV2&) = delete;
    VersaAIContextV2& operator=(const VersaAIContextV2&) = delete;
    VersaAIContextV2(VersaAIContextV2&&) noexcept = default;
    VersaAIContextV2& operator=(VersaAIContextV2&&) noexcept = default;

    /// Set a value in the context with optional namespace
    /// @param key The key to store the value under
    /// @param value The value to store
    /// @param namespace_path Optional namespace path (e.g., "session.user.preferences")
    /// @param persistent Whether this value survives context resets
    void set(const std::string& key,
             const ContextValue& value,
             const std::string& namespace_path = "",
             bool persistent = false);

    /// Get a value from the context
    /// @param key The key to retrieve
    /// @param namespace_path Optional namespace path
    /// @return The value if found, std::nullopt otherwise
    std::optional<ContextValue> get(const std::string& key,
                                     const std::string& namespace_path = "");

    /// Get a typed value from the context
    /// @tparam T The expected type
    /// @param key The key to retrieve
    /// @param namespace_path Optional namespace path
    /// @return The value if found and type matches, std::nullopt otherwise
    template<typename T>
    std::optional<T> getTyped(const std::string& key,
                              const std::string& namespace_path = "");

    /// Check if a key exists in the context
    bool exists(const std::string& key, const std::string& namespace_path = "");

    /// Remove a key from the context
    /// @return true if the key was found and removed
    bool remove(const std::string& key, const std::string& namespace_path = "");

    /// Clear all non-persistent entries
    void clear();

    /// Clear entire context including persistent entries
    void clearAll();

    /// Get metadata for a key
    std::optional<ContextMetadata> getMetadata(const std::string& key,
                                                const std::string& namespace_path = "");

    /// Create a snapshot of the current context state
    /// @return Snapshot ID that can be used for rollback
    uint64_t createSnapshot();

    /// Rollback to a previous snapshot
    /// @param snapshotId The snapshot to rollback to
    /// @return true if rollback succeeded
    bool rollbackToSnapshot(uint64_t snapshotId);

    /// Get all keys in a namespace
    std::vector<std::string> getKeysInNamespace(const std::string& namespace_path = "");

    /// Get statistics about context usage
    struct ContextStats {
        size_t totalEntries = 0;
        size_t persistentEntries = 0;
        size_t totalNamespaces = 0;
        size_t totalSnapshots = 0;
        uint64_t totalAccesses = 0;
        std::chrono::system_clock::time_point oldestEntry;
        std::chrono::system_clock::time_point newestEntry;
    };

    ContextStats getStats() const;

    /// Serialize context to JSON string
    std::string serializeToJson() const;

    /// Deserialize context from JSON string
    /// @param json JSON string to deserialize
    /// @return true if deserialization succeeded
    bool deserializeFromJson(const std::string& json);

    /// Export context to binary format (more efficient)
    std::vector<uint8_t> serializeToBinary() const;

    /// Import context from binary format
    bool deserializeFromBinary(const std::vector<uint8_t>& data);

private:
    /// Thread-safe access to context data
    mutable std::shared_mutex mutex_;

    /// Nested map structure: namespace -> key -> entry
    std::unordered_map<std::string, std::unordered_map<std::string, ContextEntry>> data_;

    /// Snapshot storage
    struct Snapshot {
        uint64_t id;
        std::chrono::system_clock::time_point timestamp;
        std::unordered_map<std::string, std::unordered_map<std::string, ContextEntry>> data;
    };

    std::vector<Snapshot> snapshots_;
    uint64_t nextSnapshotId_ = 1;

    /// Helper to get fully qualified key
    std::string getFullKey(const std::string& key, const std::string& namespace_path) const;

    /// Helper to split namespace path
    std::vector<std::string> splitNamespace(const std::string& namespace_path) const;
};

// Template implementation
template<typename T>
std::optional<T> VersaAIContextV2::getTyped(const std::string& key,
                                             const std::string& namespace_path) {
    auto value = get(key, namespace_path);
    if (!value) {
        return std::nullopt;
    }

    try {
        return std::get<T>(*value);
    } catch (const std::bad_variant_access&) {
        return std::nullopt;
    }
}

} // namespace VersaAI
