#pragma once

#include "VersaAIModel.hpp"
#include <map>
#include <mutex>
#include <functional>

namespace VersaAI {

// ============================================================================
// Model Selection Strategy
// ============================================================================

/**
 * @brief Criteria for automatic model selection
 */
struct ModelSelectionCriteria {
    std::vector<ModelCapability> requiredCapabilities;
    std::optional<ModelArchitecture> preferredArchitecture;
    uint64_t maxMemoryBytes = 0;            // 0 = no limit
    uint32_t minContextLength = 0;           // 0 = no minimum
    bool preferGPU = false;
    bool requiresQuantization = false;
    std::optional<QuantizationType> preferredQuantization;

    // Performance requirements
    double minTokensPerSecond = 0.0;
    double maxFirstTokenLatencyMs = 0.0;    // 0 = no limit
};

/**
 * @brief Strategy for selecting best model based on criteria
 */
class ModelSelectionStrategy {
public:
    virtual ~ModelSelectionStrategy() = default;

    /**
     * @brief Select best model from available models
     * @param models Available models to choose from
     * @param criteria Selection criteria
     * @return Pointer to selected model, or nullptr if no suitable model found
     */
    virtual std::shared_ptr<ModelBase> select(
        const std::vector<std::shared_ptr<ModelBase>>& models,
        const ModelSelectionCriteria& criteria
    ) = 0;
};

/**
 * @brief Default selection strategy: capabilities + smallest size
 */
class DefaultSelectionStrategy : public ModelSelectionStrategy {
public:
    std::shared_ptr<ModelBase> select(
        const std::vector<std::shared_ptr<ModelBase>>& models,
        const ModelSelectionCriteria& criteria
    ) override;
};

/**
 * @brief Performance-focused strategy: fastest model meeting criteria
 */
class PerformanceSelectionStrategy : public ModelSelectionStrategy {
public:
    std::shared_ptr<ModelBase> select(
        const std::vector<std::shared_ptr<ModelBase>>& models,
        const ModelSelectionCriteria& criteria
    ) override;
};

// ============================================================================
// Model Registry
// ============================================================================

/**
 * @brief Central registry for managing loaded models
 *
 * Thread-safe registry supporting:
 * - Model registration and deregistration
 * - Lazy loading
 * - Automatic unloading (LRU eviction)
 * - Model selection based on criteria
 */
class ModelRegistry {
public:
    static ModelRegistry& getInstance();

    /**
     * @brief Register a model (does not load it)
     * @param name Unique identifier for the model
     * @param model Model instance
     * @throws RegistryException if name already exists
     */
    void registerModel(const std::string& name, std::shared_ptr<ModelBase> model);

    /**
     * @brief Unregister a model (unloads if loaded)
     * @param name Model identifier
     * @return true if model was found and removed
     */
    bool unregisterModel(const std::string& name);

    /**
     * @brief Get model by name
     * @param name Model identifier
     * @param autoLoad If true, loads model if not already loaded
     * @return Pointer to model, or nullptr if not found
     */
    std::shared_ptr<ModelBase> getModel(const std::string& name, bool autoLoad = false);

    /**
     * @brief Load model into memory
     * @param name Model identifier
     * @throws RegistryException if model not found
     * @throws ModelException if loading fails
     */
    void loadModel(const std::string& name);

    /**
     * @brief Unload model from memory (keeps registration)
     * @param name Model identifier
     */
    void unloadModel(const std::string& name);

    /**
     * @brief Get all registered model names
     */
    std::vector<std::string> getAllModelNames() const;

    /**
     * @brief Get all loaded models
     */
    std::vector<std::shared_ptr<ModelBase>> getLoadedModels() const;

    /**
     * @brief Select best model based on criteria
     * @param criteria Selection criteria
     * @param autoLoad If true, loads selected model if not already loaded
     * @return Selected model, or nullptr if no suitable model found
     */
    std::shared_ptr<ModelBase> selectModel(
        const ModelSelectionCriteria& criteria,
        bool autoLoad = false
    );

    /**
     * @brief Set selection strategy
     */
    void setSelectionStrategy(std::unique_ptr<ModelSelectionStrategy> strategy);

    /**
     * @brief Get total memory usage of all loaded models
     */
    uint64_t getTotalMemoryUsage() const;

    /**
     * @brief Set maximum total memory limit
     * @param maxBytes Maximum bytes for all models (0 = no limit)
     */
    void setMemoryLimit(uint64_t maxBytes);

    /**
     * @brief Enable/disable automatic LRU eviction when memory limit reached
     */
    void setAutoEviction(bool enabled);

    /**
     * @brief Unload least recently used model to free memory
     * @return true if a model was unloaded
     */
    bool evictLRU();

    /**
     * @brief Clear all models (unloads and unregisters all)
     */
    void clear();

private:
    ModelRegistry() = default;

    struct ModelEntry {
        std::shared_ptr<ModelBase> model;
        std::chrono::system_clock::time_point lastAccessed;
        uint32_t accessCount = 0;
    };

    std::map<std::string, ModelEntry> models_;
    mutable std::mutex mutex_;

    std::unique_ptr<ModelSelectionStrategy> selectionStrategy_ =
        std::make_unique<DefaultSelectionStrategy>();

    uint64_t memoryLimit_ = 0;  // 0 = no limit
    bool autoEviction_ = true;

    /**
     * @brief Update access time for model (for LRU)
     */
    void updateAccessTime(const std::string& name);

    /**
     * @brief Check if loading new model would exceed memory limit
     */
    bool wouldExceedMemoryLimit(uint64_t additionalBytes) const;

    /**
     * @brief Evict models until we have enough free memory
     */
    void evictUntilFreeMemory(uint64_t requiredBytes);
};

// ============================================================================
// Model Loader
// ============================================================================

/**
 * @brief Factory for creating and loading models from files
 */
class ModelLoader {
public:
    /**
     * @brief Load model from file
     * @param filePath Path to model file
     * @param progressCallback Optional progress callback
     * @return Loaded model instance
     * @throws ModelException if loading fails
     */
    static std::shared_ptr<ModelBase> loadFromFile(
        const std::string& filePath,
        std::function<void(double)> progressCallback = nullptr
    );

    /**
     * @brief Create model metadata from file (without loading weights)
     * @param filePath Path to model file
     * @return Model metadata
     */
    static ModelMetadata createMetadataFromFile(const std::string& filePath);

    /**
     * @brief Validate model file
     * @param filePath Path to model file
     * @return true if valid
     */
    static bool validateFile(const std::string& filePath);

    /**
     * @brief Register custom model factory for a format
     */
    using ModelFactory = std::function<std::shared_ptr<ModelBase>(const std::string&)>;
    static void registerFactory(ModelFormat format, ModelFactory factory);

private:
    static std::map<ModelFormat, ModelFactory> factories_;
    static std::mutex factoryMutex_;
};

} // namespace VersaAI
