#pragma once

#include "VersaAIException.hpp"
#include "VersaAIMemoryPool.hpp"
#include <vector>
#include <memory>
#include <cstdint>
#include <algorithm>
#include <numeric>
#include <cstring>
#include <initializer_list>

namespace VersaAI {

/**
 * @brief Data types supported by tensors
 */
enum class TensorDataType {
    FLOAT32,    // 32-bit floating point
    FLOAT16,    // 16-bit floating point
    BFLOAT16,   // BF16
    INT32,      // 32-bit integer
    INT16,      // 16-bit integer
    INT8,       // 8-bit integer
    UINT8,      // 8-bit unsigned integer
    BOOL,       // Boolean
    UNKNOWN
};

/**
 * @brief Tensor device types
 */
enum class TensorDevice {
    CPU,        // CPU memory
    CUDA,       // NVIDIA CUDA
    ROCM,       // AMD ROCm
    METAL,      // Apple Metal
    VULKAN      // Vulkan compute
};

/**
 * @brief Get size in bytes for data type
 */
inline size_t getDataTypeSize(TensorDataType dtype) {
    switch (dtype) {
        case TensorDataType::FLOAT32: return 4;
        case TensorDataType::FLOAT16: return 2;
        case TensorDataType::BFLOAT16: return 2;
        case TensorDataType::INT32: return 4;
        case TensorDataType::INT16: return 2;
        case TensorDataType::INT8: return 1;
        case TensorDataType::UINT8: return 1;
        case TensorDataType::BOOL: return 1;
        default: return 0;
    }
}

/**
 * @brief Production-grade multi-dimensional tensor with memory pool support
 *
 * Features:
 * - Efficient memory management with custom allocators
 * - Broadcasting support for element-wise operations
 * - Strided access for views and slicing
 * - GPU/CPU device management
 * - Zero-copy views where possible
 */
class Tensor {
public:
    /**
     * @brief Construct empty tensor
     */
    Tensor();

    /**
     * @brief Construct tensor with given shape and data type
     */
    Tensor(const std::vector<int64_t>& shape, TensorDataType dtype = TensorDataType::FLOAT32,
           TensorDevice device = TensorDevice::CPU);

    /**
     * @brief Construct tensor from existing data (copies data)
     */
    Tensor(const std::vector<int64_t>& shape, void* data, TensorDataType dtype,
           TensorDevice device = TensorDevice::CPU);

    /**
     * @brief Construct from initializer list (1D)
     */
    template<typename T>
    Tensor(std::initializer_list<T> values, TensorDataType dtype = TensorDataType::FLOAT32);

    ~Tensor();

    // Move semantics
    Tensor(Tensor&& other) noexcept;
    Tensor& operator=(Tensor&& other) noexcept;

    // Copy semantics
    Tensor(const Tensor& other);
    Tensor& operator=(const Tensor& other);

    // ========================================================================
    // Shape & Dimension Info
    // ========================================================================

    const std::vector<int64_t>& shape() const { return shape_; }
    const std::vector<int64_t>& strides() const { return strides_; }
    int64_t ndim() const { return static_cast<int64_t>(shape_.size()); }
    int64_t size() const { return numElements_; }
    int64_t size(int64_t dim) const;

    TensorDataType dtype() const { return dtype_; }
    TensorDevice device() const { return device_; }

    size_t elementSize() const { return getDataTypeSize(dtype_); }
    size_t byteSize() const { return numElements_ * elementSize(); }

    bool isEmpty() const { return numElements_ == 0; }
    bool isContiguous() const { return contiguous_; }

    // ========================================================================
    // Data Access
    // ========================================================================

    /**
     * @brief Get raw data pointer (mutable)
     */
    void* data() { return data_; }

    /**
     * @brief Get raw data pointer (const)
     */
    const void* data() const { return data_; }

    /**
     * @brief Get typed data pointer
     */
    template<typename T>
    T* data() { return static_cast<T*>(data_); }

    template<typename T>
    const T* data() const { return static_cast<const T*>(data_); }

    /**
     * @brief Access element at flat index
     */
    template<typename T>
    T& at(int64_t index);

    template<typename T>
    const T& at(int64_t index) const;

    /**
     * @brief Access element at multi-dimensional index
     */
    template<typename T>
    T& at(const std::vector<int64_t>& indices);

    template<typename T>
    const T& at(const std::vector<int64_t>& indices) const;

