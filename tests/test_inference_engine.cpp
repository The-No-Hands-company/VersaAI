#include "VersaAIInferenceEngine.hpp"
#include "VersaAITensor.hpp"
#include "VersaAITokenizer.hpp"
#include "VersaAIGPUAccelerator.hpp"
#include "VersaAILogger.hpp"
#include <gtest/gtest.h>
#include <memory>
#include <vector>
#include <chrono>

using namespace VersaAI;

// ============================================================================
// Tensor Tests
// ============================================================================

TEST(TensorTest, Construction) {
    Tensor t({2, 3}, TensorDataType::FLOAT32);
    
    EXPECT_EQ(t.ndim(), 2);
    EXPECT_EQ(t.size(), 6);
    EXPECT_EQ(t.shape()[0], 2);
    EXPECT_EQ(t.shape()[1], 3);
    EXPECT_TRUE(t.isContiguous());
    EXPECT_TRUE(t.isCPU());
}

TEST(TensorTest, InitializerList) {
    Tensor t = {1.0f, 2.0f, 3.0f, 4.0f};
    
    EXPECT_EQ(t.size(), 4);
    EXPECT_FLOAT_EQ(t.at<float>(0), 1.0f);
    EXPECT_FLOAT_EQ(t.at<float>(1), 2.0f);
    EXPECT_FLOAT_EQ(t.at<float>(2), 3.0f);
    EXPECT_FLOAT_EQ(t.at<float>(3), 4.0f);
}

TEST(TensorTest, Fill) {
    Tensor t({3, 3}, TensorDataType::FLOAT32);
    t.fill(5.0f);
    
    for (int i = 0; i < t.size(); ++i) {
        EXPECT_FLOAT_EQ(t.at<float>(i), 5.0f);
    }
}

TEST(TensorTest, Zeros) {
    Tensor t = zeros({2, 4});
    
    EXPECT_EQ(t.size(), 8);
    for (int i = 0; i < t.size(); ++i) {
        EXPECT_FLOAT_EQ(t.at<float>(i), 0.0f);
    }
}

TEST(TensorTest, Ones) {
    Tensor t = ones({3, 2});
    
    EXPECT_EQ(t.size(), 6);
    for (int i = 0; i < t.size(); ++i) {
        EXPECT_FLOAT_EQ(t.at<float>(i), 1.0f);
    }
}

TEST(TensorTest, Eye) {
    Tensor t = eye(3);
    
    EXPECT_EQ(t.shape()[0], 3);
    EXPECT_EQ(t.shape()[1], 3);
    
    // Check diagonal
    EXPECT_FLOAT_EQ(t.at<float>({0, 0}), 1.0f);
    EXPECT_FLOAT_EQ(t.at<float>({1, 1}), 1.0f);
    EXPECT_FLOAT_EQ(t.at<float>({2, 2}), 1.0f);
    
    // Check off-diagonal
    EXPECT_FLOAT_EQ(t.at<float>({0, 1}), 0.0f);
    EXPECT_FLOAT_EQ(t.at<float>({1, 0}), 0.0f);
}

TEST(TensorTest, Reshape) {
    Tensor t({2, 3}, TensorDataType::FLOAT32);
    t.fill(1.0f);
    
    Tensor reshaped = t.reshape({3, 2});
    
    EXPECT_EQ(reshaped.shape()[0], 3);
    EXPECT_EQ(reshaped.shape()[1], 2);
    EXPECT_EQ(reshaped.size(), 6);
}

TEST(TensorTest, Flatten) {
    Tensor t({2, 3, 4}, TensorDataType::FLOAT32);
    Tensor flat = t.flatten();
    
    EXPECT_EQ(flat.ndim(), 1);
    EXPECT_EQ(flat.size(), 24);
}

TEST(TensorTest, Transpose) {
    Tensor t({2, 3}, TensorDataType::FLOAT32);
    
    // Fill with pattern
    for (int i = 0; i < 2; ++i) {
        for (int j = 0; j < 3; ++j) {
            t.at<float>({i, j}) = i * 3 + j;
        }
    }
    
    Tensor transposed = t.transpose(0, 1);
    
    EXPECT_EQ(transposed.shape()[0], 3);
    EXPECT_EQ(transposed.shape()[1], 2);
    EXPECT_FLOAT_EQ(transposed.at<float>({0, 0}), 0.0f);
    EXPECT_FLOAT_EQ(transposed.at<float>({1, 0}), 1.0f);
}

TEST(TensorTest, Addition) {
    Tensor a = {1.0f, 2.0f, 3.0f};
    Tensor b = {4.0f, 5.0f, 6.0f};
    
    Tensor c = a + b;
    
    EXPECT_FLOAT_EQ(c.at<float>(0), 5.0f);
    EXPECT_FLOAT_EQ(c.at<float>(1), 7.0f);
    EXPECT_FLOAT_EQ(c.at<float>(2), 9.0f);
}

