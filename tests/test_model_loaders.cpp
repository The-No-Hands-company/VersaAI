/**
 * @file test_model_loaders.cpp
 * @brief Comprehensive tests for model loading system
 * 
 * Tests:
 * - Format detection
 * - Metadata parsing
 * - GGUF loader
 * - ONNX loader  
 * - SafeTensors loader
 * - Model registry integration
 * - Memory-mapped loading
 * - Error handling
 * - Performance benchmarks
 */

#include <gtest/gtest.h>
#include "../include/VersaAIModelLoader.hpp"
#include "../include/VersaAIGGUFLoader.hpp"
#include "../include/VersaAIONNXLoader.hpp"
#include "../include/VersaAISafeTensorsLoader.hpp"
#include "../include/VersaAIModelFormat.hpp"
#include <filesystem>
#include <fstream>
#include <chrono>

using namespace VersaAI::Model;
namespace fs = std::filesystem;

// ============================================================================
// Test Fixtures and Helpers
// ============================================================================

class ModelLoaderTest : public ::testing::Test {
protected:
    fs::path testDataDir_;
    
    void SetUp() override {
        testDataDir_ = fs::temp_directory_path() / "versaai_model_tests";
        fs::create_directories(testDataDir_);
    }
    
    void TearDown() override {
        if (fs::exists(testDataDir_)) {
            fs::remove_all(testDataDir_);
        }
    }
    
    /**
     * @brief Create a minimal GGUF file for testing
     */
    fs::path createMockGGUFFile(const std::string& name = "test.gguf") {
        fs::path filePath = testDataDir_ / name;
        std::ofstream file(filePath, std::ios::binary);
        
        // Write GGUF header
        uint32_t magic = 0x46554747; // "GGUF"
        uint32_t version = 3;
        uint64_t tensorCount = 0;
        uint64_t metadataCount = 0;
        
        file.write(reinterpret_cast<const char*>(&magic), sizeof(magic));
        file.write(reinterpret_cast<const char*>(&version), sizeof(version));
        file.write(reinterpret_cast<const char*>(&tensorCount), sizeof(tensorCount));
        file.write(reinterpret_cast<const char*>(&metadataCount), sizeof(metadataCount));
        
        file.close();
        return filePath;
    }
    
    /**
     * @brief Create a minimal SafeTensors file for testing
     */
    fs::path createMockSafeTensorsFile(const std::string& name = "test.safetensors") {
        fs::path filePath = testDataDir_ / name;
        std::ofstream file(filePath, std::ios::binary);
        
        // Create minimal JSON header
        std::string jsonHeader = R"({"test_tensor":{"dtype":"F32","shape":[10,10],"data_offsets":[0,400]}})";
        
        // Write header size (little-endian)
        uint64_t headerSize = jsonHeader.size();
        file.write(reinterpret_cast<const char*>(&headerSize), sizeof(headerSize));
        
        // Write JSON header
        file.write(jsonHeader.c_str(), jsonHeader.size());
        
        // Write dummy tensor data (10x10 floats = 400 bytes)
        std::vector<float> dummyData(100, 1.0f);
        file.write(reinterpret_cast<const char*>(dummyData.data()), 400);
        
        file.close();
        return filePath;
    }
    
    /**
     * @brief Create a minimal ONNX file for testing
     */
    fs::path createMockONNXFile(const std::string& name = "test.onnx") {
        fs::path filePath = testDataDir_ / name;
        std::ofstream file(filePath, std::ios::binary);
        
        // Write minimal protobuf header (IR version field)
        uint8_t data[] = {0x08, 0x07}; // Field 1 (IR version), value 7
        file.write(reinterpret_cast<const char*>(data), sizeof(data));
        
        file.close();
        return filePath;
    }
};

// ============================================================================
// Format Detection Tests
// ============================================================================

TEST_F(ModelLoaderTest, DetectGGUFFormat) {
    auto filePath = createMockGGUFFile();
    
    auto format = FormatDetector::detectFromExtension(filePath);
    EXPECT_EQ(format, ModelFormat::GGUF);
    
    format = FormatDetector::detectFromMagic(filePath);
    EXPECT_EQ(format, ModelFormat::GGUF);
}

