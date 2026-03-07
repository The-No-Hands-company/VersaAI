/**
 * @file VersaAIGGUFLoader.hpp
 * @brief GGUF (GPT-Generated Unified Format) model loader
 * 
 * Supports loading models in GGUF format (llama.cpp v2+).
 * GGUF is the standard format for LLaMA, Mistral, and other
 * popular open-source models.
 * 
 * Specification: https://github.com/ggerganov/ggml/blob/master/docs/gguf.md
 */

#pragma once

#include "VersaAIModelLoader.hpp"
#include <map>
#include <cstring>

namespace VersaAI {
namespace Model {

// ============================================================================
// GGUF Constants
// ============================================================================

namespace GGUF {
    // Magic number for GGUF files
    constexpr uint32_t MAGIC = 0x46554747; // "GGUF" in little-endian
    
    // Current version
    constexpr uint32_t VERSION_1 = 1;
    constexpr uint32_t VERSION_2 = 2;
    constexpr uint32_t VERSION_3 = 3;  // Latest
    
    // Metadata value types
    enum class MetadataType : uint32_t {
        UINT8 = 0,
        INT8 = 1,
        UINT16 = 2,
        INT16 = 3,
        UINT32 = 4,
        INT32 = 5,
        FLOAT32 = 6,
        BOOL = 7,
        STRING = 8,
        ARRAY = 9,
        UINT64 = 10,
        INT64 = 11,
        FLOAT64 = 12
    };
    
    // Well-known metadata keys
    namespace Keys {
        constexpr const char* GENERAL_ARCHITECTURE = "general.architecture";
        constexpr const char* GENERAL_NAME = "general.name";
        constexpr const char* GENERAL_AUTHOR = "general.author";
        constexpr const char* GENERAL_VERSION = "general.version";
        constexpr const char* GENERAL_DESCRIPTION = "general.description";
        constexpr const char* GENERAL_LICENSE = "general.license";
        constexpr const char* GENERAL_FILE_TYPE = "general.file_type";
        constexpr const char* GENERAL_QUANTIZATION = "general.quantization_version";
        
        constexpr const char* CONTEXT_LENGTH = "*.context_length";
        constexpr const char* EMBEDDING_LENGTH = "*.embedding_length";
        constexpr const char* BLOCK_COUNT = "*.block_count";
        constexpr const char* FEED_FORWARD_LENGTH = "*.feed_forward_length";
        constexpr const char* ATTENTION_HEAD_COUNT = "*.attention.head_count";
        constexpr const char* ATTENTION_HEAD_COUNT_KV = "*.attention.head_count_kv";
        constexpr const char* ROPE_DIMENSION_COUNT = "*.rope.dimension_count";
        constexpr const char* ROPE_FREQ_BASE = "*.rope.freq_base";
        
        constexpr const char* TOKENIZER_MODEL = "tokenizer.ggml.model";
        constexpr const char* TOKENIZER_VOCAB_SIZE = "tokenizer.ggml.vocab_size";
        constexpr const char* TOKENIZER_BOS = "tokenizer.ggml.bos_token_id";
        constexpr const char* TOKENIZER_EOS = "tokenizer.ggml.eos_token_id";
        constexpr const char* TOKENIZER_UNK = "tokenizer.ggml.unknown_token_id";
        constexpr const char* TOKENIZER_PAD = "tokenizer.ggml.padding_token_id";
    }
}

// ============================================================================
// GGUF File Header
// ============================================================================

struct GGUFHeader {
    uint32_t magic;         // "GGUF" magic number
    uint32_t version;       // GGUF version
    uint64_t tensorCount;   // Number of tensors
    uint64_t metadataCount; // Number of metadata key-value pairs
    
    bool isValid() const {
        return magic == GGUF::MAGIC &&
               (version >= GGUF::VERSION_1 && version <= GGUF::VERSION_3);
    }
};

// ============================================================================
// GGUF String (length-prefixed)
// ============================================================================

struct GGUFString {
    uint64_t length;
    std::string value;
    
    static GGUFString read(const void* data, size_t& offset);
};

// ============================================================================
// GGUF Metadata Value
// ============================================================================

struct GGUFMetadataValue {
    GGUF::MetadataType type;
    
    std::variant<
        uint8_t, int8_t,
        uint16_t, int16_t,
        uint32_t, int32_t,
        uint64_t, int64_t,
        float, double,
        bool,
        std::string,
        std::vector<GGUFMetadataValue>
    > value;
    
    static GGUFMetadataValue read(const void* data, size_t& offset);
    
    /**
     * @brief Get value as specific type
     */
    template<typename T>
    T as() const {
        return std::get<T>(value);
    }
    
    /**
     * @brief Try to get value as string
     */
    std::string asString() const;
    
    /**
     * @brief Try to get value as integer
     */
    int64_t asInt() const;
    
    /**
     * @brief Try to get value as float
     */
    double asFloat() const;
};

// ============================================================================
// GGUF Tensor Info
// ============================================================================

struct GGUFTensorInfo {
    std::string name;
    uint32_t numDimensions;
    std::vector<uint64_t> dimensions;
    uint32_t ggmlType;      // GGML tensor type
    uint64_t offset;        // Offset from start of tensor data
    
    static GGUFTensorInfo read(const void* data, size_t& offset);
    
    /**
     * @brief Calculate total size in bytes
     */
    uint64_t calculateSize() const;
    
    /**
     * @brief Convert to generic TensorInfo
     */
    TensorInfo toTensorInfo() const;
};

// ============================================================================
// GGUF Loader Implementation
// ============================================================================

/**
 * @brief Loader for GGUF format models
 */
class GGUFLoader : public IModelLoader {
public:
    GGUFLoader() = default;
    ~GGUFLoader() override = default;
    
