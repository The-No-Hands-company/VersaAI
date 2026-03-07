/**
 * @file VersaAISafeTensorsLoader.hpp
 * @brief SafeTensors format model loader
 * 
 * Supports loading models in SafeTensors format.
 * SafeTensors is a safe, fast format for storing tensors developed by
 * Hugging Face. It's designed to be secure (no pickle vulnerabilities)
 * and memory-efficient (mmap-friendly).
 * 
 * Specification: https://github.com/huggingface/safetensors
 */

#pragma once

#include "VersaAIModelLoader.hpp"
#include <map>
#include <cstring>
#include <nlohmann/json.hpp>

namespace VersaAI {
namespace Model {

// ============================================================================
// SafeTensors Constants
// ============================================================================

namespace SafeTensors {
    // SafeTensors file structure:
    // [8 bytes: header length (little-endian uint64)]
    // [N bytes: JSON header]
    // [M bytes: tensor data (aligned)]
    
    constexpr size_t HEADER_SIZE_BYTES = 8;
    constexpr size_t MAX_HEADER_SIZE = 100 * 1024 * 1024; // 100MB max header
    constexpr size_t ALIGNMENT = 256; // Tensor data alignment
    
    // Data type strings (as used in JSON)
    namespace DType {
        constexpr const char* BOOL = "BOOL";
        constexpr const char* U8 = "U8";
        constexpr const char* I8 = "I8";
        constexpr const char* I16 = "I16";
        constexpr const char* U16 = "U16";
        constexpr const char* F16 = "F16";
        constexpr const char* BF16 = "BF16";
        constexpr const char* I32 = "I32";
        constexpr const char* U32 = "U32";
        constexpr const char* F32 = "F32";
        constexpr const char* F64 = "F64";
        constexpr const char* I64 = "I64";
        constexpr const char* U64 = "U64";
    }
}

// ============================================================================
// SafeTensors Data Type Conversion
// ============================================================================

/**
 * @brief Convert SafeTensors dtype string to TensorDataType
 */
inline TensorDataType safetensorsTypeToTensorType(const std::string& dtype) {
    if (dtype == SafeTensors::DType::F32) return TensorDataType::Float32;
    if (dtype == SafeTensors::DType::F16) return TensorDataType::Float16;
    if (dtype == SafeTensors::DType::BF16) return TensorDataType::BFloat16;
    if (dtype == SafeTensors::DType::I8) return TensorDataType::Int8;
    if (dtype == SafeTensors::DType::I16) return TensorDataType::Int16;
    if (dtype == SafeTensors::DType::I32) return TensorDataType::Int32;
    if (dtype == SafeTensors::DType::I64) return TensorDataType::Int64;
    if (dtype == SafeTensors::DType::U8) return TensorDataType::UInt8;
    if (dtype == SafeTensors::DType::U16) return TensorDataType::UInt16;
    if (dtype == SafeTensors::DType::U32) return TensorDataType::UInt32;
    if (dtype == SafeTensors::DType::BOOL) return TensorDataType::Bool;
    return TensorDataType::Custom;
}

/**
 * @brief Get size of SafeTensors dtype in bytes
 */
inline size_t getSafeTensorsTypeSize(const std::string& dtype) {
    if (dtype == SafeTensors::DType::F32) return 4;
    if (dtype == SafeTensors::DType::F64) return 8;
    if (dtype == SafeTensors::DType::F16) return 2;
    if (dtype == SafeTensors::DType::BF16) return 2;
    if (dtype == SafeTensors::DType::I8) return 1;
    if (dtype == SafeTensors::DType::I16) return 2;
    if (dtype == SafeTensors::DType::I32) return 4;
    if (dtype == SafeTensors::DType::I64) return 8;
    if (dtype == SafeTensors::DType::U8) return 1;
    if (dtype == SafeTensors::DType::U16) return 2;
    if (dtype == SafeTensors::DType::U32) return 4;
    if (dtype == SafeTensors::DType::U64) return 8;
    if (dtype == SafeTensors::DType::BOOL) return 1;
    return 0;
}

// ============================================================================
// SafeTensors Tensor Information
// ============================================================================

/**
 * @brief SafeTensors tensor metadata (from JSON)
 */
struct SafeTensorInfo {
    std::string name;
    std::string dtype;
    std::vector<uint64_t> shape;
    std::pair<uint64_t, uint64_t> dataOffsets; // [begin, end) in file
    
    /**
     * @brief Convert to generic TensorInfo
     */
    TensorInfo toTensorInfo() const {
        TensorInfo info;
        info.name = name;
        info.dataType = safetensorsTypeToTensorType(dtype);
        info.shape = shape;
        info.numElements = info.calculateNumElements();
        info.sizeBytes = dataOffsets.second - dataOffsets.first;
        info.offset = dataOffsets.first;
        return info;
    }
    
