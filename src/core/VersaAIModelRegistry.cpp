#include "VersaAIModelRegistry.hpp"
#include "VersaAILogger.hpp"
#include <algorithm>
#include <filesystem>

namespace VersaAI {

// ============================================================================
// DefaultSelectionStrategy Implementation
// ============================================================================

std::shared_ptr<ModelBase> DefaultSelectionStrategy::select(
    const std::vector<std::shared_ptr<ModelBase>>& models,
    const ModelSelectionCriteria& criteria
) {
    std::vector<std::shared_ptr<ModelBase>> candidates;

    // Filter by required capabilities
    for (const auto& model : models) {
        bool meetsRequirements = true;

        // Check capabilities
        for (const auto& cap : criteria.requiredCapabilities) {
            if (!model->getMetadata().hasCapability(cap)) {
                meetsRequirements = false;
                break;
            }
        }

        if (!meetsRequirements) continue;

        // Check memory limit
        if (criteria.maxMemoryBytes > 0 &&
            model->getMetadata().fileSize > criteria.maxMemoryBytes) {
            continue;
        }

        // Check context length
        if (criteria.minContextLength > 0 &&
            model->getMetadata().contextLength < criteria.minContextLength) {
            continue;
        }

        candidates.push_back(model);
    }

    if (candidates.empty()) {
        return nullptr;
    }

    // Select smallest model among candidates
    return *std::min_element(candidates.begin(), candidates.end(),
        [](const auto& a, const auto& b) {
            return a->getMetadata().fileSize < b->getMetadata().fileSize;
        });
}

// ============================================================================
// PerformanceSelectionStrategy Implementation
// ============================================================================

std::shared_ptr<ModelBase> PerformanceSelectionStrategy::select(
    const std::vector<std::shared_ptr<ModelBase>>& models,
    const ModelSelectionCriteria& criteria
) {
    std::vector<std::shared_ptr<ModelBase>> candidates;

    for (const auto& model : models) {
        bool meetsRequirements = true;

        // Check capabilities
        for (const auto& cap : criteria.requiredCapabilities) {
            if (!model->getMetadata().hasCapability(cap)) {
                meetsRequirements = false;
                break;
            }
        }

        if (!meetsRequirements) continue;

        // Check performance requirements
        const auto& perf = model->getPerformanceMetrics();

        if (criteria.minTokensPerSecond > 0.0 &&
            perf.tokensPerSecond < criteria.minTokensPerSecond) {
            continue;
        }

        if (criteria.maxFirstTokenLatencyMs > 0.0 &&
            perf.firstTokenLatencyMs > criteria.maxFirstTokenLatencyMs) {
            continue;
        }

        candidates.push_back(model);
    }

    if (candidates.empty()) {
        return nullptr;
    }

    // Select fastest model
    return *std::max_element(candidates.begin(), candidates.end(),
        [](const auto& a, const auto& b) {
            return a->getPerformanceMetrics().tokensPerSecond <
                   b->getPerformanceMetrics().tokensPerSecond;
        });
}

// ============================================================================
// ModelRegistry Implementation
// ============================================================================

ModelRegistry& ModelRegistry::getInstance() {
    static ModelRegistry instance;
    return instance;
}

void ModelRegistry::registerModel(const std::string& name, std::shared_ptr<ModelBase> model) {
    std::lock_guard lock(mutex_);

    if (models_.find(name) != models_.end()) {
        throw RegistryException(
            "Model already registered",
            ErrorCode::REGISTRY_DUPLICATE_KEY
        ).setRegistryType("ModelRegistry").setKey(name);
    }

    ModelEntry entry;
    entry.model = model;
    entry.lastAccessed = std::chrono::system_clock::now();
    entry.accessCount = 0;

    models_[name] = entry;

    Logger::getInstance().info(
        "Model registered: " + name,
        "ModelRegistry"
    );
}

bool ModelRegistry::unregisterModel(const std::string& name) {
    std::lock_guard lock(mutex_);

    auto it = models_.find(name);
    if (it == models_.end()) {
        return false;
    }

    // Unload if loaded
    if (it->second.model->isLoaded()) {
        it->second.model->unload();
    }

    models_.erase(it);

    Logger::getInstance().info(
        "Model unregistered: " + name,
        "ModelRegistry"
    );

    return true;
}

std::shared_ptr<ModelBase> ModelRegistry::getModel(const std::string& name, bool autoLoad) {
    std::lock_guard lock(mutex_);

    auto it = models_.find(name);
    if (it == models_.end()) {
        return nullptr;
    }

    updateAccessTime(name);

    if (autoLoad && !it->second.model->isLoaded()) {
        // Temporarily release lock for loading
        mutex_.unlock();
        try {
            it->second.model->load();
        } catch (...) {
            mutex_.lock();
            throw;
        }
        mutex_.lock();
    }

    return it->second.model;
}

void ModelRegistry::loadModel(const std::string& name) {
    auto model = getModel(name, false);
    if (!model) {
        throw RegistryException(
            "Model not found",
            ErrorCode::REGISTRY_KEY_NOT_FOUND
        ).setRegistryType("ModelRegistry").setKey(name);
    }

    if (model->isLoaded()) {
        return;  // Already loaded
    }

    // Check memory limit
    uint64_t modelSize = model->getMetadata().fileSize;
    if (wouldExceedMemoryLimit(modelSize)) {
        if (autoEviction_) {
            evictUntilFreeMemory(modelSize);
        } else {
            throw ResourceException(
                "Loading model would exceed memory limit",
                ErrorCode::RESOURCE_EXHAUSTED
            ).setResourceType("Memory")
             .addContext("model", name)
             .addContext("required_bytes", std::to_string(modelSize))
             .addContext("current_usage", std::to_string(getTotalMemoryUsage()))
             .addContext("limit", std::to_string(memoryLimit_));
        }
    }

    model->load();

    Logger::getInstance().info(
        "Model loaded: " + name + " (" +
        std::to_string(modelSize / (1024 * 1024)) + " MB)",
        "ModelRegistry"
    );
}

void ModelRegistry::unloadModel(const std::string& name) {
    auto model = getModel(name, false);
    if (model && model->isLoaded()) {
        model->unload();
        Logger::getInstance().info(
            "Model unloaded: " + name,
            "ModelRegistry"
        );
    }
}

std::vector<std::string> ModelRegistry::getAllModelNames() const {
    std::lock_guard lock(mutex_);

    std::vector<std::string> names;
    names.reserve(models_.size());

    for (const auto& [name, _] : models_) {
        names.push_back(name);
    }

    return names;
}

std::vector<std::shared_ptr<ModelBase>> ModelRegistry::getLoadedModels() const {
    std::lock_guard lock(mutex_);

    std::vector<std::shared_ptr<ModelBase>> loaded;
    for (const auto& [_, entry] : models_) {
        if (entry.model->isLoaded()) {
            loaded.push_back(entry.model);
        }
    }

    return loaded;
}

std::shared_ptr<ModelBase> ModelRegistry::selectModel(
    const ModelSelectionCriteria& criteria,
    bool autoLoad
) {
    std::vector<std::shared_ptr<ModelBase>> allModels;

    {
        std::lock_guard lock(mutex_);
        for (const auto& [_, entry] : models_) {
            allModels.push_back(entry.model);
        }
    }

    auto selected = selectionStrategy_->select(allModels, criteria);

    if (selected && autoLoad && !selected->isLoaded()) {
        selected->load();
    }

    return selected;
}

void ModelRegistry::setSelectionStrategy(std::unique_ptr<ModelSelectionStrategy> strategy) {
    std::lock_guard lock(mutex_);
    selectionStrategy_ = std::move(strategy);
}

uint64_t ModelRegistry::getTotalMemoryUsage() const {
    std::lock_guard lock(mutex_);

    uint64_t total = 0;
    for (const auto& [_, entry] : models_) {
        if (entry.model->isLoaded()) {
            total += entry.model->getMemoryUsage();
        }
    }

    return total;
}

void ModelRegistry::setMemoryLimit(uint64_t maxBytes) {
    std::lock_guard lock(mutex_);
    memoryLimit_ = maxBytes;

    Logger::getInstance().info(
        "Memory limit set to " + std::to_string(maxBytes / (1024 * 1024)) + " MB",
        "ModelRegistry"
    );
}

void ModelRegistry::setAutoEviction(bool enabled) {
    std::lock_guard lock(mutex_);
    autoEviction_ = enabled;
}

bool ModelRegistry::evictLRU() {
    std::lock_guard lock(mutex_);

    // Find least recently used loaded model
    std::string lruModel;
    std::chrono::system_clock::time_point oldestAccess = std::chrono::system_clock::now();

    for (const auto& [name, entry] : models_) {
        if (entry.model->isLoaded() && entry.lastAccessed < oldestAccess) {
            oldestAccess = entry.lastAccessed;
            lruModel = name;
        }
    }

    if (lruModel.empty()) {
        return false;  // No loaded models
    }

    models_[lruModel].model->unload();

    Logger::getInstance().warning(
        "LRU eviction: unloaded model " + lruModel,
        "ModelRegistry"
    );

    return true;
}

void ModelRegistry::clear() {
    std::lock_guard lock(mutex_);

    for (auto& [name, entry] : models_) {
        if (entry.model->isLoaded()) {
            entry.model->unload();
        }
    }

    models_.clear();

    Logger::getInstance().info(
        "Model registry cleared",
        "ModelRegistry"
    );
}

void ModelRegistry::updateAccessTime(const std::string& name) {
    auto it = models_.find(name);
    if (it != models_.end()) {
        it->second.lastAccessed = std::chrono::system_clock::now();
        it->second.accessCount++;
    }
}

bool ModelRegistry::wouldExceedMemoryLimit(uint64_t additionalBytes) const {
    if (memoryLimit_ == 0) {
        return false;  // No limit set
    }

    return (getTotalMemoryUsage() + additionalBytes) > memoryLimit_;
}

void ModelRegistry::evictUntilFreeMemory(uint64_t requiredBytes) {
    while (wouldExceedMemoryLimit(requiredBytes)) {
        if (!evictLRU()) {
            throw ResourceException(
                "Cannot free enough memory even after evicting all models",
                ErrorCode::RESOURCE_EXHAUSTED
            ).setResourceType("Memory");
        }
    }
}

// ============================================================================
// ModelLoader Implementation
// ============================================================================

std::map<ModelFormat, ModelLoader::ModelFactory> ModelLoader::factories_;
std::mutex ModelLoader::factoryMutex_;

std::shared_ptr<ModelBase> ModelLoader::loadFromFile(
    const std::string& filePath,
    std::function<void(double)> progressCallback
) {
    ModelFormat format = detectModelFormat(filePath);

    std::lock_guard lock(factoryMutex_);
    auto it = factories_.find(format);

    if (it == factories_.end()) {
        throw ModelException(
            "No factory registered for model format",
            ErrorCode::MODEL_INVALID_FORMAT
        ).setModelPath(filePath)
         .addContext("format", modelFormatToString(format));
    }

    auto model = it->second(filePath);
    model->load(progressCallback);

    return model;
}

ModelMetadata ModelLoader::createMetadataFromFile(const std::string& filePath) {
    ModelMetadata metadata;
    metadata.filePath = filePath;
    metadata.format = detectModelFormat(filePath);

    if (std::filesystem::exists(filePath)) {
        metadata.fileSize = std::filesystem::file_size(filePath);
    }

    // TODO: Parse actual metadata from file headers

    return metadata;
}

bool ModelLoader::validateFile(const std::string& filePath) {
    if (!std::filesystem::exists(filePath)) {
        return false;
    }

    ModelFormat format = detectModelFormat(filePath);
    if (format == ModelFormat::UNKNOWN) {
        return false;
    }

    // TODO: Format-specific validation

    return true;
}

void ModelLoader::registerFactory(ModelFormat format, ModelFactory factory) {
    std::lock_guard lock(factoryMutex_);
    factories_[format] = std::move(factory);

    Logger::getInstance().info(
        "Model factory registered for format: " + modelFormatToString(format),
        "ModelLoader"
    );
}

} // namespace VersaAI
