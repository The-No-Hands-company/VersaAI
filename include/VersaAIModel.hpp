#pragma once

#include "VersaAIException.hpp"
#include <string>
#include <vector>
#include <map>
#include <memory>
#include <chrono>
#include <optional>
#include <cstdint>
#include <functional>

namespace VersaAI {

// ============================================================================
// Model Formats & Types
// ============================================================================

/**
 * @brief Supported model file formats
 */
enum class ModelFormat {
    GGUF,           // GGML Universal Format (llama.cpp)
    SAFETENSORS,    // SafeTensors (HuggingFace)
    ONNX,           // Open Neural Network Exchange
    PYTORCH,        // PyTorch (.pt, .pth)
    TENSORFLOW,     // TensorFlow SavedModel
    UNKNOWN
};

/**
 * @brief Model architecture types
 */
enum class ModelArchitecture {
    LLAMA,          // LLaMA/LLaMA2/LLaMA3
    GPT,            // GPT-2/GPT-3/GPT-J
    MISTRAL,        // Mistral
    MIXTRAL,        // Mixtral MoE
    GEMMA,          // Google Gemma
    PHI,            // Microsoft Phi
    BERT,           // BERT variants
    T5,             // T5 variants
    CUSTOM,         // Custom architecture
    UNKNOWN
};

/**
 * @brief Model capabilities
 */
enum class ModelCapability {
    TEXT_GENERATION,    // Autoregressive text generation
    EMBEDDINGS,         // Text embeddings
    CLASSIFICATION,     // Text classification
    QUESTION_ANSWERING, // Q&A
    SUMMARIZATION,      // Text summarization
    TRANSLATION,        // Language translation
    CODE_GENERATION,    // Code completion/generation
    CHAT,              // Chat/conversation
    MULTIMODAL         // Vision + Text
};

/**
 * @brief Quantization types
 */
enum class QuantizationType {
    NONE,       // FP32/FP16
    Q8_0,       // 8-bit quantization
    Q4_0,       // 4-bit quantization
    Q4_1,       // 4-bit with scales
    Q5_0,       // 5-bit quantization
    Q5_1,       // 5-bit with scales
    Q2_K,       // 2-bit K-quant
    Q3_K,       // 3-bit K-quant
    Q4_K,       // 4-bit K-quant
    Q5_K,       // 5-bit K-quant
    Q6_K        // 6-bit K-quant
};

// ============================================================================
// Model Metadata
// ============================================================================

/**
 * @brief Hardware requirements for a model
 */
struct HardwareRequirements {
    uint64_t minRAM = 0;           // Minimum RAM in bytes
    uint64_t recommendedRAM = 0;   // Recommended RAM in bytes
    uint64_t minVRAM = 0;          // Minimum VRAM in bytes (0 = CPU only)
    uint32_t minCores = 1;         // Minimum CPU cores
    bool requiresGPU = false;      // GPU required
    bool supportsCUDA = false;     // CUDA support
    bool supportsROCm = false;     // ROCm support
    bool supportsMetal = false;    // Metal support (macOS)
};

/**
 * @brief Performance characteristics of a model
 */
struct PerformanceMetrics {
    double tokensPerSecond = 0.0;      // Average tokens/sec
    double firstTokenLatencyMs = 0.0;  // Time to first token (ms)
    double avgTokenLatencyMs = 0.0;    // Average per-token latency (ms)
    uint64_t memoryUsageBytes = 0;     // Actual memory usage
    std::chrono::system_clock::time_point lastMeasured;
};

/**
 * @brief Comprehensive model metadata
 */
struct ModelMetadata {
    // Identity
    std::string name;                           // Model name
    std::string version;                        // Version string
    std::string description;                    // Human-readable description
    std::string author;                         // Model author/organization
    std::string license;                        // License (e.g., "MIT", "Apache-2.0")

    // Technical specs
    ModelFormat format = ModelFormat::UNKNOWN;
    ModelArchitecture architecture = ModelArchitecture::UNKNOWN;
    std::vector<ModelCapability> capabilities;
    QuantizationType quantization = QuantizationType::NONE;

    // Model parameters
    uint64_t parameterCount = 0;               // Total parameters
    uint32_t contextLength = 0;                 // Max context window
    uint32_t vocabularySize = 0;                // Vocabulary size
    uint32_t hiddenSize = 0;                    // Hidden dimension
    uint32_t numLayers = 0;                     // Number of layers
    uint32_t numHeads = 0;                      // Number of attention heads

    // File information
    std::string filePath;                       // Absolute path to model file
    uint64_t fileSize = 0;                      // File size in bytes
    std::string checksum;                       // SHA256 checksum
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point modifiedAt;

    // Requirements & performance
    HardwareRequirements requirements;
    PerformanceMetrics performance;

    // Custom metadata
    std::map<std::string, std::string> customFields;

    /**
     * @brief Check if model has specific capability
     */
    bool hasCapability(ModelCapability cap) const;

    /**
     * @brief Add custom metadata field
     */
    void addCustomField(const std::string& key, const std::string& value);

