/**
 * @file model_loader_example.cpp
 * @brief Example demonstrating VersaAI model loading system
 * 
 * Shows how to:
 * - Load model metadata
 * - Detect model format
 * - Use GGUF loader
 * - Handle model lifecycle
 */

#include "../include/VersaAIModelLoader.hpp"
#include "../include/VersaAIGGUFLoader.hpp"
#include "../include/VersaAIModelBase.hpp"
#include "../include/VersaAILogger.hpp"
#include <iostream>
#include <iomanip>

using namespace VersaAI;
using namespace VersaAI::Model;

// ============================================================================
// Example 1: Model Format Detection
// ============================================================================

void example1_formatDetection() {
    std::cout << "\n=== Example 1: Model Format Detection ===\n\n";
    
    // Simulate different file paths
    std::vector<std::string> testFiles = {
        "model.gguf",
        "model.ggml",
        "model.onnx",
        "model.safetensors",
        "model.pth",
        "model.pt"
    };
    
    for (const auto& file : testFiles) {
        auto format = FormatDetector::detectFromExtension(file);
        std::cout << std::setw(20) << file << " -> " 
                  << formatToString(format) << "\n";
    }
}

// ============================================================================
// Example 2: Model Metadata
// ============================================================================

void example2_modelMetadata() {
    std::cout << "\n=== Example 2: Model Metadata ===\n\n";
    
    // Create sample metadata
    ModelMetadata meta;
    meta.name = "LLaMA-2-7B-Chat";
    meta.version = "1.0";
    meta.author = "Meta AI";
    meta.license = "LLaMA 2 License";
    meta.description = "7B parameter LLaMA 2 model fine-tuned for chat";
    
    meta.architecture = ModelArchitecture::LLaMA;
    meta.architectureVariant = "llama-2-7b";
    meta.format = ModelFormat::GGUF;
    meta.quantization = QuantizationType::Q4_0;
    
    meta.parameterCount = 7'000'000'000;  // 7B parameters
    meta.contextLength = 4096;
    meta.embeddingDimension = 4096;
    meta.vocabularySize = 32000;
    meta.numLayers = 32;
    meta.numHeads = 32;
    
    meta.fileSizeBytes = 4'000'000'000;  // ~4GB
    meta.memoryRequiredBytes = 5'000'000'000;  // ~5GB
    
    // Add capabilities
    addCapability(meta.capabilities, ModelCapability::TextGeneration);
    addCapability(meta.capabilities, ModelCapability::ChatConversation);
    addCapability(meta.capabilities, ModelCapability::InstructionTuned);
    
    meta.tokenizerType = "BPE";
    meta.bosToken = "<s>";
    meta.eosToken = "</s>";
    
    // Print summary
    std::cout << meta.getSummary() << "\n";
    
    // Check capabilities
    std::cout << "\nCapabilities:\n";
    std::cout << "  Text Generation: " 
              << (hasCapability(meta.capabilities, ModelCapability::TextGeneration) ? "Yes" : "No") << "\n";
    std::cout << "  Chat: " 
              << (hasCapability(meta.capabilities, ModelCapability::ChatConversation) ? "Yes" : "No") << "\n";
    std::cout << "  Code Generation: " 
              << (hasCapability(meta.capabilities, ModelCapability::CodeGeneration) ? "Yes" : "No") << "\n";
    std::cout << "  Function Calling: " 
              << (hasCapability(meta.capabilities, ModelCapability::FunctionCalling) ? "Yes" : "No") << "\n";
}

// ============================================================================
// Example 3: GGUF Loader Registration
// ============================================================================

