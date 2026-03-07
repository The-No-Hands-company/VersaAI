/**
 * @file VersaAIONNXLoader.cpp
 * @brief Implementation of ONNX format model loader
 */

#include "../include/VersaAIONNXLoader.hpp"
#include "../include/VersaAIModelBase.hpp"
#include "../include/VersaAIException.hpp"
#include "../include/VersaAILogger.hpp"
#include <fstream>
#include <algorithm>
#include <sstream>

namespace VersaAI {
namespace Model {

// ============================================================================
// Helper Functions
// ============================================================================

uint64_t ONNXLoader::readVarint(const uint8_t* data, size_t& offset, size_t maxSize) {
    uint64_t result = 0;
    int shift = 0;

    while (offset < maxSize) {
        uint8_t byte = data[offset++];
        result |= static_cast<uint64_t>(byte & 0x7F) << shift;

        if ((byte & 0x80) == 0) {
            return result;
        }

        shift += 7;
        if (shift >= 64) {
            throw ModelException(
                "Varint overflow in ONNX model",
                ErrorCode::MODEL_INVALID_FILE
            );
        }
    }

    throw ModelException(
        "Unexpected end of file while reading varint",
        ErrorCode::MODEL_INVALID_FILE
    );
}

void ONNXLoader::skipField(const uint8_t* data, size_t& offset, size_t maxSize, int wireType) {
    switch (static_cast<ProtoBuf::WireType>(wireType)) {
        case ProtoBuf::WireType::VARINT:
            readVarint(data, offset, maxSize);
            break;

        case ProtoBuf::WireType::FIXED64:
            offset += 8;
            break;

        case ProtoBuf::WireType::LENGTH_DELIMITED: {
            uint64_t length = readVarint(data, offset, maxSize);
            offset += length;
            break;
        }

        case ProtoBuf::WireType::FIXED32:
            offset += 4;
            break;

        default:
            throw ModelException(
                "Unsupported Protocol Buffers wire type",
                ErrorCode::MODEL_INVALID_FILE
            );
    }
}

// ============================================================================
// ONNXLoader Implementation
// ============================================================================

bool ONNXLoader::canLoad(const std::filesystem::path& filePath) const {
    if (!FormatDetector::validatePath(filePath)) {
        return false;
    }

    // Check extension
    auto ext = filePath.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

    if (ext != ".onnx") {
        return false;
    }

    // Check magic bytes (Protocol Buffers format)
    try {
        auto magic = FormatDetector::readMagic(filePath);
        if (magic.empty()) {
            return false;
        }

        // ONNX files start with Protocol Buffers encoding
        // First byte is typically 0x08 or 0x0A
        return magic[0] == 0x08 || magic[0] == 0x0A;
    } catch (...) {
        return false;
    }
}

ModelMetadata ONNXLoader::loadMetadata(const std::filesystem::path& filePath) const {
    Logger::getInstance().info(
        "Loading ONNX metadata: " + filePath.filename().string(),
        "ONNXLoader"
    );

    auto modelInfo = parseModelInfo(filePath);
    auto tensors = readTensorInfo(filePath);

    return extractModelMetadata(filePath, modelInfo, tensors);
}

std::shared_ptr<ModelBase> ONNXLoader::load(
    const std::filesystem::path& filePath,
    const ModelLoadOptions& options
) {
    Logger::getInstance().info(
        "Loading ONNX model: " + filePath.filename().string(),
        "ONNXLoader"
    );

    LoadProgressTracker progress(options.onProgress);
    progress.setTotalSteps(5);

    // Step 1: Validate file
    progress.next("Validating ONNX file");
    if (!validate(filePath)) {
        throw ModelException(
            "ONNX model validation failed",
            ErrorCode::MODEL_VALIDATION_FAILED
        );
    }

    // Step 2: Load metadata
    progress.next("Loading metadata");
    auto metadata = loadMetadata(filePath);

    // Step 3: Create model instance
    progress.next("Creating model instance");
    // TODO: Create actual ONNX model instance
    // For now, create a placeholder GenericModel
    auto model = std::make_shared<GenericModel>(metadata);

    // Step 4: Load weights
    progress.next("Loading weights");
    // TODO: Load actual tensor weights
    // This requires ONNX Runtime integration or custom inference engine

    // Step 5: Complete
    progress.complete("ONNX model loaded successfully");

    Logger::getInstance().info(
        "ONNX model loaded successfully (params: " + std::to_string(metadata.parameterCount) + ", mem: " + std::to_string(metadata.memoryRequiredBytes / 1024 / 1024) + " MB)",
        "ONNXLoader"
    );

    return model;
}

std::vector<TensorInfo> ONNXLoader::getTensorList(
    const std::filesystem::path& filePath
) const {
    auto onnxTensors = readTensorInfo(filePath);

    std::vector<TensorInfo> tensors;
    tensors.reserve(onnxTensors.size());

    for (const auto& onnxTensor : onnxTensors) {
        tensors.push_back(onnxTensor.toTensorInfo());
    }

    return tensors;
}

bool ONNXLoader::validate(const std::filesystem::path& filePath) const {
    try {
        // Check file exists and is readable
        if (!FormatDetector::validatePath(filePath)) {
            return false;
        }

        // Try to parse model info
        auto modelInfo = parseModelInfo(filePath);

        // Validate IR version
        if (modelInfo.irVersion < ONNX::MIN_IR_VERSION ||
            modelInfo.irVersion > ONNX::MAX_IR_VERSION) {
            Logger::getInstance().warning(
                "ONNX IR version may be unsupported: " + std::to_string(modelInfo.irVersion),
                "ONNXLoader"
            );
        }

        // Validate opset versions
        for (const auto& [domain, version] : modelInfo.opsetImports) {
            if (domain.empty() || domain == "ai.onnx") {
                if (version < ONNX::MIN_OPSET_VERSION) {
                    Logger::getInstance().warning(
                        "ONNX opset version may be too old: " + std::to_string(version),
                        "ONNXLoader"
                    );
                }
            }
        }

        return true;
    } catch (const std::exception& e) {
        Logger::getInstance().error(
            "ONNX validation failed: " + std::string(e.what()),
            "ONNXLoader"
        );
        return false;
    }
}

ONNXModelInfo ONNXLoader::parseModelInfo(const std::filesystem::path& filePath) {
    ONNXModelInfo info;

    // Note: This is a minimal implementation
    // For production use, integrate ONNX library or implement full protobuf parser

    std::ifstream file(filePath, std::ios::binary);
    if (!file) {
        throw ModelException(
            "Failed to open ONNX file: " + filePath.string(),
            ErrorCode::MODEL_FILE_NOT_FOUND
        );
    }

    // Read first 1KB to extract basic info
    std::vector<uint8_t> header(1024);
    file.read(reinterpret_cast<char*>(header.data()), header.size());
    size_t bytesRead = file.gcount();

    if (bytesRead < 16) {
        throw ModelException(
            "ONNX file too small",
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    // Basic protobuf parsing to extract version info
    // Field 1: IR version (varint)
    size_t offset = 0;
    if (offset < bytesRead && header[offset] == 0x08) {
        offset++;
        info.irVersion = readVarint(header.data(), offset, bytesRead);
    }

    // Set defaults for missing info
    info.producerName = "Unknown";
    info.graphName = "main";
    info.opsetImports[""] = 13; // Default to opset 13

    Logger::getInstance().debug(
        "Parsed ONNX model info (IR: " + std::to_string(info.irVersion) + ", producer: " + info.producerName + ")",
        "ONNXLoader"
    );

    return info;
}

std::vector<ONNXTensorInfo> ONNXLoader::readTensorInfo(
    const std::filesystem::path& filePath
) {
    // Note: This is a stub implementation
    // Full implementation requires parsing the ONNX protobuf graph structure

    std::vector<ONNXTensorInfo> tensors;

    Logger::getInstance().debug(
        "Reading ONNX tensor info (stub implementation)",
        "ONNXLoader"
    );

    // TODO: Parse graph.initializer and graph.value_info to extract tensor metadata
    // This requires either:
    // 1. Full Protocol Buffers implementation
    // 2. ONNX library integration
    // 3. ONNX Runtime integration

    return tensors;
}

ModelMetadata ONNXLoader::extractModelMetadata(
    const std::filesystem::path& filePath,
    const ONNXModelInfo& modelInfo,
    const std::vector<ONNXTensorInfo>& tensors
) const {
    ModelMetadata metadata;

    // Basic information
    metadata.name = filePath.stem().string();
    metadata.description = modelInfo.docString;
    metadata.version = modelInfo.producerVersion;

    // Format
    metadata.format = ModelFormat::ONNX;
    metadata.filePath = filePath.string();
    metadata.fileSizeBytes = FormatDetector::getFileSize(filePath);
    metadata.loadedAt = std::chrono::system_clock::now();

    // Architecture detection
    metadata.architecture = detectArchitecture(modelInfo);

    // Parameters and memory
    metadata.parameterCount = calculateParameters(tensors);
    metadata.memoryRequiredBytes = calculateMemoryRequirement(tensors, ModelLoadOptions());

    // Store ONNX-specific metadata
    metadata.setMetadata("onnx_ir_version", modelInfo.irVersion);
    metadata.setMetadata("onnx_producer_name", modelInfo.producerName);
    metadata.setMetadata("onnx_graph_name", modelInfo.graphName);
    metadata.setMetadata("onnx_num_nodes", static_cast<int64_t>(modelInfo.numNodes));

    // Store opset versions
    for (const auto& [domain, version] : modelInfo.opsetImports) {
        std::string key = "onnx_opset_" + (domain.empty() ? "default" : domain);
        metadata.setMetadata(key, version);
    }

    return metadata;
}

ModelArchitecture ONNXLoader::detectArchitecture(
    const ONNXModelInfo& modelInfo
) const {
    // Heuristic-based architecture detection from model name and metadata
    std::string name = modelInfo.graphName;
    std::transform(name.begin(), name.end(), name.begin(), ::tolower);

    if (name.find("bert") != std::string::npos) return ModelArchitecture::BERT;
    if (name.find("gpt") != std::string::npos) return ModelArchitecture::GPT;
    if (name.find("t5") != std::string::npos) return ModelArchitecture::T5;
    if (name.find("llama") != std::string::npos) return ModelArchitecture::LLaMA;
    if (name.find("mistral") != std::string::npos) return ModelArchitecture::Mistral;

    // Check producer name
    std::string producer = modelInfo.producerName;
    std::transform(producer.begin(), producer.end(), producer.begin(), ::tolower);

    if (producer.find("pytorch") != std::string::npos ||
        producer.find("tensorflow") != std::string::npos) {
        return ModelArchitecture::Transformer;
    }

    return ModelArchitecture::Unknown;
}

uint64_t ONNXLoader::calculateParameters(
    const std::vector<ONNXTensorInfo>& tensors
) const {
    uint64_t total = 0;

    for (const auto& tensor : tensors) {
        if (!tensor.hasData) continue;

        uint64_t elements = 1;
        for (auto dim : tensor.shape) {
            if (dim > 0) {
                elements *= static_cast<uint64_t>(dim);
            }
        }
        total += elements;
    }

    return total;
}

uint64_t ONNXLoader::calculateMemoryRequirement(
    const std::vector<ONNXTensorInfo>& tensors,
    const ModelLoadOptions& options
) const {
    uint64_t total = 0;

    for (const auto& tensor : tensors) {
        if (!tensor.hasData) continue;

        uint64_t elements = 1;
        for (auto dim : tensor.shape) {
            if (dim > 0) {
                elements *= static_cast<uint64_t>(dim);
            }
        }

        total += elements * getONNXTypeSize(tensor.dataType);
    }

    // Add overhead for runtime structures (estimated 20%)
    return static_cast<uint64_t>(total * 1.2);
}

} // namespace Model
} // namespace VersaAI
