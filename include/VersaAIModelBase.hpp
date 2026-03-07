/**
 * @file VersaAIModelBase.hpp
 * @brief Base class for all AI models in VersaAI
 *
 * Provides common interface and functionality for models
 * regardless of their format or architecture.
 */

#pragma once

#include "VersaAIModelFormat.hpp"
#include "VersaAIRegistry.hpp"
#include <memory>
#include <string>
#include <vector>

namespace VersaAI {
namespace Model {

// Forward declarations
class IModelLoader;

// ============================================================================
// Model State
// ============================================================================

/**
 * @brief Current state of a model
 */
enum class ModelState {
    Unloaded,       ///< Not loaded
    Loading,        ///< Currently loading
    Ready,          ///< Loaded and ready for inference
    Unloading,      ///< Currently unloading
    Failed          ///< Load/inference failed
};

inline std::string modelStateToString(ModelState state) {
    switch (state) {
        case ModelState::Unloaded: return "Unloaded";
        case ModelState::Loading: return "Loading";
        case ModelState::Ready: return "Ready";
        case ModelState::Unloading: return "Unloading";
        case ModelState::Failed: return "Failed";
        default: return "Unknown";
    }
}

// ============================================================================
// Model Base Class
// ============================================================================

/**
 * @brief Base class for all AI models
 *
 * Provides common interface for:
 * - Model lifecycle management
 * - Metadata access
 * - Resource management
 * - State tracking
 */
class ModelBase : public Registry::IInitializable, public Registry::IShutdownable {
public:
    virtual ~ModelBase() = default;

    /**
     * @brief Get model metadata
     */
    virtual const ModelMetadata& getMetadata() const = 0;

    /**
     * @brief Get current model state
     */
    virtual ModelState getState() const = 0;

    /**
     * @brief Check if model is ready for inference
     */
    virtual bool isReady() const {
        return getState() == ModelState::Ready;
    }

    /**
     * @brief Get memory usage in bytes
     */
    virtual uint64_t getMemoryUsage() const = 0;

    /**
     * @brief Validate model integrity
     */
    virtual bool validate() const = 0;

    /**
     * @brief Get model capabilities
     */
    virtual ModelCapabilities getCapabilities() const {
        return getMetadata().capabilities;
    }

    /**
     * @brief Check if model has specific capability
     */
    virtual bool hasCapability(ModelCapability cap) const {
        return VersaAI::Model::hasCapability(getCapabilities(), cap);
    }

    /**
     * @brief Get human-readable model summary
     */
    virtual std::string getSummary() const {
        return getMetadata().getSummary();
    }

    // IInitializable interface
    bool initialize() override = 0;
    int getInitializationPriority() const { return 100; }

    // IShutdownable interface
    void shutdown() override = 0;
    int getShutdownPriority() const { return 100; }
};

// ============================================================================
// Generic Model Implementation
// ============================================================================

/**
 * @brief Generic model implementation
 *
 * Used when specific model class is not needed
 */
class GenericModel : public ModelBase {
public:
    explicit GenericModel(ModelMetadata metadata)
        : metadata_(std::move(metadata))
        , state_(ModelState::Unloaded)
        , memoryUsage_(0)
    {}

    ~GenericModel() override {
        if (state_ == ModelState::Ready) {
            shutdown();
        }
    }

    // ModelBase interface
    const ModelMetadata& getMetadata() const override {
        return metadata_;
    }

    ModelState getState() const override {
        return state_;
    }

    uint64_t getMemoryUsage() const override {
        return memoryUsage_;
    }

    bool validate() const override {
        return state_ == ModelState::Ready || state_ == ModelState::Unloaded;
    }

    // IInitializable interface
    bool initialize() override {
        if (state_ == ModelState::Ready) {
            return true;
        }

        state_ = ModelState::Loading;

        // Initialize model (placeholder - actual loading done by loader)
        Logger::getInstance().info(
            "Initializing model: " + metadata_.name + " [" + formatToString(metadata_.format) + ", " + architectureToString(metadata_.architecture) + "]",
            "GenericModel"
        );

        state_ = ModelState::Ready;
        memoryUsage_ = metadata_.memoryRequiredBytes;

        return true;
    }

    // IShutdownable interface
    void shutdown() override {
        if (state_ == ModelState::Unloaded) {
            return;
        }

        state_ = ModelState::Unloading;

        Logger::getInstance().info(
            "Shutting down model: " + metadata_.name,
            "GenericModel"
        );

        // Release resources
        memoryUsage_ = 0;
        state_ = ModelState::Unloaded;
    }

    /**
     * @brief Set model state (for loader use)
     */
    void setState(ModelState state) {
        state_ = state;
    }

    /**
     * @brief Set memory usage (for loader use)
     */
    void setMemoryUsage(uint64_t bytes) {
        memoryUsage_ = bytes;
    }

protected:
    ModelMetadata metadata_;
    ModelState state_;
    uint64_t memoryUsage_;
};

// ============================================================================
// Model Handle (Smart Pointer Wrapper)
// ============================================================================

/**
 * @brief Convenience typedef for model smart pointer
 */
using ModelHandle = std::shared_ptr<ModelBase>;

/**
 * @brief Create a model handle
 */
template<typename T, typename... Args>
ModelHandle makeModel(Args&&... args) {
    return std::make_shared<T>(std::forward<Args>(args)...);
}

} // namespace Model
} // namespace VersaAI