void example3_loaderRegistration() {
    std::cout << "\n=== Example 3: Loader Registration ===\n\n";
    
    auto& factory = ModelLoaderFactory::getInstance();
    
    // Register GGUF loader
    factory.registerLoader(
        ModelFormat::GGUF,
        []() { return std::make_unique<GGUFLoader>(); }
    );
    
    std::cout << "Registered GGUF loader\n";
    
    // Get supported formats
    auto formats = factory.getSupportedFormats();
    std::cout << "\nSupported formats: " << formats.size() << "\n";
    for (const auto& format : formats) {
        std::cout << "  - " << formatToString(format) << "\n";
    }
}

// ============================================================================
// Example 4: Model Load Options
// ============================================================================

void example4_loadOptions() {
    std::cout << "\n=== Example 4: Model Load Options ===\n\n";
    
    ModelLoadOptions options;
    
    // Memory management
    options.useMemoryMapping = true;
    options.lockMemory = false;  // Don't lock in RAM (uses more memory)
    
    // Device selection
    options.device = ModelLoadOptions::Device::Auto;  // Auto-detect best device
    options.deviceId = 0;
    
    // Performance
    options.numThreads = 8;
    options.enableF16 = true;
    options.enableFlashAttention = true;
    
    // Context
    options.contextSize = 2048;  // Override to 2K context
    options.batchSize = 512;
    
    // GPU offloading
    options.numGPULayers = 32;  // Offload 32 layers to GPU
    
    // Validation
    options.validateChecksum = true;
    options.validateTensors = true;
    
    // Progress callback
    options.onProgress = [](float progress, const std::string& status) {
        std::cout << "[" << std::setw(3) << static_cast<int>(progress * 100) 
                  << "%] " << status << "\n";
    };
    
    std::cout << "Configured load options:\n";
    std::cout << "  Memory mapping: " << (options.useMemoryMapping ? "Yes" : "No") << "\n";
    std::cout << "  Lock memory: " << (options.lockMemory ? "Yes" : "No") << "\n";
    std::cout << "  Threads: " << options.numThreads << "\n";
    std::cout << "  FP16: " << (options.enableF16 ? "Yes" : "No") << "\n";
    std::cout << "  Flash Attention: " << (options.enableFlashAttention ? "Yes" : "No") << "\n";
    std::cout << "  Context size: " << options.contextSize << "\n";
    std::cout << "  GPU layers: " << options.numGPULayers << "\n";
}

// ============================================================================
// Example 5: Generic Model Usage
// ============================================================================

void example5_genericModel() {
    std::cout << "\n=== Example 5: Generic Model Usage ===\n\n";
    
    // Create metadata
    ModelMetadata meta;
    meta.name = "Test Model";
    meta.format = ModelFormat::GGUF;
    meta.architecture = ModelArchitecture::GPT;
    meta.parameterCount = 1'000'000;
    meta.memoryRequiredBytes = 4'000'000;
    
    // Create model
    auto model = makeModel<GenericModel>(meta);
    
    std::cout << "Initial state: " << modelStateToString(model->getState()) << "\n";
    
    // Initialize
    if (model->initialize()) {
        std::cout << "Model initialized successfully\n";
        std::cout << "State: " << modelStateToString(model->getState()) << "\n";
        std::cout << "Ready: " << (model->isReady() ? "Yes" : "No") << "\n";
        std::cout << "Memory usage: " << (model->getMemoryUsage() / 1024 / 1024) << " MB\n";
    }
    
    // Validate
    if (model->validate()) {
        std::cout << "Model validation: OK\n";
    }
    
    // Shutdown
    model->shutdown();
    std::cout << "After shutdown: " << modelStateToString(model->getState()) << "\n";
}

// ============================================================================
// Example 6: Tensor Information
// ============================================================================

