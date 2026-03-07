# Model Loading System - Quick Reference

## 🚀 Quick Start

### Load a Model (Auto-detect format)
```cpp
#include "VersaAIModelLoader.hpp"

// Simple loading
auto model = VersaAI::Model::loadModel("path/to/model.gguf");

// With options
VersaAI::Model::ModelLoadOptions opts;
opts.device = VersaAI::Model::ModelLoadOptions::Device::CUDA;
opts.useMemoryMapping = true;
opts.numGPULayers = 32;

auto model = VersaAI::Model::loadModel("path/to/model.gguf", opts);
```

### Load Metadata Only
```cpp
auto metadata = VersaAI::Model::loadModelMetadata("path/to/model.safetensors");

std::cout << metadata.getSummary() << std::endl;
std::cout << "Parameters: " << metadata.parameterCount << std::endl;
std::cout << "Context: " << metadata.contextLength << std::endl;
```

## 📝 Supported Formats

| Extension | Format | Loader Class | Status |
|-----------|--------|--------------|--------|
| `.gguf` | GGUF (llama.cpp) | `GGUFLoader` | ✅ Full |
| `.safetensors` | SafeTensors (HF) | `SafeTensorsLoader` | ✅ Full |
| `.onnx` | ONNX | `ONNXLoader` | ✅ Core |

## 🔧 Common Tasks

### Check if File is Supported
```cpp
auto& factory = VersaAI::Model::ModelLoaderFactory::getInstance();
auto format = factory.detectFormat("model.gguf");

if (format != VersaAI::Model::ModelFormat::Unknown) {
    std::cout << "Format: " << formatToString(format) << std::endl;
}
```

### Get Tensor List
```cpp
VersaAI::Model::GGUFLoader loader;
auto tensors = loader.getTensorList("model.gguf");

for (const auto& tensor : tensors) {
    std::cout << tensor.name << ": " 
              << tensor.getShapeString() 
              << " (" << tensor.sizeBytes << " bytes)" 
              << std::endl;
}
```

### Memory-Mapped Access
```cpp
VersaAI::Model::MemoryMappedFile mmf;
if (mmf.open("large_model.safetensors", true)) {
    // Direct access to file data
    const void* data = mmf.data();
    size_t size = mmf.size();
    
    // Read specific offset
    auto header = mmf.at<uint64_t>(0);
    
    // Lock in memory (prevent swapping)
    mmf.lock();
}
```

### Progress Tracking
```cpp
VersaAI::Model::ModelLoadOptions opts;
opts.onProgress = [](float progress, const std::string& status) {
    std::cout << status << ": " << (progress * 100.0f) << "%" << std::endl;
};

auto model = VersaAI::Model::loadModel("model.gguf", opts);
```

### Custom Loader Registration
```cpp
auto& factory = VersaAI::Model::ModelLoaderFactory::getInstance();

// Register custom loader
factory.registerLoader(
    VersaAI::Model::ModelFormat::Custom,
    []() { return std::make_unique<MyCustomLoader>(); }
);

// Use it
auto loader = factory.getLoader(VersaAI::Model::ModelFormat::Custom);
```

## 📊 Model Metadata

### Architecture Detection
```cpp
auto metadata = VersaAI::Model::loadModelMetadata("model.gguf");

switch (metadata.architecture) {
    case VersaAI::Model::ModelArchitecture::LLaMA:
        std::cout << "LLaMA model detected" << std::endl;
        break;
    case VersaAI::Model::ModelArchitecture::Mistral:
        std::cout << "Mistral model detected" << std::endl;
        break;
    // ...
}
```

### Quantization Info
```cpp
auto metadata = VersaAI::Model::loadModelMetadata("model.gguf");

std::cout << "Quantization: " 
          << quantizationToString(metadata.quantization) 
          << std::endl;

if (metadata.quantization == VersaAI::Model::QuantizationType::Q4_0) {
    // 4-bit quantized model
}
```

### Custom Metadata
```cpp
// Set custom metadata
metadata.setMetadata("custom_field", "custom_value");
metadata.setMetadata("batch_size", int64_t(32));

// Get custom metadata
auto value = metadata.getMetadata<std::string>("custom_field");
if (value) {
    std::cout << "Custom field: " << *value << std::endl;
}
```

## 🎛️ Loading Options

### Device Selection
```cpp
ModelLoadOptions opts;

// Auto-select best device
opts.device = ModelLoadOptions::Device::Auto;

// Force specific device
opts.device = ModelLoadOptions::Device::CUDA;
opts.deviceId = 0;  // First GPU

// Force CPU
opts.device = ModelLoadOptions::Device::CPU;
opts.numThreads = 8;
```

