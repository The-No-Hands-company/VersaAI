#include "VersaAITensor.hpp"
#include "VersaAILogger.hpp"
#include <cmath>
#include <random>
#include <sstream>
#include <iomanip>

namespace VersaAI {

// ============================================================================
// Constructors & Destructor
// ============================================================================

Tensor::Tensor()
    : data_(nullptr),
      numElements_(0),
      dtype_(TensorDataType::FLOAT32),
      device_(TensorDevice::CPU),
      contiguous_(true),
      ownsData_(false) {
}

Tensor::Tensor(const std::vector<int64_t>& shape, TensorDataType dtype, TensorDevice device)
    : shape_(shape),
      dtype_(dtype),
      device_(device),
      contiguous_(true),
      ownsData_(true) {
    
    numElements_ = std::accumulate(shape.begin(), shape.end(), 1LL, std::multiplies<int64_t>());
    strides_ = calculateStrides(shape);
    allocate();
}

Tensor::Tensor(const std::vector<int64_t>& shape, void* data, TensorDataType dtype, TensorDevice device)
    : shape_(shape),
      dtype_(dtype),
      device_(device),
      contiguous_(true),
      ownsData_(true) {
    
    numElements_ = std::accumulate(shape.begin(), shape.end(), 1LL, std::multiplies<int64_t>());
    strides_ = calculateStrides(shape);
    allocate();
    std::memcpy(data_, data, byteSize());
}

Tensor::~Tensor() {
    deallocate();
}

Tensor::Tensor(Tensor&& other) noexcept
    : data_(other.data_),
      shape_(std::move(other.shape_)),
      strides_(std::move(other.strides_)),
      numElements_(other.numElements_),
      dtype_(other.dtype_),
      device_(other.device_),
      contiguous_(other.contiguous_),
      ownsData_(other.ownsData_) {
    
    other.data_ = nullptr;
    other.ownsData_ = false;
}

Tensor& Tensor::operator=(Tensor&& other) noexcept {
    if (this != &other) {
        deallocate();
        
        data_ = other.data_;
        shape_ = std::move(other.shape_);
        strides_ = std::move(other.strides_);
        numElements_ = other.numElements_;
        dtype_ = other.dtype_;
        device_ = other.device_;
        contiguous_ = other.contiguous_;
        ownsData_ = other.ownsData_;
        
        other.data_ = nullptr;
        other.ownsData_ = false;
    }
    return *this;
}

Tensor::Tensor(const Tensor& other)
    : shape_(other.shape_),
      strides_(other.strides_),
      numElements_(other.numElements_),
      dtype_(other.dtype_),
      device_(other.device_),
      contiguous_(other.contiguous_),
      ownsData_(true) {
    
    allocate();
    std::memcpy(data_, other.data_, byteSize());
}

Tensor& Tensor::operator=(const Tensor& other) {
    if (this != &other) {
        deallocate();
        
        shape_ = other.shape_;
        strides_ = other.strides_;
        numElements_ = other.numElements_;
        dtype_ = other.dtype_;
        device_ = other.device_;
        contiguous_ = other.contiguous_;
        ownsData_ = true;
        
        allocate();
        std::memcpy(data_, other.data_, byteSize());
    }
    return *this;
}

// ============================================================================
// Shape & Dimension Info
// ============================================================================

int64_t Tensor::size(int64_t dim) const {
    if (dim < 0) {
        dim += ndim();
    }
    if (dim < 0 || dim >= ndim()) {
        throw TensorException("Dimension out of range");
    }
    return shape_[dim];
}

// ============================================================================
// Reshaping & Views
// ============================================================================

Tensor Tensor::reshape(const std::vector<int64_t>& newShape) const {
    int64_t newSize = std::accumulate(newShape.begin(), newShape.end(), 1LL, std::multiplies<int64_t>());
    
    if (newSize != numElements_) {
        throw TensorException("Cannot reshape: element count mismatch");
    }
    
    Tensor result;
    result.shape_ = newShape;
    result.strides_ = calculateStrides(newShape);
    result.numElements_ = numElements_;
    result.dtype_ = dtype_;
    result.device_ = device_;
    result.contiguous_ = contiguous_;
    
    if (contiguous_) {
        // Create view (share data)
        result.data_ = data_;
        result.ownsData_ = false;
    } else {
        // Need to copy to make contiguous
        result.ownsData_ = true;
        result.allocate();
        std::memcpy(result.data_, data_, byteSize());
        result.contiguous_ = true;
    }
    
    return result;
}

Tensor Tensor::flatten() const {
    return reshape({numElements_});
}

Tensor Tensor::transpose(int64_t dim0, int64_t dim1) const {
    if (dim0 < 0) dim0 += ndim();
    if (dim1 < 0) dim1 += ndim();
    
    if (dim0 < 0 || dim0 >= ndim() || dim1 < 0 || dim1 >= ndim()) {
        throw TensorException("Transpose dimensions out of range");
    }
    
    Tensor result = *this;
    std::swap(result.shape_[dim0], result.shape_[dim1]);
    std::swap(result.strides_[dim0], result.strides_[dim1]);
    result.contiguous_ = (dim0 == ndim() - 1 && dim1 == ndim() - 2) || (dim0 == ndim() - 2 && dim1 == ndim() - 1);
    result.ownsData_ = false;
    
    return result;
}

Tensor Tensor::squeeze() const {
    std::vector<int64_t> newShape;
    for (int64_t dim : shape_) {
        if (dim != 1) {
            newShape.push_back(dim);
        }
    }
    if (newShape.empty()) {
        newShape.push_back(1);
    }
    return reshape(newShape);
}

Tensor Tensor::unsqueeze(int64_t dim) const {
    if (dim < 0) dim += ndim() + 1;
    if (dim < 0 || dim > ndim()) {
        throw TensorException("Unsqueeze dimension out of range");
    }
    
    std::vector<int64_t> newShape = shape_;
    newShape.insert(newShape.begin() + dim, 1);
    return reshape(newShape);
}

Tensor Tensor::contiguous() const {
    if (contiguous_) {
        return *this;
    }
    
    Tensor result(shape_, dtype_, device_);
    result.copyFrom(*this);
    return result;
}

// ============================================================================
// Element-wise Operations
// ============================================================================

Tensor Tensor::operator+(const Tensor& other) const {
    if (!canBroadcast(shape_, other.shape_)) {
        throw TensorException("Shapes are not broadcast-compatible");
    }
    
    auto resultShape = broadcastShape(shape_, other.shape_);
    Tensor result(resultShape, dtype_, device_);
    
    if (dtype_ == TensorDataType::FLOAT32) {
        const float* a = data<float>();
        const float* b = other.data<float>();
        float* c = result.data<float>();
        
        for (int64_t i = 0; i < result.size(); ++i) {
            c[i] = a[i % numElements_] + b[i % other.numElements_];
        }
    }
    
    return result;
}

Tensor Tensor::operator-(const Tensor& other) const {
    if (!canBroadcast(shape_, other.shape_)) {
        throw TensorException("Shapes are not broadcast-compatible");
    }
    
    auto resultShape = broadcastShape(shape_, other.shape_);
    Tensor result(resultShape, dtype_, device_);
    
    if (dtype_ == TensorDataType::FLOAT32) {
        const float* a = data<float>();
        const float* b = other.data<float>();
        float* c = result.data<float>();
        
        for (int64_t i = 0; i < result.size(); ++i) {
            c[i] = a[i % numElements_] - b[i % other.numElements_];
        }
    }
    
    return result;
}

Tensor Tensor::operator*(const Tensor& other) const {
    if (!canBroadcast(shape_, other.shape_)) {
        throw TensorException("Shapes are not broadcast-compatible");
    }
    
    auto resultShape = broadcastShape(shape_, other.shape_);
    Tensor result(resultShape, dtype_, device_);
    
    if (dtype_ == TensorDataType::FLOAT32) {
        const float* a = data<float>();
        const float* b = other.data<float>();
        float* c = result.data<float>();
        
        for (int64_t i = 0; i < result.size(); ++i) {
            c[i] = a[i % numElements_] * b[i % other.numElements_];
        }
    }
    
    return result;
}

Tensor Tensor::operator/(const Tensor& other) const {
    if (!canBroadcast(shape_, other.shape_)) {
        throw TensorException("Shapes are not broadcast-compatible");
    }
    
    auto resultShape = broadcastShape(shape_, other.shape_);
    Tensor result(resultShape, dtype_, device_);
    
    if (dtype_ == TensorDataType::FLOAT32) {
        const float* a = data<float>();
        const float* b = other.data<float>();
        float* c = result.data<float>();
        
        for (int64_t i = 0; i < result.size(); ++i) {
            c[i] = a[i % numElements_] / b[i % other.numElements_];
        }
    }
    
    return result;
}

Tensor& Tensor::operator+=(const Tensor& other) {
    *this = *this + other;
    return *this;
}

Tensor& Tensor::operator-=(const Tensor& other) {
    *this = *this - other;
    return *this;
}

Tensor& Tensor::operator*=(const Tensor& other) {
    *this = *this * other;
    return *this;
}

Tensor& Tensor::operator/=(const Tensor& other) {
    *this = *this / other;
    return *this;
}

// ============================================================================
// Matrix Operations
// ============================================================================

Tensor Tensor::matmul(const Tensor& other) const {
    if (ndim() < 2 || other.ndim() < 2) {
        throw TensorException("matmul requires at least 2D tensors");
    }
    
    int64_t m = shape_[ndim() - 2];
    int64_t k = shape_[ndim() - 1];
    int64_t n = other.shape_[other.ndim() - 1];
    
    if (k != other.shape_[other.ndim() - 2]) {
        throw TensorException("matmul dimension mismatch");
    }
    
    std::vector<int64_t> resultShape = shape_;
    resultShape[ndim() - 2] = m;
    resultShape[ndim() - 1] = n;
    
    Tensor result(resultShape, dtype_, device_);
    
    if (dtype_ == TensorDataType::FLOAT32) {
        const float* a = data<float>();
        const float* b = other.data<float>();
        float* c = result.data<float>();
        
        // Simple matrix multiplication (BLAS would be better for production)
        for (int64_t i = 0; i < m; ++i) {
            for (int64_t j = 0; j < n; ++j) {
                float sum = 0.0f;
                for (int64_t l = 0; l < k; ++l) {
                    sum += a[i * k + l] * b[l * n + j];
                }
                c[i * n + j] = sum;
            }
        }
    }
    
    return result;
}

// ============================================================================
// Reductions
// ============================================================================

Tensor Tensor::sum(int64_t dim, bool keepDim) const {
    if (dim == -1) {
        // Sum all elements
        Tensor result({1}, dtype_, device_);
        
        if (dtype_ == TensorDataType::FLOAT32) {
            const float* ptr = data<float>();
            float total = 0.0f;
            for (int64_t i = 0; i < numElements_; ++i) {
                total += ptr[i];
            }
            result.data<float>()[0] = total;
        }
        
        return keepDim ? result : result.squeeze();
    }
    
    throw TensorException("Dimension-specific reduction not yet implemented");
}

Tensor Tensor::mean(int64_t dim, bool keepDim) const {
    Tensor s = sum(dim, keepDim);
    
    if (dtype_ == TensorDataType::FLOAT32) {
        s.data<float>()[0] /= static_cast<float>(numElements_);
    }
    
    return s;
}

// ============================================================================
// Activations
// ============================================================================

Tensor Tensor::relu() const {
    Tensor result = clone();
    
    if (dtype_ == TensorDataType::FLOAT32) {
        float* ptr = result.data<float>();
        for (int64_t i = 0; i < numElements_; ++i) {
            ptr[i] = std::max(0.0f, ptr[i]);
        }
    }
    
    return result;
}

Tensor Tensor::gelu() const {
    Tensor result = clone();
    
    if (dtype_ == TensorDataType::FLOAT32) {
        float* ptr = result.data<float>();
        const float sqrt_2_over_pi = std::sqrt(2.0f / M_PI);
        
        for (int64_t i = 0; i < numElements_; ++i) {
            float x = ptr[i];
            float tanh_arg = sqrt_2_over_pi * (x + 0.044715f * x * x * x);
            ptr[i] = 0.5f * x * (1.0f + std::tanh(tanh_arg));
        }
    }
    
    return result;
}

Tensor Tensor::sigmoid() const {
    Tensor result = clone();
    
    if (dtype_ == TensorDataType::FLOAT32) {
        float* ptr = result.data<float>();
        for (int64_t i = 0; i < numElements_; ++i) {
            ptr[i] = 1.0f / (1.0f + std::exp(-ptr[i]));
        }
    }
    
    return result;
}

Tensor Tensor::tanh() const {
    Tensor result = clone();
    
    if (dtype_ == TensorDataType::FLOAT32) {
        float* ptr = result.data<float>();
        for (int64_t i = 0; i < numElements_; ++i) {
            ptr[i] = std::tanh(ptr[i]);
        }
    }
    
    return result;
}

Tensor Tensor::softmax(int64_t dim) const {
    Tensor result = clone();
    
    if (dtype_ == TensorDataType::FLOAT32 && ndim() == 2 && dim == -1) {
        float* ptr = result.data<float>();
        int64_t rows = shape_[0];
        int64_t cols = shape_[1];
        
        for (int64_t i = 0; i < rows; ++i) {
            float* row = ptr + i * cols;
            
            // Find max for numerical stability
            float maxVal = *std::max_element(row, row + cols);
            
            // Exp and sum
            float sum = 0.0f;
            for (int64_t j = 0; j < cols; ++j) {
                row[j] = std::exp(row[j] - maxVal);
                sum += row[j];
            }
            
            // Normalize
            for (int64_t j = 0; j < cols; ++j) {
                row[j] /= sum;
            }
        }
    }
    
    return result;
}

// ============================================================================
// Utility
// ============================================================================

void Tensor::zero() {
    std::memset(data_, 0, byteSize());
}

void Tensor::copyFrom(const Tensor& other) {
    if (numElements_ != other.numElements_) {
        throw TensorException("Size mismatch in copyFrom");
    }
    std::memcpy(data_, other.data_, byteSize());
}

Tensor Tensor::clone() const {
    return Tensor(*this);
}

std::string Tensor::toString() const {
    std::ostringstream oss;
    oss << "Tensor(shape=[";
    for (size_t i = 0; i < shape_.size(); ++i) {
        oss << shape_[i];
        if (i < shape_.size() - 1) oss << ", ";
    }
    oss << "], dtype=";
    
    switch (dtype_) {
        case TensorDataType::FLOAT32: oss << "float32"; break;
        case TensorDataType::FLOAT16: oss << "float16"; break;
        case TensorDataType::INT32: oss << "int32"; break;
        default: oss << "unknown"; break;
    }
    
    oss << ", device=";
    switch (device_) {
        case TensorDevice::CPU: oss << "cpu"; break;
        case TensorDevice::CUDA: oss << "cuda"; break;
        case TensorDevice::ROCM: oss << "rocm"; break;
        default: oss << "unknown"; break;
    }
    
    oss << ", size=" << numElements_ << ")";
    return oss.str();
}

// ============================================================================
// Private Methods
// ============================================================================

std::vector<int64_t> Tensor::calculateStrides(const std::vector<int64_t>& shape) {
    std::vector<int64_t> strides(shape.size());
    int64_t stride = 1;
    
    for (int64_t i = shape.size() - 1; i >= 0; --i) {
        strides[i] = stride;
        stride *= shape[i];
    }
    
    return strides;
}

int64_t Tensor::calculateIndex(const std::vector<int64_t>& indices) const {
    int64_t index = 0;
    for (size_t i = 0; i < indices.size(); ++i) {
        index += indices[i] * strides_[i];
    }
    return index;
}

void Tensor::allocate() {
    size_t bytes = byteSize();
    if (bytes == 0) {
        data_ = nullptr;
        return;
    }
    
    // TODO: Use memory pool for allocation
    data_ = ::operator new(bytes);
    if (!data_) {
        throw TensorException("Failed to allocate tensor memory");
    }
}

void Tensor::deallocate() {
    if (data_ && ownsData_) {
        ::operator delete(data_);
    }
    data_ = nullptr;
}

void Tensor::validateIndices(const std::vector<int64_t>& indices) const {
    if (indices.size() != static_cast<size_t>(ndim())) {
        throw TensorException("Index dimension mismatch");
    }
    
    for (size_t i = 0; i < indices.size(); ++i) {
        if (indices[i] < 0 || indices[i] >= shape_[i]) {
            throw TensorException("Index out of bounds at dimension " + std::to_string(i));
        }
    }
}

bool Tensor::canBroadcast(const std::vector<int64_t>& shape1, const std::vector<int64_t>& shape2) {
    size_t maxDim = std::max(shape1.size(), shape2.size());
    
    for (size_t i = 0; i < maxDim; ++i) {
        int64_t dim1 = i < shape1.size() ? shape1[shape1.size() - 1 - i] : 1;
        int64_t dim2 = i < shape2.size() ? shape2[shape2.size() - 1 - i] : 1;
        
        if (dim1 != dim2 && dim1 != 1 && dim2 != 1) {
            return false;
        }
    }
    
    return true;
}

std::vector<int64_t> Tensor::broadcastShape(const std::vector<int64_t>& shape1,
                                             const std::vector<int64_t>& shape2) {
    size_t maxDim = std::max(shape1.size(), shape2.size());
    std::vector<int64_t> result(maxDim);
    
    for (size_t i = 0; i < maxDim; ++i) {
        int64_t dim1 = i < shape1.size() ? shape1[shape1.size() - 1 - i] : 1;
        int64_t dim2 = i < shape2.size() ? shape2[shape2.size() - 1 - i] : 1;
        result[maxDim - 1 - i] = std::max(dim1, dim2);
    }
    
    return result;
}

// ============================================================================
// Creation Functions
// ============================================================================

Tensor zeros(const std::vector<int64_t>& shape, TensorDataType dtype) {
    Tensor t(shape, dtype);
    t.zero();
    return t;
}

Tensor ones(const std::vector<int64_t>& shape, TensorDataType dtype) {
    Tensor t(shape, dtype);
    if (dtype == TensorDataType::FLOAT32) {
        t.fill(1.0f);
    }
    return t;
}

Tensor rand(const std::vector<int64_t>& shape, TensorDataType dtype) {
    Tensor t(shape, dtype);
    
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::uniform_real_distribution<float> dis(0.0f, 1.0f);
    
    if (dtype == TensorDataType::FLOAT32) {
        float* ptr = t.data<float>();
        for (int64_t i = 0; i < t.size(); ++i) {
            ptr[i] = dis(gen);
        }
    }
    
    return t;
}

Tensor randn(const std::vector<int64_t>& shape, double mean, double std, TensorDataType dtype) {
    Tensor t(shape, dtype);
    
    static std::random_device rd;
    static std::mt19937 gen(rd());
    std::normal_distribution<float> dis(mean, std);
    
    if (dtype == TensorDataType::FLOAT32) {
        float* ptr = t.data<float>();
        for (int64_t i = 0; i < t.size(); ++i) {
            ptr[i] = dis(gen);
        }
    }
    
    return t;
}

Tensor eye(int64_t n, TensorDataType dtype) {
    Tensor t({n, n}, dtype);
    t.zero();
    
    if (dtype == TensorDataType::FLOAT32) {
        float* ptr = t.data<float>();
        for (int64_t i = 0; i < n; ++i) {
            ptr[i * n + i] = 1.0f;
        }
    }
    
    return t;
}

} // namespace VersaAI