    // ========================================================================
    // Reshaping & Views
    // ========================================================================

    /**
     * @brief Reshape tensor (returns view if possible, copy otherwise)
     */
    Tensor reshape(const std::vector<int64_t>& newShape) const;

    /**
     * @brief Flatten to 1D tensor
     */
    Tensor flatten() const;

    /**
     * @brief Transpose tensor
     */
    Tensor transpose(int64_t dim0, int64_t dim1) const;

    /**
     * @brief Squeeze dimensions of size 1
     */
    Tensor squeeze() const;

    /**
     * @brief Add dimension of size 1
     */
    Tensor unsqueeze(int64_t dim) const;

    /**
     * @brief Get slice along dimension
     */
    Tensor slice(int64_t dim, int64_t start, int64_t end) const;

    /**
     * @brief Make tensor contiguous in memory
     */
    Tensor contiguous() const;

    // ========================================================================
    // Element-wise Operations
    // ========================================================================

    Tensor operator+(const Tensor& other) const;
    Tensor operator-(const Tensor& other) const;
    Tensor operator*(const Tensor& other) const;
    Tensor operator/(const Tensor& other) const;

    Tensor& operator+=(const Tensor& other);
    Tensor& operator-=(const Tensor& other);
    Tensor& operator*=(const Tensor& other);
    Tensor& operator/=(const Tensor& other);

    /**
     * @brief Scalar operations
     */
    template<typename T>
    Tensor operator+(T scalar) const;

    template<typename T>
    Tensor operator*(T scalar) const;

    // ========================================================================
    // Matrix Operations
    // ========================================================================

    /**
     * @brief Matrix multiplication
     */
    Tensor matmul(const Tensor& other) const;

    /**
     * @brief Batch matrix multiplication
     */
    Tensor bmm(const Tensor& other) const;

    // ========================================================================
    // Reductions
    // ========================================================================

    /**
     * @brief Sum along dimension
     */
    Tensor sum(int64_t dim = -1, bool keepDim = false) const;

    /**
     * @brief Mean along dimension
     */
    Tensor mean(int64_t dim = -1, bool keepDim = false) const;

    /**
     * @brief Max along dimension
     */
    Tensor max(int64_t dim = -1, bool keepDim = false) const;

    /**
     * @brief Min along dimension
     */
    Tensor min(int64_t dim = -1, bool keepDim = false) const;

    // ========================================================================
    // Activations & Functions
    // ========================================================================

    Tensor relu() const;
    Tensor gelu() const;
    Tensor sigmoid() const;
    Tensor tanh() const;
    Tensor softmax(int64_t dim = -1) const;
    Tensor layerNorm(double eps = 1e-5) const;

    // ========================================================================
    // Device Management
    // ========================================================================

    /**
     * @brief Move tensor to different device
     */
    Tensor to(TensorDevice device) const;

    /**
     * @brief Convert tensor to different data type
     */
    Tensor to(TensorDataType dtype) const;

    /**
     * @brief Check if tensor is on CPU
     */
    bool isCPU() const { return device_ == TensorDevice::CPU; }

    /**
     * @brief Check if tensor is on GPU
     */
    bool isGPU() const { return device_ != TensorDevice::CPU; }

    // ========================================================================
    // Utility
    // ========================================================================

    /**
     * @brief Fill tensor with value
     */
    template<typename T>
    void fill(T value);

    /**
     * @brief Fill tensor with zeros
     */
    void zero();

    /**
     * @brief Copy data from another tensor
     */
    void copyFrom(const Tensor& other);

    /**
     * @brief Clone tensor (deep copy)
     */
    Tensor clone() const;

    /**
     * @brief Print tensor info for debugging
     */
    std::string toString() const;

private:
    void* data_;                        // Raw data pointer
    std::vector<int64_t> shape_;        // Tensor shape
    std::vector<int64_t> strides_;      // Strides for each dimension
    int64_t numElements_;               // Total number of elements
    TensorDataType dtype_;              // Data type
    TensorDevice device_;               // Device location
    bool contiguous_;                   // Whether memory is contiguous
    bool ownsData_;                     // Whether we own the data

    /**
     * @brief Calculate strides from shape
     */
    static std::vector<int64_t> calculateStrides(const std::vector<int64_t>& shape);

    /**
     * @brief Calculate flat index from multi-dimensional indices
     */
    int64_t calculateIndex(const std::vector<int64_t>& indices) const;