    /**
     * @brief Calculate tensor size in bytes
     */
    uint64_t calculateSize() const {
        uint64_t numElements = 1;
        for (auto dim : shape) {
            numElements *= dim;
        }
        return numElements * getSafeTensorsTypeSize(dtype);
    }
};

/**
 * @brief SafeTensors file metadata
 */
struct SafeTensorsMetadata {
    std::map<std::string, SafeTensorInfo> tensors;
    nlohmann::json metadata; // Optional metadata field in header
    
    /**
     * @brief Get total number of tensors
     */
    size_t tensorCount() const {
        return tensors.size();
    }
    
    /**
     * @brief Calculate total size of all tensors
     */
    uint64_t totalSize() const {
        uint64_t total = 0;
        for (const auto& [name, tensor] : tensors) {
            total += tensor.calculateSize();
        }
        return total;
    }
};

// ============================================================================
// SafeTensors Loader Implementation
// ============================================================================

/**
 * @brief Loader for SafeTensors format models
 */
class SafeTensorsLoader : public IModelLoader {
public:
    SafeTensorsLoader() = default;
    ~SafeTensorsLoader() override = default;
    
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
        return ModelFormat::SafeTensors;
    }
    
    /**
     * @brief Parse SafeTensors file header
     * @param filePath Path to SafeTensors file
     * @return Parsed metadata
     */
    static SafeTensorsMetadata parseHeader(const std::filesystem::path& filePath);
    
    /**
     * @brief Read header JSON from SafeTensors file
     * @param filePath Path to SafeTensors file
     * @return JSON header object
     */
    static nlohmann::json readHeaderJSON(const std::filesystem::path& filePath);
    
    /**
     * @brief Get tensor data pointer (for memory-mapped access)
     * @param filePath Path to SafeTensors file
     * @param tensorName Name of tensor
     * @return Offset and size of tensor data
     */
    static std::pair<uint64_t, uint64_t> getTensorDataLocation(
        const std::filesystem::path& filePath,
        const std::string& tensorName
    );
    
private:
    /**
     * @brief Extract model metadata from SafeTensors file
     */
    ModelMetadata extractModelMetadata(
        const std::filesystem::path& filePath,
        const SafeTensorsMetadata& stMetadata
    ) const;
    
    /**
     * @brief Detect architecture from tensor names and shapes
     */
    ModelArchitecture detectArchitecture(
        const SafeTensorsMetadata& metadata
    ) const;
    
    /**
     * @brief Detect quantization from tensor dtypes
     */
    QuantizationType detectQuantization(
        const SafeTensorsMetadata& metadata
    ) const;
    
    /**
     * @brief Calculate total parameters from tensors
     */
    uint64_t calculateParameters(
        const SafeTensorsMetadata& metadata
    ) const;
    
    /**
     * @brief Calculate memory requirements
     */
    uint64_t calculateMemoryRequirement(
        const SafeTensorsMetadata& metadata,
        const ModelLoadOptions& options
    ) const;
    
    /**
     * @brief Validate tensor offsets don't overlap and are within file bounds
     */
    bool validateTensorOffsets(
        const SafeTensorsMetadata& metadata,
        uint64_t fileSize
    ) const;
};

// ============================================================================
// SafeTensors Index File Support
// ============================================================================

/**
 * @brief SafeTensors index file (.safetensors.index.json)
 * 
 * Used for sharded models split across multiple files
 */
struct SafeTensorsIndex {
    std::map<std::string, std::string> weightMap; // tensor_name -> file_name
    nlohmann::json metadata;
    
    /**
     * @brief Load index from JSON file
     */
    static SafeTensorsIndex load(const std::filesystem::path& indexPath);
    
    /**
     * @brief Get list of all shard files
     */
    std::vector<std::string> getShardFiles() const;
    
    /**
     * @brief Get file containing specific tensor
     */
    std::optional<std::string> getFileForTensor(const std::string& tensorName) const;
};

/**
 * @brief Loader for sharded SafeTensors models
 */
class ShardedSafeTensorsLoader : public SafeTensorsLoader {
public:
    /**
     * @brief Load model from index file
     */
    std::shared_ptr<ModelBase> loadFromIndex(
        const std::filesystem::path& indexPath,
        const ModelLoadOptions& options
    );
    
    /**
     * @brief Load metadata from all shards
     */
    ModelMetadata loadMetadataFromIndex(
        const std::filesystem::path& indexPath
    ) const;
    
private:
    /**
     * @brief Merge metadata from multiple shards
     */
    ModelMetadata mergeShardMetadata(
        const std::vector<ModelMetadata>& shardMetadata
    ) const;
};

} // namespace Model
} // namespace VersaAI
