/**
 * @file VersaAIModelFormat.hpp
 * @brief Model format definitions and metadata structures
 *
 * Supports multiple model formats:
 * - GGUF (GPT-Generated Unified Format) - llama.cpp format
 * - GGML (legacy format)
 * - ONNX (Open Neural Network Exchange)
 * - SafeTensors (Hugging Face format)
 * - PyTorch (.pth, .pt)
 * - Custom VersaAI format
 */

#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <variant>
#include <optional>
#include <chrono>
#include <functional>

namespace VersaAI {
namespace Model {

// ============================================================================
// Model Format Enumeration
// ============================================================================

/**
 * @brief Supported model file formats
 */
enum class ModelFormat {
    Unknown,        ///< Unknown/unsupported format
    GGUF,          ///< GGUF format (llama.cpp v2+)
    GGML,          ///< GGML format (llama.cpp v1)
    ONNX,          ///< ONNX format
    SafeTensors,   ///< SafeTensors format (Hugging Face)
    PyTorch,       ///< PyTorch checkpoint (.pth, .pt)
    TensorFlow,    ///< TensorFlow SavedModel
    VersaAI        ///< Custom VersaAI format
};

/**
 * @brief Convert format to string
 */
inline std::string formatToString(ModelFormat format) {
    switch (format) {
        case ModelFormat::GGUF: return "GGUF";
        case ModelFormat::GGML: return "GGML";
        case ModelFormat::ONNX: return "ONNX";
        case ModelFormat::SafeTensors: return "SafeTensors";
        case ModelFormat::PyTorch: return "PyTorch";
        case ModelFormat::TensorFlow: return "TensorFlow";
        case ModelFormat::VersaAI: return "VersaAI";
        default: return "Unknown";
    }
}

// ============================================================================
// Model Quantization
// ============================================================================

/**
 * @brief Quantization types for model compression
 */
enum class QuantizationType {
    None,          ///< No quantization (FP32)
    F16,           ///< 16-bit floating point
    Q4_0,          ///< 4-bit quantization (symmetric)
    Q4_1,          ///< 4-bit quantization (asymmetric)
    Q5_0,          ///< 5-bit quantization (symmetric)
    Q5_1,          ///< 5-bit quantization (asymmetric)
    Q8_0,          ///< 8-bit quantization
    Q8_1,          ///< 8-bit quantization (improved)
    K_QUANTS,      ///< K-quants (mixed precision)
    IQ_QUANTS,     ///< I-quants (importance-weighted)
    Custom         ///< Custom quantization scheme
};

inline std::string quantizationToString(QuantizationType quant) {
    switch (quant) {
        case QuantizationType::None: return "FP32";
        case QuantizationType::F16: return "FP16";
        case QuantizationType::Q4_0: return "Q4_0";
        case QuantizationType::Q4_1: return "Q4_1";
        case QuantizationType::Q5_0: return "Q5_0";
        case QuantizationType::Q5_1: return "Q5_1";
        case QuantizationType::Q8_0: return "Q8_0";
        case QuantizationType::Q8_1: return "Q8_1";
        case QuantizationType::K_QUANTS: return "K-Quants";
        case QuantizationType::IQ_QUANTS: return "I-Quants";
        case QuantizationType::Custom: return "Custom";
        default: return "Unknown";
    }
}

// ============================================================================
// Model Architecture
// ============================================================================

/**
 * @brief Model architecture types
 */
enum class ModelArchitecture {
    Unknown,
    Transformer,    ///< Generic transformer
    GPT,           ///< GPT-style decoder-only
    BERT,          ///< BERT-style encoder-only
    T5,            ///< T5-style encoder-decoder
    LLaMA,         ///< LLaMA architecture
    Mistral,       ///< Mistral architecture
    Falcon,        ///< Falcon architecture
    MPT,           ///< MosaicML MPT
    Bloom,         ///< BLOOM architecture
    StableLM,      ///< StableLM architecture
    Phi,           ///< Microsoft Phi
    Gemma,         ///< Google Gemma
    Qwen,          ///< Alibaba Qwen
    Custom         ///< Custom architecture
};

inline std::string architectureToString(ModelArchitecture arch) {
    switch (arch) {
        case ModelArchitecture::Transformer: return "Transformer";
        case ModelArchitecture::GPT: return "GPT";
        case ModelArchitecture::BERT: return "BERT";
        case ModelArchitecture::T5: return "T5";
        case ModelArchitecture::LLaMA: return "LLaMA";
        case ModelArchitecture::Mistral: return "Mistral";
        case ModelArchitecture::Falcon: return "Falcon";
        case ModelArchitecture::MPT: return "MPT";
        case ModelArchitecture::Bloom: return "BLOOM";
        case ModelArchitecture::StableLM: return "StableLM";
        case ModelArchitecture::Phi: return "Phi";
        case ModelArchitecture::Gemma: return "Gemma";
        case ModelArchitecture::Qwen: return "Qwen";
        case ModelArchitecture::Custom: return "Custom";
        default: return "Unknown";
    }
}

// ============================================================================
// Model Capabilities
// ============================================================================

/**
 * @brief Model capabilities flags
 */
enum class ModelCapability : uint32_t {
    TextGeneration      = 1 << 0,   ///< Generate text
    TextCompletion      = 1 << 1,   ///< Complete text
    ChatConversation    = 1 << 2,   ///< Chat mode
    CodeGeneration      = 1 << 3,   ///< Generate code
    Embedding           = 1 << 4,   ///< Generate embeddings
    Classification      = 1 << 5,   ///< Text classification
    Translation         = 1 << 6,   ///< Language translation
    Summarization       = 1 << 7,   ///< Text summarization
    QuestionAnswering   = 1 << 8,   ///< Q&A
    FunctionCalling     = 1 << 9,   ///< Function/tool calling
    VisionLanguage      = 1 << 10,  ///< Multimodal (vision+language)
    Audio               = 1 << 11,  ///< Audio processing
    FineTuning          = 1 << 12,  ///< Supports fine-tuning
    RLHF                = 1 << 13,  ///< RLHF-trained
    InstructionTuned    = 1 << 14,  ///< Instruction-tuned
};

using ModelCapabilities = uint32_t;

inline bool hasCapability(ModelCapabilities caps, ModelCapability cap) {
    return (caps & static_cast<uint32_t>(cap)) != 0;
}

inline void addCapability(ModelCapabilities& caps, ModelCapability cap) {
    caps |= static_cast<uint32_t>(cap);
}

// ============================================================================
// Tensor Data Type
// ============================================================================

/**
 * @brief Tensor data types
 */
enum class TensorDataType {
    Float32,    ///< 32-bit float
    Float16,    ///< 16-bit float
    BFloat16,   ///< Brain float 16
    Int8,       ///< 8-bit integer
    Int16,      ///< 16-bit integer
    Int32,      ///< 32-bit integer
    Int64,      ///< 64-bit integer
    UInt8,      ///< Unsigned 8-bit
    UInt16,     ///< Unsigned 16-bit
    UInt32,     ///< Unsigned 32-bit
    Bool,       ///< Boolean
    Custom      ///< Custom type
};

inline size_t getTensorDataTypeSize(TensorDataType type) {
    switch (type) {
        case TensorDataType::Float32: return 4;
        case TensorDataType::Float16: return 2;
        case TensorDataType::BFloat16: return 2;
        case TensorDataType::Int8: return 1;
        case TensorDataType::Int16: return 2;
        case TensorDataType::Int32: return 4;
        case TensorDataType::Int64: return 8;
        case TensorDataType::UInt8: return 1;
        case TensorDataType::UInt16: return 2;
        case TensorDataType::UInt32: return 4;
        case TensorDataType::Bool: return 1;
        default: return 0;
    }
}

// ============================================================================
// Model Metadata Value
// ============================================================================

/**
 * @brief Variant type for model metadata values
 */
using MetadataValue = std::variant<
    std::string,
    int64_t,
    double,
    bool,
    std::vector<std::string>,
    std::vector<int64_t>,
    std::vector<double>
>;

// ============================================================================
// Model Metadata
// ============================================================================

/**
 * @brief Complete model metadata
 */
struct ModelMetadata {
    // Basic Information
    std::string name;
    std::string version;
    std::string description;
    std::string author;
    std::string license;