TEST_F(ModelLoaderTest, DetectSafeTensorsFormat) {
    auto filePath = createMockSafeTensorsFile();
    
    auto format = FormatDetector::detectFromExtension(filePath);
    EXPECT_EQ(format, ModelFormat::SafeTensors);
}

TEST_F(ModelLoaderTest, DetectONNXFormat) {
    auto filePath = createMockONNXFile();
    
    auto format = FormatDetector::detectFromExtension(filePath);
    EXPECT_EQ(format, ModelFormat::ONNX);
}

TEST_F(ModelLoaderTest, DetectUnknownFormat) {
    auto filePath = testDataDir_ / "unknown.xyz";
    std::ofstream file(filePath);
    file << "random data";
    file.close();
    
    auto format = FormatDetector::detectFromExtension(filePath);
    EXPECT_EQ(format, ModelFormat::Unknown);
}

TEST_F(ModelLoaderTest, ValidatePath) {
    auto validPath = createMockGGUFFile();
    EXPECT_TRUE(FormatDetector::validatePath(validPath));
    
    auto invalidPath = testDataDir_ / "nonexistent.gguf";
    EXPECT_FALSE(FormatDetector::validatePath(invalidPath));
}

TEST_F(ModelLoaderTest, GetFileSize) {
    auto filePath = createMockGGUFFile();
    auto size = FormatDetector::getFileSize(filePath);
    
    EXPECT_GT(size, 0);
    EXPECT_EQ(size, fs::file_size(filePath));
}

// ============================================================================
// GGUF Loader Tests
// ============================================================================

TEST_F(ModelLoaderTest, GGUFLoaderCanLoad) {
    GGUFLoader loader;
    
    auto ggufFile = createMockGGUFFile();
    EXPECT_TRUE(loader.canLoad(ggufFile));
    
    auto safetensorsFile = createMockSafeTensorsFile();
    EXPECT_FALSE(loader.canLoad(safetensorsFile));
}

TEST_F(ModelLoaderTest, GGUFLoaderFormat) {
    GGUFLoader loader;
    EXPECT_EQ(loader.getFormat(), ModelFormat::GGUF);
}

TEST_F(ModelLoaderTest, GGUFLoaderValidate) {
    GGUFLoader loader;
    auto filePath = createMockGGUFFile();
    
    EXPECT_TRUE(loader.validate(filePath));
}

TEST_F(ModelLoaderTest, GGUFParseHeader) {
    auto filePath = createMockGGUFFile();
    auto header = GGUFLoader::parseHeader(filePath);
    
    EXPECT_TRUE(header.isValid());
    EXPECT_EQ(header.magic, 0x46554747);
    EXPECT_EQ(header.version, 3);
    EXPECT_EQ(header.tensorCount, 0);
    EXPECT_EQ(header.metadataCount, 0);
}

TEST_F(ModelLoaderTest, GGUFLoadMetadata) {
    GGUFLoader loader;
    auto filePath = createMockGGUFFile();
    
    auto metadata = loader.loadMetadata(filePath);
    
    EXPECT_EQ(metadata.format, ModelFormat::GGUF);
    EXPECT_FALSE(metadata.filePath.empty());
    EXPECT_GT(metadata.fileSizeBytes, 0);
}

// ============================================================================
// SafeTensors Loader Tests
// ============================================================================

TEST_F(ModelLoaderTest, SafeTensorsLoaderCanLoad) {
    SafeTensorsLoader loader;
    
    auto safetensorsFile = createMockSafeTensorsFile();
    EXPECT_TRUE(loader.canLoad(safetensorsFile));
    
    auto ggufFile = createMockGGUFFile();
    EXPECT_FALSE(loader.canLoad(ggufFile));
}

TEST_F(ModelLoaderTest, SafeTensorsLoaderFormat) {
    SafeTensorsLoader loader;
    EXPECT_EQ(loader.getFormat(), ModelFormat::SafeTensors);
}

TEST_F(ModelLoaderTest, SafeTensorsLoaderValidate) {
    SafeTensorsLoader loader;
    auto filePath = createMockSafeTensorsFile();
    
    EXPECT_TRUE(loader.validate(filePath));
}

