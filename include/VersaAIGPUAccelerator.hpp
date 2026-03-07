#pragma once

#include "VersaAITensor.hpp"
#include "VersaAIException.hpp"
#include <memory>
#include <vector>
#include <string>
#include <cstdint>

namespace VersaAI {

// ============================================================================
// GPU Backend Types
// ============================================================================

/**
 * @brief Supported compute backends
 */
enum class ComputeBackend {
    CPU,        // CPU-only (fallback)
    CUDA,       // NVIDIA CUDA
    ROCM,       // AMD ROCm
    METAL,      // Apple Metal
    VULKAN,     // Vulkan Compute
    SYCL,       // Intel oneAPI
    AUTO        // Auto-detect best backend
};

/**
 * @brief GPU device information
 */
struct GPUDeviceInfo {
    uint32_t deviceId;
    std::string name;
    ComputeBackend backend;
    uint64_t totalMemory;           // Total VRAM in bytes
    uint64_t freeMemory;            // Free VRAM in bytes
    uint32_t computeCapability;     // For CUDA: major*10 + minor
    uint32_t numCores;              // Number of CUDA cores / CUs
    uint32_t clockRateMHz;
    bool supportsFloat16;
    bool supportsBFloat16;
    bool supportsInt8;
    bool supportsTensorCores;       // CUDA tensor cores / AMD matrix cores
};

/**
 * @brief GPU memory allocation info
 */
struct GPUAllocation {
    void* devicePtr;                // Device pointer
    size_t size;                    // Allocation size in bytes
    uint32_t deviceId;
    bool isPinned;                  // Pinned/page-locked memory
};

// ============================================================================
// GPU Accelerator Base
// ============================================================================

/**
 * @brief Abstract base class for GPU acceleration
 *
 * Provides unified interface for CUDA, ROCm, Metal, Vulkan backends
 */
class GPUAccelerator {
public:
    virtual ~GPUAccelerator() = default;

    /**
     * @brief Initialize GPU backend
     */
    virtual void initialize() = 0;

    /**
     * @brief Shutdown and cleanup
     */
    virtual void shutdown() = 0;

    /**
     * @brief Get backend type
     */
    virtual ComputeBackend getBackend() const = 0;

    /**
     * @brief Check if backend is available
     */
    virtual bool isAvailable() const = 0;

    // ========================================================================
    // Device Management
    // ========================================================================

    /**
     * @brief Get number of available devices
     */
    virtual uint32_t getDeviceCount() const = 0;

    /**
     * @brief Get device information
     */
    virtual GPUDeviceInfo getDeviceInfo(uint32_t deviceId) const = 0;

    /**
     * @brief Set active device
     */
    virtual void setDevice(uint32_t deviceId) = 0;

    /**
     * @brief Get current device ID
     */
    virtual uint32_t getCurrentDevice() const = 0;

    // ========================================================================
    // Memory Management
    // ========================================================================

    /**
     * @brief Allocate device memory
     */
    virtual void* allocate(size_t size, uint32_t deviceId) = 0;

    /**
     * @brief Free device memory
     */
    virtual void deallocate(void* ptr) = 0;

    /**
     * @brief Copy host to device
     */
    virtual void copyToDevice(void* dst, const void* src, size_t size) = 0;

    /**
     * @brief Copy device to host
     */
    virtual void copyToHost(void* dst, const void* src, size_t size) = 0;

    /**
     * @brief Copy device to device
     */
    virtual void copyDeviceToDevice(void* dst, const void* src, size_t size) = 0;

    /**
     * @brief Allocate pinned host memory for faster transfers
     */
    virtual void* allocatePinned(size_t size) = 0;

    /**
     * @brief Free pinned memory
     */
    virtual void deallocatePinned(void* ptr) = 0;

    // ========================================================================
    // Synchronization
    // ========================================================================

    /**
     * @brief Wait for all operations to complete
     */
    virtual void synchronize() = 0;

    /**
     * @brief Create event for timing
     */
    virtual void* createEvent() = 0;

    /**
     * @brief Destroy event
     */
    virtual void destroyEvent(void* event) = 0;

    /**
     * @brief Record event
     */
    virtual void recordEvent(void* event) = 0;

    /**
     * @brief Get elapsed time between events (ms)
     */
    virtual float getElapsedTime(void* start, void* end) = 0;

    // ========================================================================
    // Tensor Operations (GPU-accelerated)
    // ========================================================================

    /**
     * @brief Matrix multiplication (GEMM): C = alpha * A @ B + beta * C
     */
    virtual void matmul(const Tensor& A, const Tensor& B, Tensor& C,
                       float alpha = 1.0f, float beta = 0.0f) = 0;