    // Architecture
    ModelArchitecture architecture = ModelArchitecture::Unknown;
    std::string architectureVariant;  ///< e.g., "LLaMA-2-7B"

    // Format
    ModelFormat format = ModelFormat::Unknown;
    QuantizationType quantization = QuantizationType::None;

    // Model Size
    uint64_t parameterCount = 0;        ///< Total parameters
    uint64_t fileSizeBytes = 0;         ///< File size on disk
    uint64_t memoryRequiredBytes = 0;   ///< Required RAM

    // Context
    uint32_t contextLength = 0;         ///< Max context window
    uint32_t embeddingDimension = 0;    ///< Embedding size
    uint32_t vocabularySize = 0;        ///< Vocab size
    uint32_t numLayers = 0;             ///< Number of layers
    uint32_t numHeads = 0;              ///< Attention heads

    // Capabilities
    ModelCapabilities capabilities = 0;

    // Training Information
    std::optional<std::string> trainingDataset;
    std::optional<std::chrono::system_clock::time_point> trainedAt;
    std::optional<uint64_t> trainingSteps;

    // Tokenizer
    std::string tokenizerType;          ///< e.g., "BPE", "SentencePiece"
    std::optional<std::string> tokenizerPath;

    // Special Tokens
    std::optional<std::string> bosToken;    ///< Beginning of sequence
    std::optional<std::string> eosToken;    ///< End of sequence
    std::optional<std::string> padToken;    ///< Padding token
    std::optional<std::string> unkToken;    ///< Unknown token

