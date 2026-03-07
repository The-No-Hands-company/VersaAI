/**
 * @file VersaAIModelLoader.cpp
 * @brief Implementation of model loading infrastructure
 */

#include "../include/VersaAIModelLoader.hpp"
#include <algorithm>
#include <cstring>

#ifdef _WIN32
    #include <windows.h>
#else
    #include <sys/mman.h>
    #include <sys/stat.h>
    #include <fcntl.h>
    #include <unistd.h>
#endif

namespace VersaAI {
namespace Model {

// ============================================================================
// MemoryMappedFile Implementation
// ============================================================================

MemoryMappedFile::~MemoryMappedFile() {
    close();
}

MemoryMappedFile::MemoryMappedFile(MemoryMappedFile&& other) noexcept
    : data_(other.data_)
    , size_(other.size_)
    , locked_(other.locked_)
#ifdef _WIN32
    , fileHandle_(other.fileHandle_)
    , mappingHandle_(other.mappingHandle_)
#else
    , fileDescriptor_(other.fileDescriptor_)
#endif
{
    other.data_ = nullptr;
    other.size_ = 0;
    other.locked_ = false;
#ifdef _WIN32
    other.fileHandle_ = nullptr;
    other.mappingHandle_ = nullptr;
#else
    other.fileDescriptor_ = -1;
#endif
}

MemoryMappedFile& MemoryMappedFile::operator=(MemoryMappedFile&& other) noexcept {
    if (this != &other) {
        close();

        data_ = other.data_;
        size_ = other.size_;
        locked_ = other.locked_;
#ifdef _WIN32
        fileHandle_ = other.fileHandle_;
        mappingHandle_ = other.mappingHandle_;
#else
        fileDescriptor_ = other.fileDescriptor_;
#endif

        other.data_ = nullptr;
        other.size_ = 0;
        other.locked_ = false;
#ifdef _WIN32
        other.fileHandle_ = nullptr;
        other.mappingHandle_ = nullptr;
#else
        other.fileDescriptor_ = -1;
#endif
    }
    return *this;
}

bool MemoryMappedFile::open(const std::filesystem::path& filePath, bool readOnly) {
    close();

    if (!std::filesystem::exists(filePath)) {
        Logger::getInstance().error(
            "File does not exist: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }

    size_ = std::filesystem::file_size(filePath);
    if (size_ == 0) {
        Logger::getInstance().error(
            "File is empty: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }

#ifdef _WIN32
    // Windows implementation
    DWORD access = readOnly ? GENERIC_READ : (GENERIC_READ | GENERIC_WRITE);
    DWORD share = FILE_SHARE_READ;
    DWORD disposition = OPEN_EXISTING;

    fileHandle_ = CreateFileW(
        filePath.c_str(),
        access,
        share,
        nullptr,
        disposition,
        FILE_ATTRIBUTE_NORMAL,
        nullptr
    );

    if (fileHandle_ == INVALID_HANDLE_VALUE) {
        Logger::getInstance().error(
            "Failed to open file: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }

    DWORD protect = readOnly ? PAGE_READONLY : PAGE_READWRITE;
    mappingHandle_ = CreateFileMappingW(
        fileHandle_,
        nullptr,
        protect,
        0, 0,
        nullptr
    );

    if (mappingHandle_ == nullptr) {
        CloseHandle(fileHandle_);
        fileHandle_ = nullptr;
        Logger::getInstance().error(
            "Failed to create file mapping: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }

    DWORD mapAccess = readOnly ? FILE_MAP_READ : FILE_MAP_ALL_ACCESS;
    data_ = MapViewOfFile(mappingHandle_, mapAccess, 0, 0, 0);

    if (data_ == nullptr) {
        CloseHandle(mappingHandle_);
        CloseHandle(fileHandle_);
        mappingHandle_ = nullptr;
        fileHandle_ = nullptr;
        Logger::getInstance().error(
            "Failed to map view of file: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }

#else
    // Unix implementation (Linux, macOS)
    int flags = readOnly ? O_RDONLY : O_RDWR;
    fileDescriptor_ = ::open(filePath.c_str(), flags);

    if (fileDescriptor_ == -1) {
        Logger::getInstance().error(
            "Failed to open file: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }

    int prot = readOnly ? PROT_READ : (PROT_READ | PROT_WRITE);
    data_ = ::mmap(nullptr, size_, prot, MAP_SHARED, fileDescriptor_, 0);

    if (data_ == MAP_FAILED) {
        ::close(fileDescriptor_);
        fileDescriptor_ = -1;
        data_ = nullptr;
        Logger::getInstance().error(
            "Failed to memory map file: " + filePath.string(),
            "MemoryMappedFile"
        );
        return false;
    }
#endif

    Logger::getInstance().info(
        "Memory-mapped file: " + filePath.filename().string() + " (" + std::to_string(size_ / 1024 / 1024) + " MB)",
        "MemoryMappedFile"
    );

    return true;
}

void MemoryMappedFile::close() {
    if (data_ == nullptr) {
        return;
    }

    if (locked_) {
        unlock();
    }

#ifdef _WIN32
    UnmapViewOfFile(data_);
    CloseHandle(mappingHandle_);
    CloseHandle(fileHandle_);
    mappingHandle_ = nullptr;
    fileHandle_ = nullptr;
#else
    ::munmap(data_, size_);
    ::close(fileDescriptor_);
    fileDescriptor_ = -1;
#endif

    data_ = nullptr;
    size_ = 0;
}

void MemoryMappedFile::read(size_t offset, void* dest, size_t length) const {
    if (offset + length > size_) {
        throw ModelException(
            "Memory-mapped file read out of bounds",
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    std::memcpy(dest, static_cast<const uint8_t*>(data_) + offset, length);
}

bool MemoryMappedFile::lock() {
    if (locked_ || data_ == nullptr) {
        return false;
    }

#ifdef _WIN32
    if (!VirtualLock(data_, size_)) {
        Logger::getInstance().warning(
            "Failed to lock memory pages",
            "MemoryMappedFile"
        );
        return false;
    }
#else
    if (::mlock(data_, size_) != 0) {
        Logger::getInstance().warning(
            "Failed to lock memory pages",
            "MemoryMappedFile"
        );
        return false;
    }
#endif

    locked_ = true;
    Logger::getInstance().info(
        "Locked memory pages in RAM (" + std::to_string(size_ / 1024 / 1024) + " MB)",
        "MemoryMappedFile"
    );
    return true;
}

void MemoryMappedFile::unlock() {
    if (!locked_ || data_ == nullptr) {
        return;
    }

#ifdef _WIN32
    VirtualUnlock(data_, size_);
#else
    ::munlock(data_, size_);
#endif

    locked_ = false;
}

// ============================================================================
// ModelFileReader Implementation
// ============================================================================

ModelFileReader::ModelFileReader(const std::filesystem::path& filePath)
    : file_(filePath, std::ios::binary)
    , fileSize_(0)
{
    if (!file_.is_open()) {
        throw ModelException(
            "Failed to open file: " + filePath.string(),
            ErrorCode::MODEL_LOAD_FAILED
        );
    }

    file_.seekg(0, std::ios::end);
    fileSize_ = file_.tellg();
    file_.seekg(0, std::ios::beg);
}

std::vector<uint8_t> ModelFileReader::read(size_t offset, size_t length) {
    if (offset + length > fileSize_) {
        throw ModelException(
            "File read out of bounds",
            ErrorCode::MODEL_INVALID_FILE
        );
    }

    std::vector<uint8_t> buffer(length);
    file_.seekg(offset);
    file_.read(reinterpret_cast<char*>(buffer.data()), length);

    if (!file_) {
        throw ModelException(
            "Failed to read from file",
            ErrorCode::MODEL_LOAD_FAILED
        );
    }

    return buffer;
}

std::string ModelFileReader::readString(size_t offset, size_t length) {
    auto bytes = read(offset, length);
    return std::string(bytes.begin(), bytes.end());
}

// ============================================================================
// FormatDetector Implementation
// ============================================================================

ModelFormat FormatDetector::detectFromExtension(const std::filesystem::path& filePath) {
    auto ext = filePath.extension().string();
    std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);

    if (ext == ".gguf") return ModelFormat::GGUF;
    if (ext == ".ggml") return ModelFormat::GGML;
    if (ext == ".onnx") return ModelFormat::ONNX;
    if (ext == ".safetensors") return ModelFormat::SafeTensors;
    if (ext == ".pth" || ext == ".pt") return ModelFormat::PyTorch;
    if (ext == ".pb") return ModelFormat::TensorFlow;

    return ModelFormat::Unknown;
}

ModelFormat FormatDetector::detectFromMagic(const std::filesystem::path& filePath) {
    auto magic = readMagic(filePath);
    if (magic.size() < 4) {
        return ModelFormat::Unknown;
    }

    // GGUF: "GGUF" (0x47475546 in little-endian)
    if (magic[0] == 0x47 && magic[1] == 0x47 &&
        magic[2] == 0x55 && magic[3] == 0x46) {
        return ModelFormat::GGUF;
    }

    // GGML: "ggml" or various model-specific magic
    if (magic[0] == 0x67 && magic[1] == 0x67 &&
        magic[2] == 0x6D && magic[3] == 0x6C) {
        return ModelFormat::GGML;
    }

    // ONNX: Protocol buffer magic
    if (magic[0] == 0x08) {
        return ModelFormat::ONNX;
    }

    // PyTorch: ZIP magic (PyTorch uses ZIP)
    if (magic[0] == 0x50 && magic[1] == 0x4B) {
        return ModelFormat::PyTorch;
    }

    return ModelFormat::Unknown;
}

std::vector<uint8_t> FormatDetector::readMagic(const std::filesystem::path& filePath) {
    std::ifstream file(filePath, std::ios::binary);
    if (!file.is_open()) {
        return {};
    }

    std::vector<uint8_t> magic(16);
    file.read(reinterpret_cast<char*>(magic.data()), 16);
    magic.resize(file.gcount());

    return magic;
}

bool FormatDetector::validatePath(const std::filesystem::path& filePath) {
    if (!std::filesystem::exists(filePath)) {
        Logger::getInstance().error(
            "File does not exist: " + filePath.string(),
            "FormatDetector"
        );
        return false;
    }

    if (!std::filesystem::is_regular_file(filePath)) {
        Logger::getInstance().error(
            "Path is not a regular file: " + filePath.string(),
            "FormatDetector"
        );
        return false;
    }

    return true;
}

uint64_t FormatDetector::getFileSize(const std::filesystem::path& filePath) {
    if (!validatePath(filePath)) {
        return 0;
    }

    return std::filesystem::file_size(filePath);
}

// ============================================================================
// ModelLoaderFactory Implementation
// ============================================================================

ModelLoaderFactory& ModelLoaderFactory::getInstance() {
    static ModelLoaderFactory instance;
    return instance;
}

void ModelLoaderFactory::registerLoader(
    ModelFormat format,
    std::function<std::unique_ptr<IModelLoader>()> factory
) {
    std::lock_guard<std::mutex> lock(mutex_);
    loaderFactories_[format] = factory;

    Logger::getInstance().info(
        "Registered model loader: " + formatToString(format),
        "ModelLoaderFactory"
    );
}

std::unique_ptr<IModelLoader> ModelLoaderFactory::getLoader(ModelFormat format) const {
    std::lock_guard<std::mutex> lock(mutex_);

    auto it = loaderFactories_.find(format);
    if (it == loaderFactories_.end()) {
        return nullptr;
    }

    return it->second();
}

std::unique_ptr<IModelLoader> ModelLoaderFactory::getLoaderForFile(
    const std::filesystem::path& filePath
) const {
    auto format = detectFormat(filePath);
    if (format == ModelFormat::Unknown) {
        return nullptr;
    }

    return getLoader(format);
}

ModelFormat ModelLoaderFactory::detectFormat(const std::filesystem::path& filePath) const {
    if (!FormatDetector::validatePath(filePath)) {
        return ModelFormat::Unknown;
    }

    // First try extension
    auto format = FormatDetector::detectFromExtension(filePath);
    if (format != ModelFormat::Unknown) {
        return format;
    }

    // Fall back to magic bytes
    return FormatDetector::detectFromMagic(filePath);
}

std::vector<ModelFormat> ModelLoaderFactory::getSupportedFormats() const {
    std::lock_guard<std::mutex> lock(mutex_);

    std::vector<ModelFormat> formats;
    formats.reserve(loaderFactories_.size());

    for (const auto& [format, _] : loaderFactories_) {
        formats.push_back(format);
    }

    return formats;
}

} // namespace Model
} // namespace VersaAI