    /**
     * @brief Allocate memory for tensor
     */
    void allocate();

    /**
     * @brief Free tensor memory
     */
    void deallocate();

    /**
     * @brief Validate indices are within bounds
     */
    void validateIndices(const std::vector<int64_t>& indices) const;

    /**
     * @brief Check if shapes are broadcast-compatible
     */
    static bool canBroadcast(const std::vector<int64_t>& shape1,
                            const std::vector<int64_t>& shape2);

    /**
     * @brief Get broadcast shape
     */
    static std::vector<int64_t> broadcastShape(const std::vector<int64_t>& shape1,
                                                const std::vector<int64_t>& shape2);
};

// ============================================================================
// Tensor Creation Functions
// ============================================================================

/**
 * @brief Create tensor filled with zeros
 */
Tensor zeros(const std::vector<int64_t>& shape, TensorDataType dtype = TensorDataType::FLOAT32);

/**
 * @brief Create tensor filled with ones
 */
Tensor ones(const std::vector<int64_t>& shape, TensorDataType dtype = TensorDataType::FLOAT32);

/**
 * @brief Create tensor filled with specific value
 */
template<typename T>
Tensor full(const std::vector<int64_t>& shape, T value, TensorDataType dtype = TensorDataType::FLOAT32);

/**
 * @brief Create tensor with random values (uniform distribution)
 */
Tensor rand(const std::vector<int64_t>& shape, TensorDataType dtype = TensorDataType::FLOAT32);

/**
 * @brief Create tensor with random values (normal distribution)
 */
Tensor randn(const std::vector<int64_t>& shape, double mean = 0.0, double std = 1.0,
             TensorDataType dtype = TensorDataType::FLOAT32);

/**
 * @brief Create identity matrix
 */
Tensor eye(int64_t n, TensorDataType dtype = TensorDataType::FLOAT32);

/**
 * @brief Create tensor from vector
 */
template<typename T>
Tensor fromVector(const std::vector<T>& data, TensorDataType dtype = TensorDataType::FLOAT32);

// ============================================================================
// Template Implementations
// ============================================================================

template<typename T>
Tensor::Tensor(std::initializer_list<T> values, TensorDataType dtype)
    : shape_({static_cast<int64_t>(values.size())}),
      dtype_(dtype),
      device_(TensorDevice::CPU),
      contiguous_(true),
      ownsData_(true) {
    
    numElements_ = values.size();
    strides_ = calculateStrides(shape_);
    allocate();
    
    T* ptr = data<T>();
    size_t i = 0;
    for (const auto& val : values) {
        ptr[i++] = val;
    }
}

template<typename T>
T& Tensor::at(int64_t index) {
    if (index < 0 || index >= numElements_) {
        throw TensorException("Index out of bounds: " + std::to_string(index));
    }
    return data<T>()[index];
}

template<typename T>
const T& Tensor::at(int64_t index) const {
    if (index < 0 || index >= numElements_) {
        throw TensorException("Index out of bounds: " + std::to_string(index));
    }
    return data<T>()[index];
}

template<typename T>
T& Tensor::at(const std::vector<int64_t>& indices) {
    validateIndices(indices);
    int64_t flatIndex = calculateIndex(indices);
    return data<T>()[flatIndex];
}

template<typename T>
const T& Tensor::at(const std::vector<int64_t>& indices) const {
    validateIndices(indices);
    int64_t flatIndex = calculateIndex(indices);
    return data<T>()[flatIndex];
}

template<typename T>
void Tensor::fill(T value) {
    if constexpr (std::is_same_v<T, float> && dtype_ == TensorDataType::FLOAT32) {
        float* ptr = data<float>();
        std::fill(ptr, ptr + numElements_, value);
    } else if constexpr (std::is_same_v<T, int32_t> && dtype_ == TensorDataType::INT32) {
        int32_t* ptr = data<int32_t>();
        std::fill(ptr, ptr + numElements_, value);
    } else {
        throw TensorException("Type mismatch in fill operation");
    }
}

template<typename T>
Tensor fromVector(const std::vector<T>& data, TensorDataType dtype) {
    Tensor t({static_cast<int64_t>(data.size())}, dtype);
    std::memcpy(t.data(), data.data(), data.size() * sizeof(T));
    return t;
}

} // namespace VersaAI