TEST_F(ModelLoaderTest, SafeTensorsParseHeader) {
    auto filePath = createMockSafeTensorsFile();
    auto metadata = SafeTensorsLoader::parseHeader(filePath);
    
    EXPECT_EQ(metadata.tensorCount(), 1);
    EXPECT_TRUE(metadata.tensors.contains("test_tensor"));
    
    auto& tensor = metadata.tensors["test_tensor"];
    EXPECT_EQ(tensor.dtype, "F32");
    EXPECT_EQ(tensor.shape.size(), 2);
    EXPECT_EQ(tensor.shape[0], 10);
    EXPECT_EQ(tensor.shape[1], 10);
}

TEST_F(ModelLoaderTest, SafeTensorsLoadMetadata) {
    SafeTensorsLoader loader;
    auto filePath = createMockSafeTensorsFile();
    
    auto metadata = loader.loadMetadata(filePath);
    
    EXPECT_EQ(metadata.format, ModelFormat::SafeTensors);
    EXPECT_GT(metadata.parameterCount, 0);
    EXPECT_GT(metadata.memoryRequiredBytes, 0);
}

TEST_F(ModelLoaderTest, SafeTensorsGetTensorList) {
    SafeTensorsLoader loader;
    auto filePath = createMockSafeTensorsFile();
    
    auto tensors = loader.getTensorList(filePath);
    
    EXPECT_EQ(tensors.size(), 1);
    EXPECT_EQ(tensors[0].name, "test_tensor");
    EXPECT_EQ(tensors[0].dataType, TensorDataType::Float32);
    EXPECT_EQ(tensors[0].numElements, 100);
}

TEST_F(ModelLoaderTest, SafeTensorsGetTensorDataLocation) {
    auto filePath = createMockSafeTensorsFile();
    auto location = SafeTensorsLoader::getTensorDataLocation(filePath, "test_tensor");
    
    EXPECT_GT(location.first, 0);
    EXPECT_GT(location.second, location.first);
    EXPECT_EQ(location.second - location.first, 400); // 100 floats * 4 bytes
}

// ============================================================================
// ONNX Loader Tests
// ============================================================================

TEST_F(ModelLoaderTest, ONNXLoaderCanLoad) {
    ONNXLoader loader;
    
    auto onnxFile = createMockONNXFile();
    EXPECT_TRUE(loader.canLoad(onnxFile));
    
    auto ggufFile = createMockGGUFFile();
    EXPECT_FALSE(loader.canLoad(ggufFile));
}

TEST_F(ModelLoaderTest, ONNXLoaderFormat) {
    ONNXLoader loader;
    EXPECT_EQ(loader.getFormat(), ModelFormat::ONNX);
}

TEST_F(ModelLoaderTest, ONNXLoaderValidate) {
    ONNXLoader loader;
    auto filePath = createMockONNXFile();
    
    EXPECT_TRUE(loader.validate(filePath));
}

TEST_F(ModelLoaderTest, ONNXLoadMetadata) {
    ONNXLoader loader;
    auto filePath = createMockONNXFile();
    
    auto metadata = loader.loadMetadata(filePath);
    
    EXPECT_EQ(metadata.format, ModelFormat::ONNX);
    EXPECT_FALSE(metadata.filePath.empty());
}

// ============================================================================
// Model Loader Factory Tests
// ============================================================================

TEST_F(ModelLoaderTest, FactoryRegisterLoader) {
    auto& factory = ModelLoaderFactory::getInstance();
    
    factory.registerLoader(ModelFormat::GGUF, []() {
        return std::make_unique<GGUFLoader>();
    });
    
    auto loader = factory.getLoader(ModelFormat::GGUF);
    EXPECT_NE(loader, nullptr);
    EXPECT_EQ(loader->getFormat(), ModelFormat::GGUF);
}