TEST(TensorTest, Multiplication) {
    Tensor a = {2.0f, 3.0f, 4.0f};
    Tensor b = {5.0f, 6.0f, 7.0f};
    
    Tensor c = a * b;
    
    EXPECT_FLOAT_EQ(c.at<float>(0), 10.0f);
    EXPECT_FLOAT_EQ(c.at<float>(1), 18.0f);
    EXPECT_FLOAT_EQ(c.at<float>(2), 28.0f);
}

TEST(TensorTest, MatrixMultiplication) {
    Tensor A({2, 3}, TensorDataType::FLOAT32);
    Tensor B({3, 2}, TensorDataType::FLOAT32);
    
    // A = [[1, 2, 3], [4, 5, 6]]
    float dataA[] = {1, 2, 3, 4, 5, 6};
    std::memcpy(A.data(), dataA, 6 * sizeof(float));
    
    // B = [[1, 2], [3, 4], [5, 6]]
    float dataB[] = {1, 2, 3, 4, 5, 6};
    std::memcpy(B.data(), dataB, 6 * sizeof(float));
    
    Tensor C = A.matmul(B);
    
    EXPECT_EQ(C.shape()[0], 2);
    EXPECT_EQ(C.shape()[1], 2);
    
    // Result should be [[22, 28], [49, 64]]
    EXPECT_FLOAT_EQ(C.at<float>({0, 0}), 22.0f);
    EXPECT_FLOAT_EQ(C.at<float>({0, 1}), 28.0f);
    EXPECT_FLOAT_EQ(C.at<float>({1, 0}), 49.0f);
    EXPECT_FLOAT_EQ(C.at<float>({1, 1}), 64.0f);
}

TEST(TensorTest, ReLU) {
    Tensor t = {-1.0f, 0.0f, 1.0f, 2.0f, -3.0f};
    Tensor result = t.relu();
    
    EXPECT_FLOAT_EQ(result.at<float>(0), 0.0f);
    EXPECT_FLOAT_EQ(result.at<float>(1), 0.0f);
    EXPECT_FLOAT_EQ(result.at<float>(2), 1.0f);
    EXPECT_FLOAT_EQ(result.at<float>(3), 2.0f);
    EXPECT_FLOAT_EQ(result.at<float>(4), 0.0f);
}

TEST(TensorTest, Sigmoid) {
    Tensor t = {0.0f};
    Tensor result = t.sigmoid();
    
    EXPECT_NEAR(result.at<float>(0), 0.5f, 1e-5);
}

TEST(TensorTest, Softmax) {
    Tensor t({1, 3}, TensorDataType::FLOAT32);
    t.at<float>({0, 0}) = 1.0f;
    t.at<float>({0, 1}) = 2.0f;
    t.at<float>({0, 2}) = 3.0f;
    
    Tensor result = t.softmax();
    
    // Sum should be 1.0
    float sum = result.at<float>({0, 0}) + result.at<float>({0, 1}) + result.at<float>({0, 2});
    EXPECT_NEAR(sum, 1.0f, 1e-5);
    
    // Values should be in ascending order
    EXPECT_LT(result.at<float>({0, 0}), result.at<float>({0, 1}));
    EXPECT_LT(result.at<float>({0, 1}), result.at<float>({0, 2}));
}

TEST(TensorTest, Clone) {
    Tensor original = {1.0f, 2.0f, 3.0f};
    Tensor cloned = original.clone();
    
    EXPECT_EQ(cloned.size(), original.size());
    
    // Modify original
    original.at<float>(0) = 999.0f;
    
    // Clone should be unchanged
    EXPECT_FLOAT_EQ(cloned.at<float>(0), 1.0f);
}

// ============================================================================
// KV-Cache Tests
// ============================================================================

TEST(KVCacheTest, Construction) {
    KVCache cache(12, 2048, 8, 64);
    
    EXPECT_EQ(cache.getSequenceLength(), 0);
    EXPECT_FALSE(cache.isFull());
}

TEST(KVCacheTest, StoreAndRetrieve) {
    KVCache cache(2, 10, 4, 8);
    
    Tensor key({1, 4, 8}, TensorDataType::FLOAT32);
    Tensor value({1, 4, 8}, TensorDataType::FLOAT32);
    
    key.fill(1.0f);
    value.fill(2.0f);
    
    cache.store(0, key, value, 0);
    
    Tensor retrievedKey = cache.getKeys(0, 0, 1);
    Tensor retrievedValue = cache.getValues(0, 0, 1);
    
    EXPECT_EQ(retrievedKey.size(), key.size());
    EXPECT_EQ(retrievedValue.size(), value.size());
}

TEST(KVCacheTest, Clear) {
    KVCache cache(2, 10, 4, 8);
    
    Tensor key({1, 4, 8}, TensorDataType::FLOAT32);
    Tensor value({1, 4, 8}, TensorDataType::FLOAT32);
    
    cache.store(0, key, value, 0);
    cache.clear();
    
    EXPECT_EQ(cache.getSequenceLength(), 0);
}