    /**
     * @brief Batch matrix multiplication
     */
    virtual void batchMatmul(const Tensor& A, const Tensor& B, Tensor& C,
                            uint32_t batchSize) = 0;

    /**
     * @brief Element-wise addition
     */
    virtual void add(const Tensor& A, const Tensor& B, Tensor& C) = 0;

    /**
     * @brief Element-wise multiplication
     */
    virtual void multiply(const Tensor& A, const Tensor& B, Tensor& C) = 0;

    /**
     * @brief Softmax activation
     */
    virtual void softmax(const Tensor& input, Tensor& output, int32_t dim) = 0;

    /**
     * @brief Layer normalization
     */
    virtual void layerNorm(const Tensor& input, Tensor& output,
                          const Tensor& weight, const Tensor& bias, float eps) = 0;

    /**
     * @brief GELU activation
     */
    virtual void gelu(const Tensor& input, Tensor& output) = 0;

    /**
     * @brief ReLU activation
     */
    virtual void relu(const Tensor& input, Tensor& output) = 0;

    /**
     * @brief Embedding lookup
     */
    virtual void embedding(const Tensor& indices, const Tensor& weights, Tensor& output) = 0;

    /**
     * @brief Attention (scaled dot-product)
     */
    virtual void attention(const Tensor& Q, const Tensor& K, const Tensor& V,
                          Tensor& output, const Tensor* mask = nullptr) = 0;

    // ========================================================================
    // Quantization Support
    // ========================================================================

    /**
     * @brief Quantize FP32 to INT8
     */
    virtual void quantizeInt8(const Tensor& input, Tensor& output,
                             float& scale, int8_t& zeroPoint) = 0;

    /**
     * @brief Dequantize INT8 to FP32
     */
    virtual void dequantizeInt8(const Tensor& input, Tensor& output,
                               float scale, int8_t zeroPoint) = 0;

    // ========================================================================
    // Factory
    // ========================================================================

    /**
     * @brief Create GPU accelerator for specified backend
     */
    static std::unique_ptr<GPUAccelerator> create(ComputeBackend backend = ComputeBackend::AUTO);

    /**
     * @brief Auto-detect best available backend
     */
    static ComputeBackend detectBackend();
};

// ============================================================================
// CUDA Accelerator
// ============================================================================

#ifdef VERSAAI_CUDA_SUPPORT

/**
 * @brief NVIDIA CUDA acceleration implementation
 */
class CUDAAccelerator : public GPUAccelerator {
public:
    CUDAAccelerator();
    ~CUDAAccelerator() override;

    void initialize() override;
    void shutdown() override;
    ComputeBackend getBackend() const override { return ComputeBackend::CUDA; }
    bool isAvailable() const override;

    uint32_t getDeviceCount() const override;
    GPUDeviceInfo getDeviceInfo(uint32_t deviceId) const override;
    void setDevice(uint32_t deviceId) override;
    uint32_t getCurrentDevice() const override;

    void* allocate(size_t size, uint32_t deviceId) override;
    void deallocate(void* ptr) override;
    void copyToDevice(void* dst, const void* src, size_t size) override;
    void copyToHost(void* dst, const void* src, size_t size) override;
    void copyDeviceToDevice(void* dst, const void* src, size_t size) override;
    void* allocatePinned(size_t size) override;
    void deallocatePinned(void* ptr) override;

    void synchronize() override;
    void* createEvent() override;
    void destroyEvent(void* event) override;
    void recordEvent(void* event) override;
    float getElapsedTime(void* start, void* end) override;

    void matmul(const Tensor& A, const Tensor& B, Tensor& C,
               float alpha, float beta) override;
    void batchMatmul(const Tensor& A, const Tensor& B, Tensor& C,
                    uint32_t batchSize) override;
    void add(const Tensor& A, const Tensor& B, Tensor& C) override;
    void multiply(const Tensor& A, const Tensor& B, Tensor& C) override;
    void softmax(const Tensor& input, Tensor& output, int32_t dim) override;
    void layerNorm(const Tensor& input, Tensor& output,
                  const Tensor& weight, const Tensor& bias, float eps) override;
    void gelu(const Tensor& input, Tensor& output) override;
    void relu(const Tensor& input, Tensor& output) override;
    void embedding(const Tensor& indices, const Tensor& weights, Tensor& output) override;
    void attention(const Tensor& Q, const Tensor& K, const Tensor& V,
                  Tensor& output, const Tensor* mask) override;