TEST_F(ModelLoaderTest, FactoryAutoDetect) {
    auto& factory = ModelLoaderFactory::getInstance();
    
    // Register loaders
    factory.registerLoader(ModelFormat::GGUF, []() {
        return std::make_unique<GGUFLoader>();
    });
    factory.registerLoader(ModelFormat::SafeTensors, []() {
        return std::make_unique<SafeTensorsLoader>();
    });
    factory.registerLoader(ModelFormat::ONNX, []() {
        return std::make_unique<ONNXLoader>();
    });
    
    // Test auto-detection
    auto ggufFile = createMockGGUFFile();
    auto format = factory.detectFormat(ggufFile);
    EXPECT_EQ(format, ModelFormat::GGUF);
    
    auto safetensorsFile = createMockSafeTensorsFile();
    format = factory.detectFormat(safetensorsFile);
    EXPECT_EQ(format, ModelFormat::SafeTensors);
    
    auto onnxFile = createMockONNXFile();
    format = factory.detectFormat(onnxFile);
    EXPECT_EQ(format, ModelFormat::ONNX);
}

TEST_F(ModelLoaderTest, FactoryGetLoaderForFile) {
    auto& factory = ModelLoaderFactory::getInstance();
    
    factory.registerLoader(ModelFormat::GGUF, []() {
        return std::make_unique<GGUFLoader>();
    });
    
    auto ggufFile = createMockGGUFFile();
    auto loader = factory.getLoaderForFile(ggufFile);
    
    EXPECT_NE(loader, nullptr);
    EXPECT_EQ(loader->getFormat(), ModelFormat::GGUF);
}

// ============================================================================
// Memory-Mapped File Tests
// ============================================================================

TEST_F(ModelLoaderTest, MemoryMappedFileOpen) {
    auto filePath = createMockGGUFFile();
    
    MemoryMappedFile mmf;
    EXPECT_TRUE(mmf.open(filePath, true));
    EXPECT_TRUE(mmf.isOpen());
    EXPECT_NE(mmf.data(), nullptr);
    EXPECT_GT(mmf.size(), 0);
}

TEST_F(ModelLoaderTest, MemoryMappedFileClose) {
    auto filePath = createMockGGUFFile();
    
    MemoryMappedFile mmf;
    mmf.open(filePath, true);
    mmf.close();
    
    EXPECT_FALSE(mmf.isOpen());
    EXPECT_EQ(mmf.data(), nullptr);
    EXPECT_EQ(mmf.size(), 0);
}

TEST_F(ModelLoaderTest, MemoryMappedFileMove) {
    auto filePath = createMockGGUFFile();
    
    MemoryMappedFile mmf1;
    mmf1.open(filePath, true);
    
    MemoryMappedFile mmf2(std::move(mmf1));
    
    EXPECT_FALSE(mmf1.isOpen());
    EXPECT_TRUE(mmf2.isOpen());
    EXPECT_NE(mmf2.data(), nullptr);
}

TEST_F(ModelLoaderTest, MemoryMappedFileRead) {
    auto filePath = createMockGGUFFile();
    
    MemoryMappedFile mmf;
    mmf.open(filePath, true);
    
    // Read GGUF magic number
    auto magic = mmf.at<uint32_t>(0);
    EXPECT_EQ(*magic, 0x46554747);
}

// ============================================================================
// Data Type Conversion Tests
// ============================================================================

TEST_F(ModelLoaderTest, ONNXDataTypeConversion) {
    EXPECT_EQ(onnxTypeToTensorType(ONNX::DataType::FLOAT), TensorDataType::Float32);
    EXPECT_EQ(onnxTypeToTensorType(ONNX::DataType::FLOAT16), TensorDataType::Float16);
    EXPECT_EQ(onnxTypeToTensorType(ONNX::DataType::INT8), TensorDataType::Int8);
    EXPECT_EQ(onnxTypeToTensorType(ONNX::DataType::BOOL), TensorDataType::Bool);
}

TEST_F(ModelLoaderTest, SafeTensorsDataTypeConversion) {
    EXPECT_EQ(safetensorsTypeToTensorType("F32"), TensorDataType::Float32);
    EXPECT_EQ(safetensorsTypeToTensorType("F16"), TensorDataType::Float16);
    EXPECT_EQ(safetensorsTypeToTensorType("I8"), TensorDataType::Int8);
    EXPECT_EQ(safetensorsTypeToTensorType("BOOL"), TensorDataType::Bool);
}