// ============================================================================
// GPU Accelerator Tests
// ============================================================================

TEST(GPUAcceleratorTest, Detection) {
    ComputeBackend backend = GPUAccelerator::detectBackend();
    EXPECT_NE(backend, ComputeBackend::AUTO);
    
    Logger::info("Detected backend: " + getBackendName(backend));
}

TEST(GPUAcceleratorTest, CPUFallback) {
    auto accelerator = GPUAccelerator::create(ComputeBackend::CPU);
    
    ASSERT_NE(accelerator, nullptr);
    EXPECT_TRUE(accelerator->isAvailable());
    EXPECT_EQ(accelerator->getBackend(), ComputeBackend::CPU);
}

TEST(GPUAcceleratorTest, DeviceInfo) {
    auto accelerator = GPUAccelerator::create();
    
    if (accelerator->isAvailable()) {
        uint32_t deviceCount = accelerator->getDeviceCount();
        EXPECT_GT(deviceCount, 0);
        
        for (uint32_t i = 0; i < deviceCount; ++i) {
            GPUDeviceInfo info = accelerator->getDeviceInfo(i);
            Logger::info("Device " + std::to_string(i) + ": " + info.name);
            Logger::info("  Total Memory: " + formatMemorySize(info.totalMemory));
        }
    }
}

// ============================================================================
// Performance Benchmarks
// ============================================================================

TEST(BenchmarkTest, MatrixMultiplication) {
    const int64_t N = 512;
    
    Tensor A({N, N}, TensorDataType::FLOAT32);
    Tensor B({N, N}, TensorDataType::FLOAT32);
    
    A.fill(1.0f);
    B.fill(2.0f);
    
    auto start = std::chrono::high_resolution_clock::now();
    Tensor C = A.matmul(B);
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start);
    
    Logger::info("Matrix multiplication (" + std::to_string(N) + "x" + std::to_string(N) + "): " +
                std::to_string(duration.count()) + " ms");
    
    EXPECT_EQ(C.shape()[0], N);
    EXPECT_EQ(C.shape()[1], N);
}

TEST(BenchmarkTest, TensorOperations) {
    const int64_t N = 1000000;
    
    Tensor a = rand({N});
    Tensor b = rand({N});
    
    auto start = std::chrono::high_resolution_clock::now();
    Tensor c = a + b;
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    Logger::info("Element-wise addition (" + std::to_string(N) + " elements): " +
                std::to_string(duration.count()) + " μs");
    
    EXPECT_EQ(c.size(), N);
}

TEST(BenchmarkTest, Softmax) {
    const int64_t batchSize = 32;
    const int64_t seqLen = 512;
    
    Tensor logits({batchSize, seqLen}, TensorDataType::FLOAT32);
    logits = randn({batchSize, seqLen});
    
    auto start = std::chrono::high_resolution_clock::now();
    Tensor probs = logits.softmax();
    auto end = std::chrono::high_resolution_clock::now();
    
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(end - start);
    
    Logger::info("Softmax (batch=" + std::to_string(batchSize) + ", seq=" + std::to_string(seqLen) + "): " +
                std::to_string(duration.count()) + " μs");
}

// ============================================================================
// Integration Tests
// ============================================================================

TEST(IntegrationTest, EndToEndTensorFlow) {
    // Simulate a simple feed-forward layer
    const int64_t batchSize = 4;
    const int64_t inputDim = 128;
    const int64_t hiddenDim = 512;
    
    // Input
    Tensor input = randn({batchSize, inputDim});
    
    // Weights
    Tensor W1 = randn({inputDim, hiddenDim}, 0.0, 0.1);
    Tensor b1 = zeros({hiddenDim});
    
    // Forward pass: y = ReLU(x @ W1 + b1)
    Tensor hidden = input.matmul(W1);
    
    // Add bias (broadcasting)
    for (int64_t i = 0; i < batchSize; ++i) {
        for (int64_t j = 0; j < hiddenDim; ++j) {
            hidden.at<float>({i, j}) += b1.at<float>(j);
        }
    }
    
    Tensor output = hidden.relu();
    
    EXPECT_EQ(output.shape()[0], batchSize);
    EXPECT_EQ(output.shape()[1], hiddenDim);
    
    // Check ReLU property: all values >= 0
    for (int64_t i = 0; i < output.size(); ++i) {
        EXPECT_GE(output.at<float>(i), 0.0f);
    }
}

int main(int argc, char** argv) {
    ::testing::InitGoogleTest(&argc, argv);
    
    // Initialize logger
    Logger::setLogLevel(Logger::LogLevel::INFO);
    Logger::info("Starting Inference Engine Tests");
    
    return RUN_ALL_TESTS();
}