void example6_tensorInfo() {
    std::cout << "\n=== Example 6: Tensor Information ===\n\n";
    
    // Create sample tensor info
    TensorInfo tensor;
    tensor.name = "model.layers.0.attention.wq.weight";
    tensor.dataType = TensorDataType::Float16;
    tensor.shape = {4096, 4096};
    tensor.numElements = tensor.shape[0] * tensor.shape[1];
    tensor.sizeBytes = tensor.numElements * getTensorDataTypeSize(tensor.dataType);
    
    std::cout << "Tensor: " << tensor.name << "\n";
    std::cout << "  Shape: " << tensor.getShapeString() << "\n";
    std::cout << "  Data Type: " << "Float16" << "\n";
    std::cout << "  Elements: " << tensor.numElements << "\n";
    std::cout << "  Size: " << (tensor.sizeBytes / 1024 / 1024) << " MB\n";
}

// ============================================================================
// Example 7: GGML Type Conversions
// ============================================================================

void example7_ggmlTypes() {
    std::cout << "\n=== Example 7: GGML Type Conversions ===\n\n";
    
    std::vector<GGMLType> types = {
        GGMLType::F32,
        GGMLType::F16,
        GGMLType::Q4_0,
        GGMLType::Q4_1,
        GGMLType::Q5_0,
        GGMLType::Q8_0,
        GGMLType::I8
    };
    
    std::cout << "GGML Type Conversions:\n";
    std::cout << std::setw(10) << "GGML Type" 
              << std::setw(15) << "Quantization" 
              << std::setw(15) << "Size (bytes)\n";
    std::cout << std::string(40, '-') << "\n";
    
    for (const auto& type : types) {
        auto quant = ggmlTypeToQuantization(type);
        auto size = getGGMLTypeSize(type);
        
        std::cout << std::setw(10) << static_cast<int>(type)
                  << std::setw(15) << quantizationToString(quant)
                  << std::setw(15) << size << "\n";
    }
}

// ============================================================================
// Example 8: Memory-Mapped File (Simulated)
// ============================================================================

void example8_memoryMapping() {
    std::cout << "\n=== Example 8: Memory-Mapped File Concept ===\n\n";
    
    std::cout << "Memory-mapped files provide:\n";
    std::cout << "  ✓ Efficient large file access\n";
    std::cout << "  ✓ OS-level caching\n";
    std::cout << "  ✓ Reduced memory footprint\n";
    std::cout << "  ✓ Fast random access\n";
    std::cout << "  ✓ Automatic paging\n\n";
    
    std::cout << "For a 4GB model file:\n";
    std::cout << "  Traditional load: 4GB+ RAM required immediately\n";
    std::cout << "  Memory-mapped:    Only accessed pages loaded (~100-500MB)\n";
    std::cout << "  Speed:            Direct memory access (no read() calls)\n";
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "=================================================\n";
    std::cout << "     VersaAI Model Loader System Examples\n";
    std::cout << "=================================================\n";
    
    try {
        // Initialize logging
        Logger::getInstance().setLogLevel(LogLevel::INFO);
        
        // Run examples
        example1_formatDetection();
        example2_modelMetadata();
        example3_loaderRegistration();
        example4_loadOptions();
        example5_genericModel();
        example6_tensorInfo();
        example7_ggmlTypes();
        example8_memoryMapping();
        
        std::cout << "\n=================================================\n";
        std::cout << "         All examples completed successfully!\n";
        std::cout << "=================================================\n\n";
        
        std::cout << "Note: To load actual models, you need:\n";
        std::cout << "  1. A valid GGUF model file\n";
        std::cout << "  2. Enough RAM (check model metadata)\n";
        std::cout << "  3. Optional: CUDA/ROCm for GPU acceleration\n\n";
        
        std::cout << "Example usage with real model:\n";
        std::cout << "  auto metadata = loadModelMetadata(\"model.gguf\");\n";
        std::cout << "  std::cout << metadata.getSummary();\n";
        std::cout << "  auto model = loadModel(\"model.gguf\", options);\n\n";
        
        return 0;
        
    } catch (const Exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        std::cerr << "Code: " << static_cast<int>(e.getErrorCode()) << "\n";
        return 1;
    } catch (const std::exception& e) {
        std::cerr << "Unexpected error: " << e.what() << "\n";
        return 1;
    }
}
