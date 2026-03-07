/**
 * @file VersaAIONNXLoader.hpp
 * @brief ONNX (Open Neural Network Exchange) model loader
 * 
 * Supports loading models in ONNX format.
 * ONNX is a widely-adopted open format for neural network models,
 * supported by PyTorch, TensorFlow, and many other frameworks.
 * 
 * Specification: https://onnx.ai/onnx/
 */

#pragma once

#include "VersaAIModelLoader.hpp"
#include <map>
#include <cstring>

namespace VersaAI {
namespace Model {

// ============================================================================
// ONNX Constants
// ============================================================================

namespace ONNX {
    // ONNX uses Protocol Buffers for serialization
    // Magic bytes for Protocol Buffers (0x0A for field 1, wire type 2)
    constexpr uint8_t PROTO_MAGIC = 0x0A;
    
    // ONNX model IR version
    constexpr int64_t MIN_IR_VERSION = 3;
    constexpr int64_t MAX_IR_VERSION = 9; // As of ONNX 1.14
    
    // ONNX opset versions
    constexpr int64_t MIN_OPSET_VERSION = 7;
    constexpr int64_t MAX_OPSET_VERSION = 18;
    
    // Tensor element types
    enum class DataType : int32_t {
        UNDEFINED = 0,
        FLOAT = 1,      // float32
        UINT8 = 2,      // uint8_t
        INT8 = 3,       // int8_t
        UINT16 = 4,     // uint16_t
        INT16 = 5,      // int16_t
        INT32 = 6,      // int32_t
        INT64 = 7,      // int64_t
        STRING = 8,     // string
        BOOL = 9,       // bool
        FLOAT16 = 10,   // float16
        DOUBLE = 11,    // float64
        UINT32 = 12,    // uint32_t
        UINT64 = 13,    // uint64_t
        COMPLEX64 = 14, // complex64
        COMPLEX128 = 15,// complex128
        BFLOAT16 = 16,  // bfloat16
    };
}

// ============================================================================
// ONNX Tensor Data Type Conversion
// ============================================================================

/**
 * @brief Convert ONNX data type to TensorDataType
 */
inline TensorDataType onnxTypeToTensorType(ONNX::DataType type) {
    switch (type) {
        case ONNX::DataType::FLOAT: return TensorDataType::Float32;
        case ONNX::DataType::FLOAT16: return TensorDataType::Float16;
        case ONNX::DataType::BFLOAT16: return TensorDataType::BFloat16;
        case ONNX::DataType::INT8: return TensorDataType::Int8;
        case ONNX::DataType::INT16: return TensorDataType::Int16;
        case ONNX::DataType::INT32: return TensorDataType::Int32;
        case ONNX::DataType::INT64: return TensorDataType::Int64;
        case ONNX::DataType::UINT8: return TensorDataType::UInt8;
        case ONNX::DataType::UINT16: return TensorDataType::UInt16;
        case ONNX::DataType::UINT32: return TensorDataType::UInt32;
        case ONNX::DataType::BOOL: return TensorDataType::Bool;
        default: return TensorDataType::Custom;
    }
}

/**
 * @brief Get size of ONNX data type in bytes
 */
inline size_t getONNXTypeSize(ONNX::DataType type) {
    switch (type) {
        case ONNX::DataType::FLOAT: return 4;
        case ONNX::DataType::DOUBLE: return 8;
        case ONNX::DataType::FLOAT16: return 2;
        case ONNX::DataType::BFLOAT16: return 2;
        case ONNX::DataType::INT8: return 1;
        case ONNX::DataType::INT16: return 2;
        case ONNX::DataType::INT32: return 4;
        case ONNX::DataType::INT64: return 8;
        case ONNX::DataType::UINT8: return 1;
        case ONNX::DataType::UINT16: return 2;
        case ONNX::DataType::UINT32: return 4;
        case ONNX::DataType::UINT64: return 8;
        case ONNX::DataType::BOOL: return 1;
        case ONNX::DataType::COMPLEX64: return 8;
        case ONNX::DataType::COMPLEX128: return 16;
        default: return 0;
    }
}

// ============================================================================
// ONNX Model Metadata
// ============================================================================

/**
 * @brief Parsed ONNX model metadata
 */
struct ONNXModelInfo {
    int64_t irVersion = 0;
    std::string producerName;
    std::string producerVersion;
    std::string domain;
    int64_t modelVersion = 0;
    std::string docString;
    