    // Additional metadata (flexible key-value store)
    std::unordered_map<std::string, MetadataValue> additionalMetadata;

    // File Information
    std::string filePath;
    std::chrono::system_clock::time_point loadedAt;

    /**
     * @brief Get metadata value by key
     */
    template<typename T>
    std::optional<T> getMetadata(const std::string& key) const {
        auto it = additionalMetadata.find(key);
        if (it == additionalMetadata.end()) {
            return std::nullopt;
        }

        try {
            return std::get<T>(it->second);
        } catch (const std::bad_variant_access&) {
            return std::nullopt;
        }
    }

    /**
     * @brief Set metadata value
     */
    template<typename T>
    void setMetadata(const std::string& key, const T& value) {
        additionalMetadata[key] = value;
    }

    /**
     * @brief Get human-readable summary
     */
    std::string getSummary() const {
        std::string summary;
        summary += "Model: " + name + "\n";
        summary += "Architecture: " + architectureToString(architecture);
        if (!architectureVariant.empty()) {
            summary += " (" + architectureVariant + ")";
        }
        summary += "\n";
        summary += "Format: " + formatToString(format) + "\n";
        summary += "Quantization: " + quantizationToString(quantization) + "\n";
        summary += "Parameters: " + std::to_string(parameterCount / 1000000) + "M\n";
        summary += "Context Length: " + std::to_string(contextLength) + "\n";
        summary += "Memory Required: " + std::to_string(memoryRequiredBytes / 1024 / 1024) + " MB\n";
        return summary;
    }
};

// ============================================================================
// Model Load Options
// ============================================================================

/**
 * @brief Options for loading a model
 */
struct ModelLoadOptions {
    // Memory Management
    bool useMemoryMapping = true;       ///< Use mmap for large models
    bool lockMemory = false;            ///< Lock pages in RAM (prevents swapping)
    size_t preAllocateBytes = 0;        ///< Pre-allocate memory

    // Device Selection
    enum class Device {
        Auto,       ///< Automatically select best device
        CPU,        ///< Force CPU
        CUDA,       ///< Force CUDA (NVIDIA GPU)
        ROCm,       ///< Force ROCm (AMD GPU)
        Metal,      ///< Force Metal (Apple Silicon)
        Vulkan,     ///< Force Vulkan
        OpenCL      ///< Force OpenCL
    };
    Device device = Device::Auto;
    int deviceId = 0;                   ///< Device index (for multi-GPU)

    // Performance
    uint32_t numThreads = 0;            ///< 0 = auto-detect
    bool enableF16 = true;              ///< Use FP16 for KV cache
    bool enableFlashAttention = true;   ///< Use flash attention if available

    // Context
    uint32_t contextSize = 0;           ///< Override context size (0 = use model default)
    uint32_t batchSize = 512;           ///< Batch size for processing

    // GPU Layers (for offloading)
    int32_t numGPULayers = -1;          ///< Number of layers to offload (-1 = all)

    // Validation
    bool validateChecksum = true;       ///< Validate file integrity
    bool validateTensors = true;        ///< Validate tensor shapes/types

    // Progress Callback
    using ProgressCallback = std::function<void(float progress, const std::string& status)>;
    ProgressCallback onProgress;
};

// ============================================================================
// Tensor Information
// ============================================================================

/**
 * @brief Information about a single tensor in the model
 */
struct TensorInfo {
    std::string name;
    TensorDataType dataType;
    std::vector<uint64_t> shape;
    uint64_t numElements = 0;
    uint64_t sizeBytes = 0;
    uint64_t offset = 0;                ///< Offset in file

    /**
     * @brief Calculate total number of elements
     */
    uint64_t calculateNumElements() const {
        uint64_t total = 1;
        for (auto dim : shape) {
            total *= dim;
        }
        return total;
    }

    /**
     * @brief Get shape as string (e.g., "[4096, 768]")
     */
    std::string getShapeString() const {
        std::string result = "[";
        for (size_t i = 0; i < shape.size(); ++i) {
            if (i > 0) result += ", ";
            result += std::to_string(shape[i]);
        }
        result += "]";
        return result;
    }
};

} // namespace Model
} // namespace VersaAI
