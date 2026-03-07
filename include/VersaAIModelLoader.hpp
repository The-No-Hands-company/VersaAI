/**
 * @file VersaAIModelLoader.hpp
 * @brief Model loading infrastructure with support for multiple formats
 *
 * Features:
 * - Multi-format support (GGUF, ONNX, SafeTensors, etc.)
 * - Memory-mapped loading for efficiency
 * - Metadata extraction
 * - Validation and checksums
 * - Progress callbacks
 * - Error recovery
 */

#pragma once

#include "VersaAIModelFormat.hpp"
#include "VersaAIException.hpp"
#include "VersaAILogger.hpp"
#include <filesystem>
#include <fstream>
#include <memory>
#include <string>
#include <vector>
#include <functional>

namespace VersaAI {
namespace Model {

// ============================================================================
// Model Loader Interface
// ============================================================================

/**
 * @brief Abstract base class for model loaders
 *
 * Each format (GGUF, ONNX, etc.) implements this interface
 */
class IModelLoader {
public:
    virtual ~IModelLoader() = default;

    /**
     * @brief Check if this loader can handle the given file
     * @param filePath Path to model file
     * @return true if this loader supports the format
     */
    virtual bool canLoad(const std::filesystem::path& filePath) const = 0;

    /**
     * @brief Load model metadata without loading weights
     * @param filePath Path to model file
     * @return Model metadata
     * @throws ModelException if loading fails
     */
    virtual ModelMetadata loadMetadata(const std::filesystem::path& filePath) const = 0;

    /**
     * @brief Load complete model
     * @param filePath Path to model file
     * @param options Loading options
     * @return Loaded model instance
     * @throws ModelException if loading fails
     */
    virtual std::shared_ptr<class ModelBase> load(
        const std::filesystem::path& filePath,
        const ModelLoadOptions& options = ModelLoadOptions()
    ) = 0;

    /**
     * @brief Get list of tensors in the model file
     * @param filePath Path to model file
     * @return Vector of tensor information
     */
    virtual std::vector<TensorInfo> getTensorList(
        const std::filesystem::path& filePath
    ) const = 0;

    /**
     * @brief Validate model file integrity
     * @param filePath Path to model file
     * @return true if file is valid
     */
    virtual bool validate(const std::filesystem::path& filePath) const = 0;

    /**
     * @brief Get supported format
     */
    virtual ModelFormat getFormat() const = 0;
};

// ============================================================================
// Model Loader Factory
// ============================================================================

/**
 * @brief Factory for creating appropriate model loaders
 */
class ModelLoaderFactory {
public:
    static ModelLoaderFactory& getInstance();

    /**
     * @brief Register a model loader for a specific format
     */
    void registerLoader(
        ModelFormat format,
        std::function<std::unique_ptr<IModelLoader>()> factory
    );

    /**
     * @brief Get loader for a specific format
     */
    std::unique_ptr<IModelLoader> getLoader(ModelFormat format) const;

    /**
     * @brief Auto-detect format and get appropriate loader
     * @param filePath Path to model file
     * @return Appropriate loader or nullptr if format not recognized
     */
    std::unique_ptr<IModelLoader> getLoaderForFile(
        const std::filesystem::path& filePath
    ) const;

    /**
     * @brief Detect model format from file
     */
    ModelFormat detectFormat(const std::filesystem::path& filePath) const;

    /**
     * @brief Get list of all supported formats
     */
    std::vector<ModelFormat> getSupportedFormats() const;

private:
    ModelLoaderFactory() = default;

    std::unordered_map<
        ModelFormat,
        std::function<std::unique_ptr<IModelLoader>()>
    > loaderFactories_;

    mutable std::mutex mutex_;
};

// ============================================================================
// File Format Detection Utilities
// ============================================================================

/**
 * @brief Utility functions for detecting file formats
 */
class FormatDetector {
public:
    /**
     * @brief Detect format from file extension
     */
    static ModelFormat detectFromExtension(const std::filesystem::path& filePath);

    /**
     * @brief Detect format from file magic bytes
     */
    static ModelFormat detectFromMagic(const std::filesystem::path& filePath);

    /**
     * @brief Read file magic bytes (first 16 bytes)
     */
    static std::vector<uint8_t> readMagic(const std::filesystem::path& filePath);

    /**
     * @brief Check if file exists and is readable
     */
    static bool validatePath(const std::filesystem::path& filePath);

    /**
     * @brief Get file size
     */
    static uint64_t getFileSize(const std::filesystem::path& filePath);
};

// ============================================================================
// Memory-Mapped File Handler
// ============================================================================

/**
 * @brief RAII wrapper for memory-mapped files
 *
 * Provides efficient access to large model files
 */
class MemoryMappedFile {
public:
    MemoryMappedFile() = default;
    ~MemoryMappedFile();

    // No copying
    MemoryMappedFile(const MemoryMappedFile&) = delete;
    MemoryMappedFile& operator=(const MemoryMappedFile&) = delete;

    // Allow moving
    MemoryMappedFile(MemoryMappedFile&& other) noexcept;
    MemoryMappedFile& operator=(MemoryMappedFile&& other) noexcept;

    /**
     * @brief Open file for memory mapping
     */
    bool open(const std::filesystem::path& filePath, bool readOnly = true);

    /**
     * @brief Close memory-mapped file
     */
    void close();