    // Graph information
    std::string graphName;
    size_t numInputs = 0;
    size_t numOutputs = 0;
    size_t numNodes = 0;
    size_t numInitializers = 0;
    
    // Opset versions
    std::map<std::string, int64_t> opsetImports;
    
    // Metadata properties
    std::map<std::string, std::string> metadataProps;
};

/**
 * @brief ONNX tensor information
 */
struct ONNXTensorInfo {
    std::string name;
    ONNX::DataType dataType;
    std::vector<int64_t> shape;
    bool hasData = false;
    uint64_t dataOffset = 0;
    uint64_t dataSize = 0;
    
    /**
     * @brief Convert to generic TensorInfo
     */
    TensorInfo toTensorInfo() const {
        TensorInfo info;
        info.name = name;
        info.dataType = onnxTypeToTensorType(dataType);
        info.shape.clear();
        for (auto dim : shape) {
            info.shape.push_back(static_cast<uint64_t>(dim > 0 ? dim : 0));
        }
        info.numElements = info.calculateNumElements();
        info.sizeBytes = info.numElements * getTensorDataTypeSize(info.dataType);
        info.offset = dataOffset;
        return info;
    }
};

// ============================================================================
// ONNX Loader Implementation
// ============================================================================

/**
 * @brief Loader for ONNX format models
 * 
 * This implementation uses a minimal Protocol Buffers parser to avoid
 * heavy dependencies. For production use with complex ONNX models,
 * consider using the official ONNX Runtime library.
 */
class ONNXLoader : public IModelLoader {
public:
    ONNXLoader() = default;
    ~ONNXLoader() override = default;
    
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
        return ModelFormat::ONNX;
    }
    
    /**
     * @brief Parse ONNX model information
     */
    static ONNXModelInfo parseModelInfo(const std::filesystem::path& filePath);
    
    /**
     * @brief Read tensor information from ONNX model
     */
    static std::vector<ONNXTensorInfo> readTensorInfo(
        const std::filesystem::path& filePath
    );
    
private:
    /**
     * @brief Extract model metadata from ONNX model info
     */
    ModelMetadata extractModelMetadata(
        const std::filesystem::path& filePath,
        const ONNXModelInfo& modelInfo,
        const std::vector<ONNXTensorInfo>& tensors
    ) const;
    
    /**
     * @brief Detect architecture from ONNX graph structure
     */
    ModelArchitecture detectArchitecture(
        const ONNXModelInfo& modelInfo
    ) const;
    
    /**
     * @brief Calculate total parameters
     */
    uint64_t calculateParameters(
        const std::vector<ONNXTensorInfo>& tensors
    ) const;
    
    /**
     * @brief Calculate memory requirements
     */
    uint64_t calculateMemoryRequirement(
        const std::vector<ONNXTensorInfo>& tensors,
        const ModelLoadOptions& options
    ) const;
    
    /**
     * @brief Parse Protocol Buffers varint
     */
    static uint64_t readVarint(const uint8_t* data, size_t& offset, size_t maxSize);
    
    /**
     * @brief Skip Protocol Buffers field
     */
    static void skipField(const uint8_t* data, size_t& offset, size_t maxSize, int wireType);
};

// ============================================================================
// Protocol Buffers Wire Types
// ============================================================================

namespace ProtoBuf {
    enum class WireType : uint8_t {
        VARINT = 0,
        FIXED64 = 1,
        LENGTH_DELIMITED = 2,
        START_GROUP = 3,
        END_GROUP = 4,
        FIXED32 = 5
    };
    
    inline WireType getWireType(uint8_t tag) {
        return static_cast<WireType>(tag & 0x07);
    }
    
    inline uint32_t getFieldNumber(uint8_t tag) {
        return tag >> 3;
    }
}

} // namespace Model
} // namespace VersaAI