    /**
     * @brief Get custom field value
     */
    std::optional<std::string> getCustomField(const std::string& key) const;

    /**
     * @brief Serialize metadata to JSON
     */
    std::string toJson() const;

    /**
     * @brief Load metadata from JSON
     */
    static ModelMetadata fromJson(const std::string& json);

    /**
     * @brief Validate metadata completeness
     */
    bool validate() const;
};

// ============================================================================
// Model State
// ============================================================================

/**
 * @brief Model loading state
 */
enum class ModelState {
    UNLOADED,       // Not loaded in memory
    LOADING,        // Currently loading
    LOADED,         // Fully loaded and ready
    UNLOADING,      // Currently unloading
    ERROR           // Error state
};

// ============================================================================
// Model Base Class
// ============================================================================

/**
 * @brief Abstract base class for all model implementations
 *
 * Provides interface for model loading, inference, and resource management.
 * Concrete implementations handle specific model formats and architectures.
 */
class ModelBase {
public:
    explicit ModelBase(const ModelMetadata& metadata);
    virtual ~ModelBase();

    // Disable copy, enable move
    ModelBase(const ModelBase&) = delete;
    ModelBase& operator=(const ModelBase&) = delete;
    ModelBase(ModelBase&&) = default;
    ModelBase& operator=(ModelBase&&) = default;

    // ========================================================================
    // Lifecycle Management
    // ========================================================================

    /**
     * @brief Load model into memory
     * @param progressCallback Optional callback for loading progress (0.0-1.0)
     * @throws ModelException if loading fails
     */
    virtual void load(std::function<void(double)> progressCallback = nullptr) = 0;

    /**
     * @brief Unload model from memory
     */
    virtual void unload() = 0;

    /**
     * @brief Check if model is loaded
     */
    bool isLoaded() const { return state_ == ModelState::LOADED; }

    /**
     * @brief Get current loading state
     */
    ModelState getState() const { return state_; }

    // ========================================================================
    // Inference Interface
    // ========================================================================

    /**
     * @brief Tokenize text to token IDs
     * @param text Input text
     * @return Vector of token IDs
     */
    virtual std::vector<int32_t> tokenize(const std::string& text) = 0;

    /**
     * @brief Detokenize token IDs to text
     * @param tokens Vector of token IDs
     * @return Decoded text
     */
    virtual std::string detokenize(const std::vector<int32_t>& tokens) = 0;

    /**
     * @brief Generate text from prompt
     * @param prompt Input prompt
     * @param maxTokens Maximum tokens to generate
     * @param temperature Sampling temperature (0.0-2.0)
     * @param topP Nucleus sampling threshold
     * @return Generated text
     */
    virtual std::string generate(
        const std::string& prompt,
        uint32_t maxTokens = 512,
        double temperature = 0.7,
        double topP = 0.9
    ) = 0;

    /**
     * @brief Get embeddings for text
     * @param text Input text
     * @return Embedding vector
     * @throws ModelException if model doesn't support embeddings
     */
    virtual std::vector<float> getEmbeddings(const std::string& text);

    // ========================================================================
    // Metadata & Information
    // ========================================================================

    const ModelMetadata& getMetadata() const { return metadata_; }

    std::string getName() const { return metadata_.name; }
    std::string getVersion() const { return metadata_.version; }
    ModelFormat getFormat() const { return metadata_.format; }
    ModelArchitecture getArchitecture() const { return metadata_.architecture; }

    /**
     * @brief Get current memory usage in bytes
     */
    virtual uint64_t getMemoryUsage() const = 0;

    /**
     * @brief Update performance metrics
     */
    void updatePerformanceMetrics(const PerformanceMetrics& metrics);

    const PerformanceMetrics& getPerformanceMetrics() const {
        return metadata_.performance;
    }

    // ========================================================================
    // Validation
    // ========================================================================

    /**
     * @brief Validate model file integrity
     * @throws ModelException if validation fails
     */
    virtual void validate();

protected:
    ModelMetadata metadata_;
    ModelState state_ = ModelState::UNLOADED;

    /**
     * @brief Set model state (thread-safe)
     */
    void setState(ModelState newState);

    /**
     * @brief Log model operation
     */
    void logOperation(const std::string& operation, const std::string& details = "") const;
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * @brief Convert ModelFormat to string
 */
std::string modelFormatToString(ModelFormat format);

/**
 * @brief Convert string to ModelFormat
 */
ModelFormat stringToModelFormat(const std::string& str);

/**
 * @brief Convert ModelArchitecture to string
 */
std::string modelArchitectureToString(ModelArchitecture arch);

/**
 * @brief Convert ModelCapability to string
 */
std::string modelCapabilityToString(ModelCapability cap);

/**
 * @brief Convert QuantizationType to string
 */
std::string quantizationTypeToString(QuantizationType quant);

/**
 * @brief Detect model format from file extension
 */
ModelFormat detectModelFormat(const std::string& filePath);

/**
 * @brief Calculate SHA256 checksum of file
 */
std::string calculateChecksum(const std::string& filePath);

} // namespace VersaAI
