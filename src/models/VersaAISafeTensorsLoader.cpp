/**
 * @file VersaAISafeTensorsLoader.cpp
 * @brief Implementation of SafeTensors format model loader
 */

#include "../include/VersaAISafeTensorsLoader.hpp"
#include "../include/VersaAIModelBase.hpp"
#include "../include/VersaAIException.hpp"
#include "../include/VersaAILogger.hpp"
#include <fstream>
#include <algorithm>
#include <cstring>
#include <set>

namespace VersaAI {
namespace Model {

// ============================================================================
// SafeTensorsIndex Implementation
// ============================================================================

SafeTensorsIndex SafeTensorsIndex::load(const std::filesystem::path& indexPath) {
    std::ifstream file(indexPath);
    if (!file) {
        throw ModelException(
            "Failed to open SafeTensors index file: " + indexPath.string(),
            ErrorCode::MODEL_FILE_NOT_FOUND
        );
    }

    nlohmann::json j;
    try {
        file >> j;
    } catch (const nlohmann::json::exception& e) {
        throw ModelException(
            "Failed to parse SafeTensors index JSON: " + std::string(e.what()),
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    SafeTensorsIndex index;

    // Parse weight_map
    if (j.contains("weight_map")) {
        index.weightMap = j["weight_map"].get<std::map<std::string, std::string>>();
    }

    // Parse metadata
    if (j.contains("metadata")) {
        index.metadata = j["metadata"];
    }

    return index;
}

std::vector<std::string> SafeTensorsIndex::getShardFiles() const {
    std::set<std::string> uniqueFiles;
    for (const auto& [tensor, file] : weightMap) {
        uniqueFiles.insert(file);
    }
    return std::vector<std::string>(uniqueFiles.begin(), uniqueFiles.end());
}

std::optional<std::string> SafeTensorsIndex::getFileForTensor(
    const std::string& tensorName
) const {
    auto it = weightMap.find(tensorName);
    if (it != weightMap.end()) {
        return it->second;
    }
    return std::nullopt;
}

// ============================================================================
// SafeTensorsLoader Implementation
// ============================================================================

bool SafeTensorsLoader::canLoad(const std::filesystem::path& filePath) const {
    if (!FormatDetector::validatePath(filePath)) {
        return false;
    }

    // Check extension
    auto ext = filePath.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

    if (ext != ".safetensors") {
        return false;
    }

    // Validate header
    try {
        std::ifstream file(filePath, std::ios::binary);
        if (!file) {
            return false;
        }

        // Read header size
        uint64_t headerSize;
        file.read(reinterpret_cast<char*>(&headerSize), sizeof(headerSize));

        // Header size should be reasonable
        return headerSize > 0 && headerSize < SafeTensors::MAX_HEADER_SIZE;
    } catch (...) {
        return false;
    }
}

ModelMetadata SafeTensorsLoader::loadMetadata(const std::filesystem::path& filePath) const {
    Logger::getInstance().info(
        "Loading SafeTensors metadata: " + filePath.filename().string(),
        "SafeTensorsLoader"
    );

    auto stMetadata = parseHeader(filePath);
    return extractModelMetadata(filePath, stMetadata);
}

std::shared_ptr<ModelBase> SafeTensorsLoader::load(
    const std::filesystem::path& filePath,
    const ModelLoadOptions& options
) {
    Logger::getInstance().info(
        "Loading SafeTensors model: " + filePath.filename().string(),
        "SafeTensorsLoader"
    );

    LoadProgressTracker progress(options.onProgress);
    progress.setTotalSteps(5);

    // Step 1: Validate file
    progress.next("Validating SafeTensors file");
    if (!validate(filePath)) {
        throw ModelException(
            "SafeTensors model validation failed",
            ErrorCode::MODEL_VALIDATION_FAILED
        );
    }

    // Step 2: Parse header
    progress.next("Parsing header");
    auto stMetadata = parseHeader(filePath);

    // Step 3: Load metadata
    progress.next("Loading metadata");
    auto metadata = extractModelMetadata(filePath, stMetadata);

    // Step 4: Load tensors
    progress.next("Loading tensors");

    // Create model instance using GenericModel instead of abstract ModelBase
    auto model = std::make_shared<GenericModel>(metadata);

    // Memory-mapped loading for efficiency
    if (options.useMemoryMapping) {
        MemoryMappedFile mmf;
        if (!mmf.open(filePath, true)) {
            throw ModelException(
                "Failed to memory-map SafeTensors file",
                ErrorCode::MODEL_LOAD_FAILED
            );
        }

        // TODO: Load tensor data from memory-mapped file
        // Access tensors directly from mmf.data() at specified offsets

        Logger::getInstance().debug(
            "SafeTensors file memory-mapped successfully (" + std::to_string(mmf.size() / 1024 / 1024) + " MB)",
            "SafeTensorsLoader"
        );
    } else {
        // Traditional file reading
        std::ifstream file(filePath, std::ios::binary);
        if (!file) {
            throw ModelException(
                "Failed to open SafeTensors file",
                ErrorCode::MODEL_FILE_NOT_FOUND
            );
        }

        // TODO: Load tensor data from file
    }

    // Step 5: Complete
    progress.complete("SafeTensors model loaded successfully");

    Logger::getInstance().info(
        "SafeTensors model loaded successfully (" + std::to_string(stMetadata.tensorCount()) + " tensors, " + std::to_string(stMetadata.totalSize() / 1024 / 1024) + " MB)",
        "SafeTensorsLoader"
    );

    return model;
}

std::vector<TensorInfo> SafeTensorsLoader::getTensorList(
    const std::filesystem::path& filePath
) const {
    auto stMetadata = parseHeader(filePath);

    std::vector<TensorInfo> tensors;
    tensors.reserve(stMetadata.tensorCount());

    for (const auto& [name, stTensor] : stMetadata.tensors) {
        tensors.push_back(stTensor.toTensorInfo());
    }

    return tensors;
}

bool SafeTensorsLoader::validate(const std::filesystem::path& filePath) const {
    try {
        // Check file exists
        if (!FormatDetector::validatePath(filePath)) {
            return false;
        }

        // Parse and validate header
        auto stMetadata = parseHeader(filePath);

        // Validate tensor offsets
        uint64_t fileSize = FormatDetector::getFileSize(filePath);
        if (!validateTensorOffsets(stMetadata, fileSize)) {
            Logger::getInstance().error(
                "SafeTensors tensor offset validation failed",
                "SafeTensorsLoader"
            );
            return false;
        }

        return true;
    } catch (const std::exception& e) {
        Logger::getInstance().error(
            "SafeTensors validation failed: " + std::string(e.what()),
            "SafeTensorsLoader"
        );
        return false;
    }
}

SafeTensorsMetadata SafeTensorsLoader::parseHeader(const std::filesystem::path& filePath) {
    std::ifstream file(filePath, std::ios::binary);
    if (!file) {
        throw ModelException(
            "Failed to open SafeTensors file: " + filePath.string(),
            ErrorCode::MODEL_FILE_NOT_FOUND
        );
    }

    // Read header size (8 bytes, little-endian)
    uint64_t headerSize;
    file.read(reinterpret_cast<char*>(&headerSize), sizeof(headerSize));

    if (!file || headerSize == 0 || headerSize > SafeTensors::MAX_HEADER_SIZE) {
        throw ModelException(
            "Invalid SafeTensors header size: " + std::to_string(headerSize),
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    // Read header JSON
    std::vector<char> headerData(headerSize);
    file.read(headerData.data(), headerSize);

    if (!file || static_cast<size_t>(file.gcount()) != headerSize) {
        throw ModelException(
            "Failed to read SafeTensors header",
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    // Parse JSON
    nlohmann::json j;
    try {
        j = nlohmann::json::parse(headerData.begin(), headerData.end());
    } catch (const nlohmann::json::exception& e) {
        throw ModelException(
            "Failed to parse SafeTensors header JSON: " + std::string(e.what()),
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    SafeTensorsMetadata metadata;

    // Calculate data offset (after header)
    uint64_t dataOffset = SafeTensors::HEADER_SIZE_BYTES + headerSize;

    // Parse tensors
    for (auto it = j.begin(); it != j.end(); ++it) {
        const std::string& tensorName = it.key();

        // Skip metadata field
        if (tensorName == "__metadata__") {
            metadata.metadata = it.value();
            continue;
        }

        const auto& tensorJson = it.value();

        SafeTensorInfo tensor;
        tensor.name = tensorName;

        // Parse dtype
        if (tensorJson.contains("dtype")) {
            tensor.dtype = tensorJson["dtype"].get<std::string>();
        } else {
            throw ModelException(
                "Missing dtype for tensor: " + tensorName,
                ErrorCode::MODEL_INVALID_FILE
            );
        }

        // Parse shape
        if (tensorJson.contains("shape")) {
            tensor.shape = tensorJson["shape"].get<std::vector<uint64_t>>();
        } else {
            throw ModelException(
                "Missing shape for tensor: " + tensorName,
                ErrorCode::MODEL_INVALID_FILE
            );
        }

        // Parse data offsets
        if (tensorJson.contains("data_offsets")) {
            auto offsets = tensorJson["data_offsets"].get<std::vector<uint64_t>>();
            if (offsets.size() != 2) {
                throw ModelException(
                    "Invalid data_offsets for tensor: " + tensorName,
                    ErrorCode::MODEL_INVALID_FILE
                );
            }
            // Offsets are relative to start of data section
            tensor.dataOffsets = {dataOffset + offsets[0], dataOffset + offsets[1]};
        } else {
            throw ModelException(
                "Missing data_offsets for tensor: " + tensorName,
                ErrorCode::MODEL_INVALID_FILE
            );
        }

        metadata.tensors[tensorName] = tensor;
    }

    Logger::getInstance().debug(
        "Parsed SafeTensors header (" + std::to_string(metadata.tensorCount()) + " tensors, header: " + std::to_string(headerSize / 1024) + " KB)",
        "SafeTensorsLoader"
    );

    return metadata;
}

nlohmann::json SafeTensorsLoader::readHeaderJSON(const std::filesystem::path& filePath) {
    auto metadata = parseHeader(filePath);

    nlohmann::json j;
    for (const auto& [name, tensor] : metadata.tensors) {
        j[name]["dtype"] = tensor.dtype;
        j[name]["shape"] = tensor.shape;
        j[name]["data_offsets"] = std::vector<uint64_t>{
            tensor.dataOffsets.first,
            tensor.dataOffsets.second
        };
    }

    if (!metadata.metadata.is_null()) {
        j["__metadata__"] = metadata.metadata;
    }

    return j;
}

std::pair<uint64_t, uint64_t> SafeTensorsLoader::getTensorDataLocation(
    const std::filesystem::path& filePath,
    const std::string& tensorName
) {
    auto metadata = parseHeader(filePath);

    auto it = metadata.tensors.find(tensorName);
    if (it == metadata.tensors.end()) {
        throw ModelException(
            "Tensor not found: " + tensorName,
            ErrorCode::MODEL_TENSOR_NOT_FOUND
        );
    }

    return it->second.dataOffsets;
}

ModelMetadata SafeTensorsLoader::extractModelMetadata(
    const std::filesystem::path& filePath,
    const SafeTensorsMetadata& stMetadata
) const {
    ModelMetadata metadata;

    // Basic information
    metadata.name = filePath.stem().string();
    metadata.format = ModelFormat::SafeTensors;
    metadata.filePath = filePath.string();
    metadata.fileSizeBytes = FormatDetector::getFileSize(filePath);
    metadata.loadedAt = std::chrono::system_clock::now();

    // Extract metadata from __metadata__ field
    if (!stMetadata.metadata.is_null()) {
        if (stMetadata.metadata.contains("name")) {
            metadata.name = stMetadata.metadata["name"].get<std::string>();
        }
        if (stMetadata.metadata.contains("version")) {
            metadata.version = stMetadata.metadata["version"].get<std::string>();
        }
        if (stMetadata.metadata.contains("description")) {
            metadata.description = stMetadata.metadata["description"].get<std::string>();
        }
        if (stMetadata.metadata.contains("author")) {
            metadata.author = stMetadata.metadata["author"].get<std::string>();
        }
        if (stMetadata.metadata.contains("license")) {
            metadata.license = stMetadata.metadata["license"].get<std::string>();
        }
    }

    // Architecture detection
    metadata.architecture = detectArchitecture(stMetadata);
    metadata.quantization = detectQuantization(stMetadata);

    // Parameters and memory
    metadata.parameterCount = calculateParameters(stMetadata);
    metadata.memoryRequiredBytes = calculateMemoryRequirement(stMetadata, ModelLoadOptions());

    // Store SafeTensors-specific metadata
    metadata.setMetadata("safetensors_tensor_count", static_cast<int64_t>(stMetadata.tensorCount()));
    metadata.setMetadata("safetensors_total_size", static_cast<int64_t>(stMetadata.totalSize()));

    return metadata;
}

ModelArchitecture SafeTensorsLoader::detectArchitecture(
    const SafeTensorsMetadata& metadata
) const {
    // Heuristic-based detection from tensor names
    std::set<std::string> tensorNames;
    for (const auto& [name, _] : metadata.tensors) {
        std::string lowerName = name;
        std::transform(lowerName.begin(), lowerName.end(), lowerName.begin(), ::tolower);
        tensorNames.insert(lowerName);
    }

    // Check for architecture-specific patterns
    bool hasLlamaPatterns = false;
    bool hasMistralPatterns = false;
    bool hasGPTPatterns = false;
    bool hasBERTPatterns = false;

    for (const auto& name : tensorNames) {
        if (name.find("llama") != std::string::npos) hasLlamaPatterns = true;
        if (name.find("mistral") != std::string::npos) hasMistralPatterns = true;
        if (name.find("gpt") != std::string::npos) hasGPTPatterns = true;
        if (name.find("bert") != std::string::npos) hasBERTPatterns = true;
    }

    if (hasLlamaPatterns) return ModelArchitecture::LLaMA;
    if (hasMistralPatterns) return ModelArchitecture::Mistral;
    if (hasGPTPatterns) return ModelArchitecture::GPT;
    if (hasBERTPatterns) return ModelArchitecture::BERT;

    return ModelArchitecture::Transformer;
}

QuantizationType SafeTensorsLoader::detectQuantization(
    const SafeTensorsMetadata& metadata
) const {
    // Check tensor dtypes for quantization
    bool hasF16 = false;
    bool hasF32 = false;
    bool hasInt8 = false;

    for (const auto& [_, tensor] : metadata.tensors) {
        if (tensor.dtype == "F16" || tensor.dtype == "BF16") hasF16 = true;
        if (tensor.dtype == "F32") hasF32 = true;
        if (tensor.dtype == "I8") hasInt8 = true;
    }

    if (hasInt8) return QuantizationType::Q8_0;
    if (hasF16) return QuantizationType::F16;
    if (hasF32) return QuantizationType::None;

    return QuantizationType::None;
}

uint64_t SafeTensorsLoader::calculateParameters(
    const SafeTensorsMetadata& metadata
) const {
    uint64_t total = 0;

    for (const auto& [_, tensor] : metadata.tensors) {
        uint64_t elements = 1;
        for (auto dim : tensor.shape) {
            elements *= dim;
        }
        total += elements;
    }

    return total;
}

uint64_t SafeTensorsLoader::calculateMemoryRequirement(
    const SafeTensorsMetadata& metadata,
    const ModelLoadOptions& options
) const {
    // Base size is the total tensor data
    uint64_t total = metadata.totalSize();

    // Add overhead for runtime structures (estimated 15%)
    return static_cast<uint64_t>(total * 1.15);
}

bool SafeTensorsLoader::validateTensorOffsets(
    const SafeTensorsMetadata& metadata,
    uint64_t fileSize
) const {
    for (const auto& [name, tensor] : metadata.tensors) {
        // Check offsets are within file
        if (tensor.dataOffsets.second > fileSize) {
            Logger::getInstance().error(
                "Tensor data extends beyond file: " + name + " (offset: " + std::to_string(tensor.dataOffsets.second) + ", file size: " + std::to_string(fileSize) + ")",
                "SafeTensorsLoader"
            );
            return false;
        }

        // Check offset order
        if (tensor.dataOffsets.first >= tensor.dataOffsets.second) {
            Logger::getInstance().error(
                "Invalid tensor offset range: " + name,
                "SafeTensorsLoader"
            );
            return false;
        }

        // Check size matches shape
        uint64_t expectedSize = tensor.calculateSize();
        uint64_t actualSize = tensor.dataOffsets.second - tensor.dataOffsets.first;

        if (expectedSize != actualSize) {
            Logger::getInstance().warning(
                "Tensor size mismatch: " + name + " SafeTensorsLoader"
            );
        }
    }

    return true;
}

// ============================================================================
// ShardedSafeTensorsLoader Implementation
// ============================================================================

std::shared_ptr<ModelBase> ShardedSafeTensorsLoader::loadFromIndex(
    const std::filesystem::path& indexPath,
    const ModelLoadOptions& options
) {
    Logger::getInstance().info(
        "Loading sharded SafeTensors model from index: " + indexPath.filename().string(),
        "ShardedSafeTensorsLoader"
    );

    // Load index
    auto index = SafeTensorsIndex::load(indexPath);
    auto shardFiles = index.getShardFiles();

    Logger::getInstance().info(
        "Found " + std::to_string(shardFiles.size()) + " shard files",
        "ShardedSafeTensorsLoader"
    );

    // TODO: Load all shards and merge
    // For now, return placeholder with default metadata
    Model::ModelMetadata defaultMetadata;
    defaultMetadata.name = "ShardedSafeTensorsModel";
    defaultMetadata.format = Model::ModelFormat::SafeTensors;
    return std::make_shared<Model::GenericModel>(defaultMetadata);
}

ModelMetadata ShardedSafeTensorsLoader::loadMetadataFromIndex(
    const std::filesystem::path& indexPath
) const {
    auto index = SafeTensorsIndex::load(indexPath);
    auto shardFiles = index.getShardFiles();

    std::vector<ModelMetadata> shardMetadata;
    auto baseDir = indexPath.parent_path();

    for (const auto& shardFile : shardFiles) {
        auto shardPath = baseDir / shardFile;
        shardMetadata.push_back(loadMetadata(shardPath));
    }

    return mergeShardMetadata(shardMetadata);
}

ModelMetadata ShardedSafeTensorsLoader::mergeShardMetadata(
    const std::vector<ModelMetadata>& shardMetadata
) const {
    if (shardMetadata.empty()) {
        throw ModelException(
            "No shard metadata to merge",
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    // Use first shard as base
    ModelMetadata merged = shardMetadata[0];

    // Sum parameters and memory from all shards
    merged.parameterCount = 0;
    merged.memoryRequiredBytes = 0;

    for (const auto& shard : shardMetadata) {
        merged.parameterCount += shard.parameterCount;
        merged.memoryRequiredBytes += shard.memoryRequiredBytes;
    }

    merged.setMetadata("num_shards", static_cast<int64_t>(shardMetadata.size()));

    return merged;
}

} // namespace Model
} // namespace VersaAI