    void quantizeInt8(const Tensor& input, Tensor& output,
                     float& scale, int8_t& zeroPoint) override;
    void dequantizeInt8(const Tensor& input, Tensor& output,
                       float scale, int8_t zeroPoint) override;

private:
    bool initialized_;
    uint32_t deviceCount_;
    uint32_t currentDevice_;
    
    void* cublasHandle_;    // cuBLAS handle
    void* cudnnHandle_;     // cuDNN handle (for convolutions, pooling, etc.)

    void checkCUDAError(int error, const char* file, int line);
};

#define CUDA_CHECK(err) checkCUDAError(err, __FILE__, __LINE__)

#endif // VERSAAI_CUDA_SUPPORT

// ============================================================================
// ROCm Accelerator
// ============================================================================

#ifdef VERSAAI_ROCM_SUPPORT

/**
 * @brief AMD ROCm acceleration implementation
 */
class ROCmAccelerator : public GPUAccelerator {
public:
    ROCmAccelerator();
    ~ROCmAccelerator() override;

    void initialize() override;
    void shutdown() override;
    ComputeBackend getBackend() const override { return ComputeBackend::ROCM; }
    bool isAvailable() const override;

    // Similar interface to CUDA...
    // Implementation uses HIP, rocBLAS, MIOpen

private:
    bool initialized_;
    void* rocblasHandle_;
    void* miopenHandle_;
};

#endif // VERSAAI_ROCM_SUPPORT

// ============================================================================
// CPU Fallback
// ============================================================================

/**
 * @brief CPU-based implementation (fallback when no GPU available)
 *
 * Uses optimized CPU libraries (Eigen, OpenBLAS, etc.)
 */
class CPUAccelerator : public GPUAccelerator {
public:
    CPUAccelerator();
    ~CPUAccelerator() override;

    void initialize() override;
    void shutdown() override;
    ComputeBackend getBackend() const override { return ComputeBackend::CPU; }
    bool isAvailable() const override { return true; }

    uint32_t getDeviceCount() const override { return 1; }
    GPUDeviceInfo getDeviceInfo(uint32_t deviceId) const override;
    void setDevice(uint32_t deviceId) override {}
    uint32_t getCurrentDevice() const override { return 0; }

    void* allocate(size_t size, uint32_t deviceId) override;
    void deallocate(void* ptr) override;
    void copyToDevice(void* dst, const void* src, size_t size) override;
    void copyToHost(void* dst, const void* src, size_t size) override;
    void copyDeviceToDevice(void* dst, const void* src, size_t size) override;
    void* allocatePinned(size_t size) override;
    void deallocatePinned(void* ptr) override;

    void synchronize() override {}
    void* createEvent() override;
    void destroyEvent(void* event) override;
    void recordEvent(void* event) override;
    float getElapsedTime(void* start, void* end) override;

    void matmul(const Tensor& A, const Tensor& B, Tensor& C,
               float alpha, float beta) override;
    void batchMatmul(const Tensor& A, const Tensor& B, Tensor& C,
                    uint32_t batchSize) override;
    void add(const Tensor& A, const Tensor& B, Tensor& C) override;
    void multiply(const Tensor& A, const Tensor& B, Tensor& C) override;
    void softmax(const Tensor& input, Tensor& output, int32_t dim) override;
    void layerNorm(const Tensor& input, Tensor& output,
                  const Tensor& weight, const Tensor& bias, float eps) override;
    void gelu(const Tensor& input, Tensor& output) override;
    void relu(const Tensor& input, Tensor& output) override;
    void embedding(const Tensor& indices, const Tensor& weights, Tensor& output) override;
    void attention(const Tensor& Q, const Tensor& K, const Tensor& V,
                  Tensor& output, const Tensor* mask) override;

    void quantizeInt8(const Tensor& input, Tensor& output,
                     float& scale, int8_t& zeroPoint) override;
    void dequantizeInt8(const Tensor& input, Tensor& output,
                       float scale, int8_t zeroPoint) override;

private:
    bool initialized_;
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * @brief Get human-readable backend name
 */
std::string getBackendName(ComputeBackend backend);

/**
 * @brief Format memory size (bytes to GB/MB/KB)
 */
std::string formatMemorySize(uint64_t bytes);

/**
 * @brief Check if tensor is on GPU
 */
bool isGPUTensor(const Tensor& tensor);

/**
 * @brief Move tensor to GPU
 */
Tensor toGPU(const Tensor& tensor, ComputeBackend backend, uint32_t deviceId = 0);

/**
 * @brief Move tensor to CPU
 */
Tensor toCPU(const Tensor& tensor);

} // namespace VersaAI