    // IModelLoader implementation
    bool canLoad(const std::filesystem::path& filePath) const override;
    
    ModelMetadata loadMetadata(const std::filesystem::path& filePath) const override;
    
    std::shared_ptr<ModelBase> load(
        const std::filesystem::path& filePath,
        const ModelLoadOptions& options
    ) override;
    
    std::vector<TensorInfo> getTensorList(
        const std::filesystem::path& filePath
    ) const override;
    
    bool validate(const std::filesystem::path& filePath) const override;
    
    ModelFormat getFormat() const override {
        return ModelFormat::GGUF;
    }
    
    /**
     * @brief Parse GGUF file header
     */
    static GGUFHeader parseHeader(const std::filesystem::path& filePath);
    
    /**
     * @brief Read all metadata from GGUF file
     */
    static std::map<std::string, GGUFMetadataValue> readMetadata(
        const std::filesystem::path& filePath
    );
    
    /**
     * @brief Read tensor information from GGUF file
     */
    static std::vector<GGUFTensorInfo> readTensorInfo(
        const std::filesystem::path& filePath
    );
    
private:
    /**
     * @brief Extract model metadata from GGUF metadata map
     */
    ModelMetadata extractModelMetadata(
        const std::filesystem::path& filePath,
        const std::map<std::string, GGUFMetadataValue>& metadata,
        const std::vector<GGUFTensorInfo>& tensors
    ) const;
    
    /**
     * @brief Get metadata value with wildcard replacement
     */
    std::optional<GGUFMetadataValue> getMetadata(
        const std::map<std::string, GGUFMetadataValue>& metadata,
        const std::string& key,
        const std::string& architecture = ""
    ) const;
    
    /**
     * @brief Detect architecture from metadata
     */
    ModelArchitecture detectArchitecture(
        const std::map<std::string, GGUFMetadataValue>& metadata
    ) const;
    
    /**
     * @brief Detect quantization type
     */
    QuantizationType detectQuantization(
        const std::map<std::string, GGUFMetadataValue>& metadata
    ) const;
    
    /**
     * @brief Calculate total parameters
     */
    uint64_t calculateParameters(
        const std::vector<GGUFTensorInfo>& tensors
    ) const;
    
    /**
     * @brief Calculate memory requirements
     */
    uint64_t calculateMemoryRequirement(
        const std::vector<GGUFTensorInfo>& tensors,
        const ModelLoadOptions& options
    ) const;
};

// ============================================================================
// GGML Type Conversion
// ============================================================================

/**
 * @brief GGML tensor type enumeration
 */
enum class GGMLType : uint32_t {
    F32 = 0,
    F16 = 1,
    Q4_0 = 2,
    Q4_1 = 3,
    Q5_0 = 6,
    Q5_1 = 7,
    Q8_0 = 8,
    Q8_1 = 9,
    Q2_K = 10,
    Q3_K = 11,
    Q4_K = 12,
    Q5_K = 13,
    Q6_K = 14,
    Q8_K = 15,
    I8 = 16,
    I16 = 17,
    I32 = 18,
};

/**
 * @brief Convert GGML type to TensorDataType
 */
inline TensorDataType ggmlTypeToTensorType(GGMLType type) {
    switch (type) {
        case GGMLType::F32: return TensorDataType::Float32;
        case GGMLType::F16: return TensorDataType::Float16;
        case GGMLType::I8: return TensorDataType::Int8;
        case GGMLType::I16: return TensorDataType::Int16;
        case GGMLType::I32: return TensorDataType::Int32;
        default: return TensorDataType::Custom;
    }
}

/**
 * @brief Convert GGML type to QuantizationType
 */
inline QuantizationType ggmlTypeToQuantization(GGMLType type) {
    switch (type) {
        case GGMLType::F32: return QuantizationType::None;
        case GGMLType::F16: return QuantizationType::F16;
        case GGMLType::Q4_0: return QuantizationType::Q4_0;
        case GGMLType::Q4_1: return QuantizationType::Q4_1;
        case GGMLType::Q5_0: return QuantizationType::Q5_0;
        case GGMLType::Q5_1: return QuantizationType::Q5_1;
        case GGMLType::Q8_0: return QuantizationType::Q8_0;
        case GGMLType::Q8_1: return QuantizationType::Q8_1;
        case GGMLType::Q2_K:
        case GGMLType::Q3_K:
        case GGMLType::Q4_K:
        case GGMLType::Q5_K:
        case GGMLType::Q6_K:
        case GGMLType::Q8_K:
            return QuantizationType::K_QUANTS;
        default: return QuantizationType::Custom;
    }
}

/**
 * @brief Get size per element for GGML type
 */
inline size_t getGGMLTypeSize(GGMLType type) {
    switch (type) {
        case GGMLType::F32: return 4;
        case GGMLType::F16: return 2;
        case GGMLType::I8: return 1;
        case GGMLType::I16: return 2;
        case GGMLType::I32: return 4;
        // Quantized types have variable size, return approximate
        case GGMLType::Q4_0: return 0.5;  // 4 bits + metadata
        case GGMLType::Q4_1: return 0.5;
        case GGMLType::Q5_0: return 0.625; // 5 bits + metadata
        case GGMLType::Q5_1: return 0.625;
        case GGMLType::Q8_0: return 1.0;
        case GGMLType::Q8_1: return 1.0;
        default: return 4; // Default to F32 size
    }
}

} // namespace Model
} // namespace VersaAI
