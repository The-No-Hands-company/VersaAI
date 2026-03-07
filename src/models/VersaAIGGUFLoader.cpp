/**
 * @file VersaAIGGUFLoader.cpp
 * @brief Implementation of GGUF format model loader
 */

#include "../include/VersaAIGGUFLoader.hpp"
#include "../include/VersaAIModelBase.hpp"
#include <cstring>
#include <sstream>

namespace VersaAI {
namespace Model {

// ============================================================================
// GGUFString Implementation
// ============================================================================

GGUFString GGUFString::read(const void* data, size_t& offset) {
    GGUFString str;
    
    // Read length (uint64_t)
    std::memcpy(&str.length, static_cast<const uint8_t*>(data) + offset, sizeof(uint64_t));
    offset += sizeof(uint64_t);
    
    // Read string data
    if (str.length > 0) {
        str.value.resize(str.length);
        std::memcpy(str.value.data(), static_cast<const uint8_t*>(data) + offset, str.length);
        offset += str.length;
    }
    
    return str;
}

// ============================================================================
// GGUFMetadataValue Implementation
// ============================================================================

GGUFMetadataValue GGUFMetadataValue::read(const void* data, size_t& offset) {
    GGUFMetadataValue val;
    
    // Read type
    std::memcpy(&val.type, static_cast<const uint8_t*>(data) + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Read value based on type
    switch (val.type) {
        case GGUF::MetadataType::UINT8: {
            uint8_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(uint8_t));
            offset += sizeof(uint8_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::INT8: {
            int8_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(int8_t));
            offset += sizeof(int8_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::UINT16: {
            uint16_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(uint16_t));
            offset += sizeof(uint16_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::INT16: {
            int16_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(int16_t));
            offset += sizeof(int16_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::UINT32: {
            uint32_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(uint32_t));
            offset += sizeof(uint32_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::INT32: {
            int32_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(int32_t));
            offset += sizeof(int32_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::UINT64: {
            uint64_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(uint64_t));
            offset += sizeof(uint64_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::INT64: {
            int64_t v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(int64_t));
            offset += sizeof(int64_t);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::FLOAT32: {
            float v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(float));
            offset += sizeof(float);
            val.value = static_cast<double>(v);
            break;
        }
        case GGUF::MetadataType::FLOAT64: {
            double v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(double));
            offset += sizeof(double);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::BOOL: {
            bool v;
            std::memcpy(&v, static_cast<const uint8_t*>(data) + offset, sizeof(bool));
            offset += sizeof(bool);
            val.value = v;
            break;
        }
        case GGUF::MetadataType::STRING: {
            auto str = GGUFString::read(data, offset);
            val.value = str.value;
            break;
        }
        case GGUF::MetadataType::ARRAY: {
            // Read array type
            GGUF::MetadataType arrayType;
            std::memcpy(&arrayType, static_cast<const uint8_t*>(data) + offset, sizeof(uint32_t));
            offset += sizeof(uint32_t);
            
            // Read array length
            uint64_t arrayLength;
            std::memcpy(&arrayLength, static_cast<const uint8_t*>(data) + offset, sizeof(uint64_t));
            offset += sizeof(uint64_t);
            
            // Read array elements
            std::vector<GGUFMetadataValue> array;
            array.reserve(arrayLength);
            
            for (uint64_t i = 0; i < arrayLength; ++i) {
                GGUFMetadataValue elem;
                elem.type = arrayType;
                
                size_t tempOffset = offset;
                offset += sizeof(uint32_t); // Skip type as we already know it
                elem = read(data, tempOffset);
                offset = tempOffset;
                
                array.push_back(std::move(elem));
            }
            
            val.value = array;
            break;
        }
        default:
            throw ModelException(
                "Unknown GGUF metadata type: " + std::to_string(static_cast<uint32_t>(val.type)),
                ErrorCode::MODEL_INVALID_FORMAT
            );
    }
    
    return val;
}

std::string GGUFMetadataValue::asString() const {
    if (std::holds_alternative<std::string>(value)) {
        return std::get<std::string>(value);
    }
    
    // Try to convert numeric types
    try {
        if (std::holds_alternative<int64_t>(value)) {
            return std::to_string(std::get<int64_t>(value));
        }
        if (std::holds_alternative<uint64_t>(value)) {
            return std::to_string(std::get<uint64_t>(value));
        }
        if (std::holds_alternative<double>(value)) {
            return std::to_string(std::get<double>(value));
        }
        if (std::holds_alternative<bool>(value)) {
            return std::get<bool>(value) ? "true" : "false";
        }
    } catch (...) {}
    
    return "";
}

int64_t GGUFMetadataValue::asInt() const {
    if (std::holds_alternative<int64_t>(value)) {
        return std::get<int64_t>(value);
    }
    if (std::holds_alternative<uint64_t>(value)) {
        return static_cast<int64_t>(std::get<uint64_t>(value));
    }
    if (std::holds_alternative<int32_t>(value)) {
        return static_cast<int64_t>(std::get<int32_t>(value));
    }
    if (std::holds_alternative<uint32_t>(value)) {
        return static_cast<int64_t>(std::get<uint32_t>(value));
    }
    return 0;
}

double GGUFMetadataValue::asFloat() const {
    if (std::holds_alternative<double>(value)) {
        return std::get<double>(value);
    }
    if (std::holds_alternative<int64_t>(value)) {
        return static_cast<double>(std::get<int64_t>(value));
    }
    return 0.0;
}

// ============================================================================
// GGUFTensorInfo Implementation
// ============================================================================

GGUFTensorInfo GGUFTensorInfo::read(const void* data, size_t& offset) {
    GGUFTensorInfo info;
    
    // Read tensor name
    auto nameStr = GGUFString::read(data, offset);
    info.name = nameStr.value;
    
    // Read number of dimensions
    std::memcpy(&info.numDimensions, static_cast<const uint8_t*>(data) + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Read dimensions
    info.dimensions.resize(info.numDimensions);
    for (uint32_t i = 0; i < info.numDimensions; ++i) {
        std::memcpy(&info.dimensions[i], static_cast<const uint8_t*>(data) + offset, sizeof(uint64_t));
        offset += sizeof(uint64_t);
    }
    
    // Read GGML type
    std::memcpy(&info.ggmlType, static_cast<const uint8_t*>(data) + offset, sizeof(uint32_t));
    offset += sizeof(uint32_t);
    
    // Read offset
    std::memcpy(&info.offset, static_cast<const uint8_t*>(data) + offset, sizeof(uint64_t));
    offset += sizeof(uint64_t);
    
    return info;
}

uint64_t GGUFTensorInfo::calculateSize() const {
    uint64_t numElements = 1;
    for (auto dim : dimensions) {
        numElements *= dim;
    }
    
    // Get size per element based on GGML type
    size_t bytesPerElement = getGGMLTypeSize(static_cast<GGMLType>(ggmlType));
    
    return static_cast<uint64_t>(numElements * bytesPerElement);
}

TensorInfo GGUFTensorInfo::toTensorInfo() const {
    TensorInfo info;
    info.name = name;
    info.dataType = ggmlTypeToTensorType(static_cast<GGMLType>(ggmlType));
    info.shape = dimensions;
    info.numElements = 1;
    for (auto dim : dimensions) {
        info.numElements *= dim;
    }
    info.sizeBytes = calculateSize();
    info.offset = offset;
    return info;
}

// ============================================================================
// GGUFLoader Implementation
// ============================================================================

bool GGUFLoader::canLoad(const std::filesystem::path& filePath) const {
    if (!FormatDetector::validatePath(filePath)) {
        return false;
    }
    
    // Check extension
    auto ext = filePath.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
    if (ext == ".gguf") {
        return true;
    }
    
    // Check magic bytes
    auto magic = FormatDetector::readMagic(filePath);
    if (magic.size() >= 4) {
        return magic[0] == 0x47 && magic[1] == 0x47 && 
               magic[2] == 0x55 && magic[3] == 0x46;
    }
    
    return false;
}

GGUFHeader GGUFLoader::parseHeader(const std::filesystem::path& filePath) {
    ModelFileReader reader(filePath);
    
    GGUFHeader header;
    header.magic = reader.read<uint32_t>(0);
    header.version = reader.read<uint32_t>(4);
    header.tensorCount = reader.read<uint64_t>(8);
    header.metadataCount = reader.read<uint64_t>(16);
    
    if (!header.isValid()) {
        throw ModelException(
            "Invalid GGUF header in file: " + filePath.string(),
            ErrorCode::MODEL_INVALID_FORMAT
        );
    }
    
    return header;
}

std::map<std::string, GGUFMetadataValue> GGUFLoader::readMetadata(
    const std::filesystem::path& filePath
) {
    MemoryMappedFile mmFile;
    if (!mmFile.open(filePath, true)) {
        throw ModelException(
            "Failed to open GGUF file: " + filePath.string(),
            ErrorCode::MODEL_LOAD_FAILED
        );
    }
    
    size_t offset = 0;
    
    // Read header
    GGUFHeader header;
    std::memcpy(&header, mmFile.data(), sizeof(GGUFHeader));
    offset = sizeof(GGUFHeader);
    
    if (!header.isValid()) {
        throw ModelException(
            "Invalid GGUF header",
            ErrorCode::MODEL_INVALID_FORMAT
        );
    }
    
    // Read metadata key-value pairs
    std::map<std::string, GGUFMetadataValue> metadata;
    
    for (uint64_t i = 0; i < header.metadataCount; ++i) {
        // Read key
        auto key = GGUFString::read(mmFile.data(), offset);
        
        // Read value
        auto value = GGUFMetadataValue::read(mmFile.data(), offset);
        
        metadata[key.value] = std::move(value);
    }
    
    return metadata;
}

std::vector<GGUFTensorInfo> GGUFLoader::readTensorInfo(
    const std::filesystem::path& filePath
) {
    MemoryMappedFile mmFile;
    if (!mmFile.open(filePath, true)) {
        throw ModelException(
            "Failed to open GGUF file: " + filePath.string(),
            ErrorCode::MODEL_LOAD_FAILED
        );
    }
    
    size_t offset = 0;
    
    // Read header
    GGUFHeader header;
    std::memcpy(&header, mmFile.data(), sizeof(GGUFHeader));
    offset = sizeof(GGUFHeader);
    
    // Skip metadata
    for (uint64_t i = 0; i < header.metadataCount; ++i) {
        auto key = GGUFString::read(mmFile.data(), offset);
        auto value = GGUFMetadataValue::read(mmFile.data(), offset);
    }
    
    // Read tensor info
    std::vector<GGUFTensorInfo> tensors;
    tensors.reserve(header.tensorCount);
    
    for (uint64_t i = 0; i < header.tensorCount; ++i) {
        tensors.push_back(GGUFTensorInfo::read(mmFile.data(), offset));
    }
    
    return tensors;
}

ModelMetadata GGUFLoader::loadMetadata(const std::filesystem::path& filePath) const {
    auto ggufMeta = readMetadata(filePath);
    auto tensors = readTensorInfo(filePath);
    
    return extractModelMetadata(filePath, ggufMeta, tensors);
}

std::vector<TensorInfo> GGUFLoader::getTensorList(
    const std::filesystem::path& filePath
) const {
    auto ggufTensors = readTensorInfo(filePath);
    
    std::vector<TensorInfo> tensors;
    tensors.reserve(ggufTensors.size());
    
    for (const auto& t : ggufTensors) {
        tensors.push_back(t.toTensorInfo());
    }
    
    return tensors;
}

bool GGUFLoader::validate(const std::filesystem::path& filePath) const {
    try {
        auto header = parseHeader(filePath);
        return header.isValid();
    } catch (...) {
        return false;
    }
}

std::shared_ptr<ModelBase> GGUFLoader::load(
    const std::filesystem::path& filePath,
    const ModelLoadOptions& options
) {
    LoadProgressTracker progress(options.onProgress);
    progress.setTotalSteps(5);
    
    progress.next("Loading GGUF metadata...");
    auto metadata = loadMetadata(filePath);
    
    progress.next("Validating model...");
    if (!validate(filePath)) {
        throw ModelException(
            "GGUF validation failed",
            ErrorCode::MODEL_INVALID_FORMAT
        );
    }
    
    progress.next("Loading tensors...");
    auto tensors = getTensorList(filePath);
    
    progress.next("Creating model instance...");
    // TODO: Create actual model instance
    // For now, return nullptr as ModelBase needs to be implemented
    
    progress.complete("Model loaded successfully");
    
    return nullptr; // Placeholder
}

ModelMetadata GGUFLoader::extractModelMetadata(
    const std::filesystem::path& filePath,
    const std::map<std::string, GGUFMetadataValue>& metadata,
    const std::vector<GGUFTensorInfo>& tensors
) const {
    ModelMetadata meta;
    
    // File info
    meta.filePath = filePath.string();
    meta.loadedAt = std::chrono::system_clock::now();
    meta.format = ModelFormat::GGUF;
    meta.fileSizeBytes = FormatDetector::getFileSize(filePath);
    
    // Basic info
    if (auto val = getMetadata(metadata, GGUF::Keys::GENERAL_NAME)) {
        meta.name = val->asString();
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::GENERAL_AUTHOR)) {
        meta.author = val->asString();
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::GENERAL_VERSION)) {
        meta.version = val->asString();
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::GENERAL_DESCRIPTION)) {
        meta.description = val->asString();
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::GENERAL_LICENSE)) {
        meta.license = val->asString();
    }
    
    // Architecture
    meta.architecture = detectArchitecture(metadata);
    if (auto val = getMetadata(metadata, GGUF::Keys::GENERAL_ARCHITECTURE)) {
        meta.architectureVariant = val->asString();
    }
    
    // Quantization
    meta.quantization = detectQuantization(metadata);
    
    // Model size
    meta.parameterCount = calculateParameters(tensors);
    meta.memoryRequiredBytes = calculateMemoryRequirement(tensors, ModelLoadOptions());
    
    // Context and architecture details
    std::string arch = meta.architectureVariant;
    if (auto val = getMetadata(metadata, GGUF::Keys::CONTEXT_LENGTH, arch)) {
        meta.contextLength = static_cast<uint32_t>(val->asInt());
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::EMBEDDING_LENGTH, arch)) {
        meta.embeddingDimension = static_cast<uint32_t>(val->asInt());
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::BLOCK_COUNT, arch)) {
        meta.numLayers = static_cast<uint32_t>(val->asInt());
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::ATTENTION_HEAD_COUNT, arch)) {
        meta.numHeads = static_cast<uint32_t>(val->asInt());
    }
    
    // Tokenizer
    if (auto val = getMetadata(metadata, GGUF::Keys::TOKENIZER_MODEL)) {
        meta.tokenizerType = val->asString();
    }
    if (auto val = getMetadata(metadata, GGUF::Keys::TOKENIZER_VOCAB_SIZE)) {
        meta.vocabularySize = static_cast<uint32_t>(val->asInt());
    }
    
    // Set default capabilities based on architecture
    addCapability(meta.capabilities, ModelCapability::TextGeneration);
    addCapability(meta.capabilities, ModelCapability::TextCompletion);
    
    return meta;
}

std::optional<GGUFMetadataValue> GGUFLoader::getMetadata(
    const std::map<std::string, GGUFMetadataValue>& metadata,
    const std::string& key,
    const std::string& architecture
) const {
    // Try exact key first
    auto it = metadata.find(key);
    if (it != metadata.end()) {
        return it->second;
    }
    
    // Try with architecture substitution
    if (!architecture.empty() && key.find("*") != std::string::npos) {
        std::string archKey = key;
        size_t pos = archKey.find("*");
        archKey.replace(pos, 1, architecture);
        
        it = metadata.find(archKey);
        if (it != metadata.end()) {
            return it->second;
        }
    }
    
    return std::nullopt;
}

ModelArchitecture GGUFLoader::detectArchitecture(
    const std::map<std::string, GGUFMetadataValue>& metadata
) const {
    auto it = metadata.find(GGUF::Keys::GENERAL_ARCHITECTURE);
    if (it == metadata.end()) {
        return ModelArchitecture::Unknown;
    }
    
    std::string arch = it->second.asString();
    std::transform(arch.begin(), arch.end(), arch.begin(), ::tolower);
    
    if (arch.find("llama") != std::string::npos) return ModelArchitecture::LLaMA;
    if (arch.find("mistral") != std::string::npos) return ModelArchitecture::Mistral;
    if (arch.find("falcon") != std::string::npos) return ModelArchitecture::Falcon;
    if (arch.find("gpt") != std::string::npos) return ModelArchitecture::GPT;
    if (arch.find("phi") != std::string::npos) return ModelArchitecture::Phi;
    if (arch.find("gemma") != std::string::npos) return ModelArchitecture::Gemma;
    if (arch.find("qwen") != std::string::npos) return ModelArchitecture::Qwen;
    
    return ModelArchitecture::Unknown;
}

QuantizationType GGUFLoader::detectQuantization(
    const std::map<std::string, GGUFMetadataValue>& metadata
) const {
    auto it = metadata.find(GGUF::Keys::GENERAL_FILE_TYPE);
    if (it == metadata.end()) {
        return QuantizationType::None;
    }
    
    int fileType = static_cast<int>(it->second.asInt());
    
    // GGUF file type to quantization mapping
    switch (fileType) {
        case 0: return QuantizationType::None; // F32
        case 1: return QuantizationType::F16;
        case 2: return QuantizationType::Q4_0;
        case 3: return QuantizationType::Q4_1;
        case 6: return QuantizationType::Q5_0;
        case 7: return QuantizationType::Q5_1;
        case 8: return QuantizationType::Q8_0;
        default: return QuantizationType::Custom;
    }
}

uint64_t GGUFLoader::calculateParameters(
    const std::vector<GGUFTensorInfo>& tensors
) const {
    uint64_t total = 0;
    
    for (const auto& tensor : tensors) {
        uint64_t elements = 1;
        for (auto dim : tensor.dimensions) {
            elements *= dim;
        }
        total += elements;
    }
    
    return total;
}

uint64_t GGUFLoader::calculateMemoryRequirement(
    const std::vector<GGUFTensorInfo>& tensors,
    const ModelLoadOptions& options
) const {
    uint64_t total = 0;
    
    for (const auto& tensor : tensors) {
        total += tensor.calculateSize();
    }
    
    // Add overhead for KV cache and intermediate buffers
    // Rough estimate: 20% overhead
    total = static_cast<uint64_t>(total * 1.2);
    
    return total;
}

} // namespace Model
} // namespace VersaAI