TEST_F(ModelLoaderTest, GGMLDataTypeConversion) {
    EXPECT_EQ(ggmlTypeToTensorType(GGMLType::F32), TensorDataType::Float32);
    EXPECT_EQ(ggmlTypeToTensorType(GGMLType::F16), TensorDataType::Float16);
    EXPECT_EQ(ggmlTypeToTensorType(GGMLType::I8), TensorDataType::Int8);
}

TEST_F(ModelLoaderTest, GGMLQuantizationConversion) {
    EXPECT_EQ(ggmlTypeToQuantization(GGMLType::F32), QuantizationType::None);
    EXPECT_EQ(ggmlTypeToQuantization(GGMLType::F16), QuantizationType::F16);
    EXPECT_EQ(ggmlTypeToQuantization(GGMLType::Q4_0), QuantizationType::Q4_0);
    EXPECT_EQ(ggmlTypeToQuantization(GGMLType::Q8_0), QuantizationType::Q8_0);
}

// ============================================================================
// Model Metadata Tests
// ============================================================================

TEST_F(ModelLoaderTest, ModelMetadataBasics) {
    ModelMetadata metadata;
    metadata.name = "TestModel";
    metadata.version = "1.0";
    metadata.architecture = ModelArchitecture::LLaMA;
    metadata.format = ModelFormat::GGUF;
    
    EXPECT_EQ(metadata.name, "TestModel");
    EXPECT_EQ(metadata.version, "1.0");
    EXPECT_EQ(metadata.architecture, ModelArchitecture::LLaMA);
}

TEST_F(ModelLoaderTest, ModelMetadataCustomValues) {
    ModelMetadata metadata;
    
    metadata.setMetadata("custom_int", int64_t(42));
    metadata.setMetadata("custom_string", std::string("test"));
    metadata.setMetadata("custom_double", 3.14);
    
    EXPECT_EQ(metadata.getMetadata<int64_t>("custom_int").value(), 42);
    EXPECT_EQ(metadata.getMetadata<std::string>("custom_string").value(), "test");
    EXPECT_DOUBLE_EQ(metadata.getMetadata<double>("custom_double").value(), 3.14);
}

TEST_F(ModelLoaderTest, ModelMetadataSummary) {
    ModelMetadata metadata;
    metadata.name = "TestModel";
    metadata.architecture = ModelArchitecture::LLaMA;
    metadata.format = ModelFormat::GGUF;
    metadata.parameterCount = 7000000000;
    metadata.contextLength = 4096;
    
    auto summary = metadata.getSummary();
    
    EXPECT_TRUE(summary.find("TestModel") != std::string::npos);
    EXPECT_TRUE(summary.find("LLaMA") != std::string::npos);
    EXPECT_TRUE(summary.find("GGUF") != std::string::npos);
}

// ============================================================================
// Error Handling Tests
// ============================================================================

TEST_F(ModelLoaderTest, LoadNonexistentFile) {
    GGUFLoader loader;
    auto fakePath = testDataDir_ / "nonexistent.gguf";
    
    EXPECT_THROW(loader.loadMetadata(fakePath), ModelException);
}

TEST_F(ModelLoaderTest, LoadInvalidFormat) {
    auto filePath = testDataDir_ / "invalid.gguf";
    std::ofstream file(filePath);
    file << "not a valid gguf file";
    file.close();
    
    GGUFLoader loader;
    EXPECT_FALSE(loader.validate(filePath));
}

// ============================================================================
// Performance Benchmarks
// ============================================================================

TEST_F(ModelLoaderTest, BenchmarkFormatDetection) {
    auto filePath = createMockGGUFFile();
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < 1000; ++i) {
        FormatDetector::detectFromExtension(filePath);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    std::cout << "Format detection (1000 iterations): " << duration.count() << " μs" << std::endl;
    EXPECT_LT(duration.count(), 10000); // Should be < 10ms for 1000 iterations
}

TEST_F(ModelLoaderTest, BenchmarkMetadataLoading) {
    SafeTensorsLoader loader;
    auto filePath = createMockSafeTensorsFile();
    
    auto start = std::chrono::high_resolution_clock::now();
    
    for (int i = 0; i < 100; ++i) {
        loader.loadMetadata(filePath);
    }
    
    auto end = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    std::cout << "Metadata loading (100 iterations): " << duration.count() << " ms" << std::endl;
}

// ============================================================================
// Main
// ============================================================================

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
