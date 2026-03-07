#include "VersaAIModel.hpp"
#include "VersaAILogger.hpp"
#include <sstream>
#include <fstream>
#include <filesystem>
#include <algorithm>
#include <iomanip>

// For SHA256 checksum (simplified - in production use OpenSSL or similar)
#include <cstring>

namespace VersaAI {

// ============================================================================
// ModelMetadata Implementation
// ============================================================================

bool ModelMetadata::hasCapability(ModelCapability cap) const {
    return std::find(capabilities.begin(), capabilities.end(), cap) != capabilities.end();
}

void ModelMetadata::addCustomField(const std::string& key, const std::string& value) {
    customFields[key] = value;
}

std::optional<std::string> ModelMetadata::getCustomField(const std::string& key) const {
    auto it = customFields.find(key);
    if (it != customFields.end()) {
        return it->second;
    }
    return std::nullopt;
}

std::string ModelMetadata::toJson() const {
    std::ostringstream oss;
    oss << "{\n";
    oss << "  \"name\": \"" << name << "\",\n";
    oss << "  \"version\": \"" << version << "\",\n";
    oss << "  \"description\": \"" << description << "\",\n";
    oss << "  \"author\": \"" << author << "\",\n";
    oss << "  \"license\": \"" << license << "\",\n";
    oss << "  \"format\": \"" << modelFormatToString(format) << "\",\n";
    oss << "  \"architecture\": \"" << modelArchitectureToString(architecture) << "\",\n";
    oss << "  \"quantization\": \"" << quantizationTypeToString(quantization) << "\",\n";
    oss << "  \"parameterCount\": " << parameterCount << ",\n";
    oss << "  \"contextLength\": " << contextLength << ",\n";
    oss << "  \"vocabularySize\": " << vocabularySize << ",\n";
    oss << "  \"filePath\": \"" << filePath << "\",\n";
    oss << "  \"fileSize\": " << fileSize << ",\n";
    oss << "  \"checksum\": \"" << checksum << "\"\n";
    oss << "}";
    return oss.str();
}

ModelMetadata ModelMetadata::fromJson(const std::string& json) {
    // Simplified JSON parsing - in production use a proper JSON library
    ModelMetadata metadata;
    // TODO: Implement proper JSON parsing
    return metadata;
}

bool ModelMetadata::validate() const {
    if (name.empty()) return false;
    if (version.empty()) return false;
    if (filePath.empty()) return false;
    if (format == ModelFormat::UNKNOWN) return false;
    if (parameterCount == 0) return false;
    if (contextLength == 0) return false;
    if (capabilities.empty()) return false;
    return true;
}

// ============================================================================
// ModelBase Implementation
// ============================================================================

ModelBase::ModelBase(const ModelMetadata& metadata)
    : metadata_(metadata), state_(ModelState::UNLOADED) {
    logOperation("ModelBase constructed", "Model: " + metadata_.name);
}

ModelBase::~ModelBase() {
    // Note: Can't call virtual unload() from destructor
    // Derived classes must ensure unload() is called before destruction
    if (state_ == ModelState::LOADED) {
        logOperation("ModelBase destroyed while still loaded",
                    "Model: " + metadata_.name + " (Warning: Resource leak possible)");
    }
    logOperation("ModelBase destroyed", "Model: " + metadata_.name);
}

void ModelBase::setState(ModelState newState) {
    ModelState oldState = state_;
    state_ = newState;

    std::string oldStateStr = std::to_string(static_cast<int>(oldState));
    std::string newStateStr = std::to_string(static_cast<int>(newState));

    logOperation("State transition",
        "Model: " + metadata_.name + ", " + oldStateStr + " -> " + newStateStr);
}

void ModelBase::logOperation(const std::string& operation, const std::string& details) const {
    LogEntry entry(LogLevel::DEBUG, operation, "ModelBase");
    entry.addContext("model_name", metadata_.name);
    if (!details.empty()) {
        entry.addContext("details", details);
    }
    Logger::getInstance().log(entry);
}

std::vector<float> ModelBase::getEmbeddings(const std::string& /* text */) {
    throw ModelException(
        "Model does not support embeddings",
        ErrorCode::MODEL_INFERENCE_FAILED
    ).setModelName(metadata_.name)
     .addContext("capability", "embeddings");
}

void ModelBase::validate() {
    if (!std::filesystem::exists(metadata_.filePath)) {
        throw ModelException(
            "Model file not found",
            ErrorCode::MODEL_NOT_FOUND
        ).setModelPath(metadata_.filePath);
    }

    auto fileSize = std::filesystem::file_size(metadata_.filePath);
    if (fileSize != metadata_.fileSize) {
        Logger::getInstance().warning(
            "Model file size mismatch: expected " +
            std::to_string(metadata_.fileSize) + ", got " +
            std::to_string(fileSize),
            "ModelBase"
        );
    }

    // TODO: Verify checksum
    if (!metadata_.checksum.empty()) {
        // std::string actualChecksum = calculateChecksum(metadata_.filePath);
        // if (actualChecksum != metadata_.checksum) {
        //     throw ModelException("Checksum mismatch", ErrorCode::MODEL_INVALID_FORMAT);
        // }
    }
}

void ModelBase::updatePerformanceMetrics(const PerformanceMetrics& metrics) {
    metadata_.performance = metrics;
    metadata_.performance.lastMeasured = std::chrono::system_clock::now();
}

// ============================================================================
// Utility Functions
// ============================================================================

std::string modelFormatToString(ModelFormat format) {
    switch (format) {
        case ModelFormat::GGUF: return "GGUF";
        case ModelFormat::SAFETENSORS: return "SafeTensors";
        case ModelFormat::ONNX: return "ONNX";
        case ModelFormat::PYTORCH: return "PyTorch";
        case ModelFormat::TENSORFLOW: return "TensorFlow";
        case ModelFormat::UNKNOWN: return "Unknown";
        default: return "Unknown";
    }
}

ModelFormat stringToModelFormat(const std::string& str) {
    if (str == "GGUF") return ModelFormat::GGUF;
    if (str == "SafeTensors") return ModelFormat::SAFETENSORS;
    if (str == "ONNX") return ModelFormat::ONNX;
    if (str == "PyTorch") return ModelFormat::PYTORCH;
    if (str == "TensorFlow") return ModelFormat::TENSORFLOW;
    return ModelFormat::UNKNOWN;
}

std::string modelArchitectureToString(ModelArchitecture arch) {
    switch (arch) {
        case ModelArchitecture::LLAMA: return "LLaMA";
        case ModelArchitecture::GPT: return "GPT";
        case ModelArchitecture::MISTRAL: return "Mistral";
        case ModelArchitecture::MIXTRAL: return "Mixtral";
        case ModelArchitecture::GEMMA: return "Gemma";
        case ModelArchitecture::PHI: return "Phi";
        case ModelArchitecture::BERT: return "BERT";
        case ModelArchitecture::T5: return "T5";
        case ModelArchitecture::CUSTOM: return "Custom";
        case ModelArchitecture::UNKNOWN: return "Unknown";
        default: return "Unknown";
    }
}

std::string modelCapabilityToString(ModelCapability cap) {
    switch (cap) {
        case ModelCapability::TEXT_GENERATION: return "TextGeneration";
        case ModelCapability::EMBEDDINGS: return "Embeddings";
        case ModelCapability::CLASSIFICATION: return "Classification";
        case ModelCapability::QUESTION_ANSWERING: return "QuestionAnswering";
        case ModelCapability::SUMMARIZATION: return "Summarization";
        case ModelCapability::TRANSLATION: return "Translation";
        case ModelCapability::CODE_GENERATION: return "CodeGeneration";
        case ModelCapability::CHAT: return "Chat";
        case ModelCapability::MULTIMODAL: return "Multimodal";
        default: return "Unknown";
    }
}

std::string quantizationTypeToString(QuantizationType quant) {
    switch (quant) {
        case QuantizationType::NONE: return "None";
        case QuantizationType::Q8_0: return "Q8_0";
        case QuantizationType::Q4_0: return "Q4_0";
        case QuantizationType::Q4_1: return "Q4_1";
        case QuantizationType::Q5_0: return "Q5_0";
        case QuantizationType::Q5_1: return "Q5_1";
        case QuantizationType::Q2_K: return "Q2_K";
        case QuantizationType::Q3_K: return "Q3_K";
        case QuantizationType::Q4_K: return "Q4_K";
        case QuantizationType::Q5_K: return "Q5_K";
        case QuantizationType::Q6_K: return "Q6_K";
        default: return "Unknown";
    }
}

ModelFormat detectModelFormat(const std::string& filePath) {
    std::filesystem::path path(filePath);
    std::string ext = path.extension().string();

    // Convert to lowercase
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

    if (ext == ".gguf") return ModelFormat::GGUF;
    if (ext == ".safetensors") return ModelFormat::SAFETENSORS;
    if (ext == ".onnx") return ModelFormat::ONNX;
    if (ext == ".pt" || ext == ".pth") return ModelFormat::PYTORCH;
    if (ext == ".pb") return ModelFormat::TENSORFLOW;

    return ModelFormat::UNKNOWN;
}

std::string calculateChecksum(const std::string& filePath) {
    // Simplified SHA256 - in production use OpenSSL or similar
    // For now, return placeholder
    (void)filePath;  // Suppress unused warning
    return "placeholder_checksum";

    // TODO: Implement actual SHA256
    // std::ifstream file(filePath, std::ios::binary);
    // ... SHA256 calculation ...
}

} // namespace VersaAI