### Memory Options
```cpp
ModelLoadOptions opts;

// Memory mapping (recommended for large models)
opts.useMemoryMapping = true;

// Lock pages in RAM (prevent swapping)
opts.lockMemory = true;

// Pre-allocate memory
opts.preAllocateBytes = 8ULL * 1024 * 1024 * 1024;  // 8GB
```

### GPU Offloading
```cpp
ModelLoadOptions opts;
opts.device = ModelLoadOptions::Device::CUDA;

// Offload all layers
opts.numGPULayers = -1;

// Offload first 32 layers
opts.numGPULayers = 32;

// CPU only
opts.numGPULayers = 0;
```

### Performance Tuning
```cpp
ModelLoadOptions opts;

// Enable FP16 for KV cache
opts.enableF16 = true;

// Enable Flash Attention
opts.enableFlashAttention = true;

// Context and batch size
opts.contextSize = 4096;
opts.batchSize = 512;
```

### Validation
```cpp
ModelLoadOptions opts;

// Validate file integrity
opts.validateChecksum = true;

// Validate tensor shapes/types
opts.validateTensors = true;
```

## 🔍 Format-Specific Features

### GGUF
```cpp
VersaAI::Model::GGUFLoader loader;

// Parse header
auto header = VersaAI::Model::GGUFLoader::parseHeader("model.gguf");
std::cout << "Version: " << header.version << std::endl;
std::cout << "Tensors: " << header.tensorCount << std::endl;

// Read metadata
auto metadata = VersaAI::Model::GGUFLoader::readMetadata("model.gguf");
for (const auto& [key, value] : metadata) {
    std::cout << key << " = " << value.asString() << std::endl;
}
```

### SafeTensors
```cpp
VersaAI::Model::SafeTensorsLoader loader;

// Parse header
auto stMetadata = VersaAI::Model::SafeTensorsLoader::parseHeader("model.safetensors");
std::cout << "Tensors: " << stMetadata.tensorCount() << std::endl;

// Get tensor data location (for mmap access)
auto [offset, endOffset] = VersaAI::Model::SafeTensorsLoader::getTensorDataLocation(
    "model.safetensors",
    "model.layers.0.weight"
);
std::cout << "Tensor at offset: " << offset << std::endl;
```

### SafeTensors Sharded Models
```cpp
VersaAI::Model::ShardedSafeTensorsLoader loader;

// Load from index file
auto model = loader.loadFromIndex(
    "model.safetensors.index.json",
    opts
);

// Get metadata from all shards
auto metadata = loader.loadMetadataFromIndex("model.safetensors.index.json");
std::cout << "Shards: " << metadata.getMetadata<int64_t>("num_shards").value() << std::endl;
```

### ONNX
```cpp
VersaAI::Model::ONNXLoader loader;

// Parse model info
auto info = VersaAI::Model::ONNXLoader::parseModelInfo("model.onnx");
std::cout << "IR Version: " << info.irVersion << std::endl;
std::cout << "Producer: " << info.producerName << std::endl;

// Check opset versions
for (const auto& [domain, version] : info.opsetImports) {
    std::cout << "Opset " << domain << ": " << version << std::endl;
}
```

## ⚠️ Error Handling

```cpp
try {
    auto model = VersaAI::Model::loadModel("model.gguf");
} catch (const VersaAI::ModelException& e) {
    std::cerr << "Model error: " << e.what() << std::endl;
    std::cerr << "Error code: " << static_cast<int>(e.getErrorCode()) << std::endl;
    
    switch (e.getErrorCode()) {
        case VersaAI::ErrorCode::MODEL_FILE_NOT_FOUND:
            // Handle missing file
            break;
        case VersaAI::ErrorCode::MODEL_INVALID_FILE:
            // Handle invalid format
            break;
        case VersaAI::ErrorCode::MODEL_LOAD_FAILED:
            // Handle load failure
            break;
    }
}
```

## 🧪 Testing Your Integration

```cpp
// Validate file before loading
VersaAI::Model::GGUFLoader loader;
if (loader.validate("model.gguf")) {
    std::cout << "Model file is valid" << std::endl;
    auto model = loader.load("model.gguf");
}

// Check format compatibility
if (loader.canLoad("model.gguf")) {
    std::cout << "Loader supports this file" << std::endl;
}
```

## 📚 See Also

- **Full Docs**: `docs/Model_Loading_System.md`
- **Architecture**: `docs/Architecture.md`
- **Phase 2.1 Summary**: `PHASE_2_1_COMPLETE_FULL.md`
- **Tests**: `tests/test_model_loaders.cpp`

---

**Last Updated**: 2025-11-14