    /**
     * @brief Check if file is open
     */
    bool isOpen() const { return data_ != nullptr; }

    /**
     * @brief Get pointer to mapped memory
     */
    const void* data() const { return data_; }
    void* data() { return data_; }

    /**
     * @brief Get file size
     */
    size_t size() const { return size_; }

    /**
     * @brief Get data at specific offset
     */
    template<typename T>
    const T* at(size_t offset) const {
        if (offset + sizeof(T) > size_) {
            throw ModelException(
                "Memory-mapped file access out of bounds",
                ErrorCode::MODEL_INVALID_FILE
            );
        }
        return reinterpret_cast<const T*>(
            static_cast<const uint8_t*>(data_) + offset
        );
    }

    /**
     * @brief Read data at offset
     */
    void read(size_t offset, void* dest, size_t length) const;

    /**
     * @brief Lock pages in memory (prevent swapping)
     */
    bool lock();

    /**
     * @brief Unlock pages
     */
    void unlock();

private:
    void* data_ = nullptr;
    size_t size_ = 0;
    bool locked_ = false;

#ifdef _WIN32
    void* fileHandle_ = nullptr;
    void* mappingHandle_ = nullptr;
#else
    int fileDescriptor_ = -1;
#endif
};

// ============================================================================
// Model File Reader (Non-memory-mapped alternative)
// ============================================================================

/**
 * @brief Traditional file reader for smaller models
 */
class ModelFileReader {
public:
    explicit ModelFileReader(const std::filesystem::path& filePath);
    ~ModelFileReader() = default;

    /**
     * @brief Read bytes at specific offset
     */
    std::vector<uint8_t> read(size_t offset, size_t length);

    /**
     * @brief Read typed data at offset
     */
    template<typename T>
    T read(size_t offset) {
        T value;
        file_.seekg(offset);
        file_.read(reinterpret_cast<char*>(&value), sizeof(T));
        if (!file_) {
            throw ModelException(
                "Failed to read from model file",
                ErrorCode::MODEL_LOAD_FAILED
            );
        }
        return value;
    }

    /**
     * @brief Read string at offset
     */
    std::string readString(size_t offset, size_t length);

    /**
     * @brief Get file size
     */
    size_t size() const { return fileSize_; }

    /**
     * @brief Check if file is open
     */
    bool isOpen() const { return file_.is_open(); }

private:
    std::ifstream file_;
    size_t fileSize_;
};

// ============================================================================
// Progress Tracker
// ============================================================================

/**
 * @brief Helper for tracking and reporting loading progress
 */
class LoadProgressTracker {
public:
    explicit LoadProgressTracker(ModelLoadOptions::ProgressCallback callback)
        : callback_(callback)
        , totalSteps_(0)
        , currentStep_(0)
    {}

    /**
     * @brief Set total number of steps
     */
    void setTotalSteps(size_t total) {
        totalSteps_ = total;
        currentStep_ = 0;
    }

    /**
     * @brief Report progress
     */
    void report(const std::string& status) {
        if (callback_) {
            float progress = totalSteps_ > 0
                ? static_cast<float>(currentStep_) / totalSteps_
                : 0.0f;
            callback_(progress, status);
        }
    }

    /**
     * @brief Advance to next step
     */
    void next(const std::string& status) {
        currentStep_++;
        report(status);
    }

    /**
     * @brief Complete progress
     */
    void complete(const std::string& status) {
        currentStep_ = totalSteps_;
        report(status);
    }

private:
    ModelLoadOptions::ProgressCallback callback_;
    size_t totalSteps_;
    size_t currentStep_;
};

// ============================================================================
// Helper Functions
// ============================================================================

/**
 * @brief Load model with auto-detection
 */
inline std::shared_ptr<ModelBase> loadModel(
    const std::filesystem::path& filePath,
    const ModelLoadOptions& options = ModelLoadOptions()
) {
    auto& factory = ModelLoaderFactory::getInstance();

    // Detect format
    auto format = factory.detectFormat(filePath);
    if (format == ModelFormat::Unknown) {
        throw ModelException(
            "Unsupported model format: " + filePath.string(),
            ErrorCode::MODEL_UNSUPPORTED_FORMAT
        );
    }

    // Get appropriate loader
    auto loader = factory.getLoaderForFile(filePath);
    if (!loader) {
        throw ModelException(
            "No loader available for format: " + formatToString(format),
            ErrorCode::MODEL_LOADER_NOT_FOUND
        );
    }

    // Load model
    Logger::getInstance().info(
        "Loading model: " + filePath.filename().string() + " [" + formatToString(format) + "]",
        "ModelLoader"
    );

    return loader->load(filePath, options);
}

/**
 * @brief Load model metadata only
 */
inline ModelMetadata loadModelMetadata(const std::filesystem::path& filePath) {
    auto& factory = ModelLoaderFactory::getInstance();

    auto format = factory.detectFormat(filePath);
    if (format == ModelFormat::Unknown) {
        throw ModelException(
            "Unsupported model format: " + filePath.string(),
            ErrorCode::MODEL_UNSUPPORTED_FORMAT
        );
    }

    auto loader = factory.getLoaderForFile(filePath);
    if (!loader) {
        throw ModelException(
            "No loader available for format: " + formatToString(format),
            ErrorCode::MODEL_LOADER_NOT_FOUND
        );
    }

    return loader->loadMetadata(filePath);
}

} // namespace Model
} // namespace VersaAI
