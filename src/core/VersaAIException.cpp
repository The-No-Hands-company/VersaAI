#include "VersaAIException.hpp"
#include "VersaAILogger.hpp"
#include <sstream>
#include <iomanip>
#include <ctime>

#ifdef __GNUC__
#include <execinfo.h>
#include <cxxabi.h>
#endif

namespace VersaAI {

// ============================================================================
// Exception Implementation
// ============================================================================

Exception::Exception(
    const std::string& message,
    ErrorCode code,
    ErrorSeverity severity
) : message_(message),
    errorCode_(code),
    severity_(severity),
    component_("VersaAI"),
    timestamp_(std::chrono::system_clock::now()) {
    captureStackTrace();
}

Exception::Exception(
    const std::string& message,
    ErrorCode code,
    ErrorSeverity severity,
    std::exception_ptr cause
) : message_(message),
    errorCode_(code),
    severity_(severity),
    component_("VersaAI"),
    cause_(cause),
    timestamp_(std::chrono::system_clock::now()) {
    captureStackTrace();
}

const char* Exception::what() const noexcept {
    try {
        if (whatBuffer_.empty()) {
            whatBuffer_ = format();
        }
        return whatBuffer_.c_str();
    } catch (...) {
        return message_.c_str();
    }
}

Exception& Exception::addContext(const std::string& key, const std::string& value) {
    context_[key] = value;
    whatBuffer_.clear();  // Invalidate cache
    return *this;
}

Exception& Exception::setComponent(const std::string& component) {
    component_ = component;
    whatBuffer_.clear();
    return *this;
}

std::string Exception::format() const {
    std::ostringstream oss;

    // Header
    oss << "[" << errorSeverityToString(severity_) << "] "
        << "[" << component_ << "] "
        << errorCodeToString(errorCode_) << " (" << static_cast<int>(errorCode_) << ")\n";

    // Message
    oss << "Message: " << message_ << "\n";

    // Timestamp
    auto time_t = std::chrono::system_clock::to_time_t(timestamp_);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp_.time_since_epoch()) % 1000;

    std::tm tm_buf;
    localtime_r(&time_t, &tm_buf);

    oss << "Timestamp: "
        << std::put_time(&tm_buf, "%Y-%m-%d %H:%M:%S")
        << "." << std::setfill('0') << std::setw(3) << ms.count() << "\n";

    // Context
    if (!context_.empty()) {
        oss << "Context:\n";
        for (const auto& [key, value] : context_) {
            oss << "  " << key << " = " << value << "\n";
        }
    }

    // Stack trace
    if (!stackTrace_.empty()) {
        oss << "Stack Trace:\n";
        for (size_t i = 0; i < stackTrace_.size(); ++i) {
            oss << "  #" << i << " " << stackTrace_[i] << "\n";
        }
    }

    // Chained cause
    if (cause_) {
        try {
            std::rethrow_exception(cause_);
        } catch (const Exception& ex) {
            oss << "\nCaused by:\n" << ex.format();
        } catch (const std::exception& ex) {
            oss << "\nCaused by: " << ex.what() << "\n";
        } catch (...) {
            oss << "\nCaused by: Unknown exception\n";
        }
    }

    return oss.str();
}

void Exception::captureStackTrace() {
#ifdef __GNUC__
    const int maxFrames = 64;
    void* buffer[maxFrames];
    int frameCount = backtrace(buffer, maxFrames);

    char** symbols = backtrace_symbols(buffer, frameCount);
    if (symbols) {
        // Skip first 2 frames (captureStackTrace and Exception constructor)
        for (int i = 2; i < frameCount; ++i) {
            std::string frame = symbols[i];

            // Try to demangle C++ symbols
            size_t start = frame.find('(');
            size_t end = frame.find('+', start);
            if (start != std::string::npos && end != std::string::npos) {
                std::string mangled = frame.substr(start + 1, end - start - 1);
                int status;
                char* demangled = abi::__cxa_demangle(mangled.c_str(), nullptr, nullptr, &status);
                if (status == 0 && demangled) {
                    frame = frame.substr(0, start + 1) + demangled + frame.substr(end);
                    free(demangled);
                }
            }

            stackTrace_.push_back(frame);
        }
        free(symbols);
    }
#endif
    // On non-GNU platforms, stack trace remains empty
}

// ============================================================================
// Utility Functions
// ============================================================================

std::string errorCodeToString(ErrorCode code) {
    switch (code) {
        // Generic
        case ErrorCode::UNKNOWN: return "UNKNOWN";
        case ErrorCode::INVALID_ARGUMENT: return "INVALID_ARGUMENT";
        case ErrorCode::NULL_POINTER: return "NULL_POINTER";
        case ErrorCode::OUT_OF_RANGE: return "OUT_OF_RANGE";
        case ErrorCode::INVALID_STATE: return "INVALID_STATE";

        // Model
        case ErrorCode::MODEL_NOT_FOUND: return "MODEL_NOT_FOUND";
        case ErrorCode::MODEL_LOAD_FAILED: return "MODEL_LOAD_FAILED";
        case ErrorCode::MODEL_INVALID_FORMAT: return "MODEL_INVALID_FORMAT";
        case ErrorCode::MODEL_INFERENCE_FAILED: return "MODEL_INFERENCE_FAILED";
        case ErrorCode::MODEL_OUT_OF_MEMORY: return "MODEL_OUT_OF_MEMORY";

        // Agent
        case ErrorCode::AGENT_NOT_REGISTERED: return "AGENT_NOT_REGISTERED";
        case ErrorCode::AGENT_INITIALIZATION_FAILED: return "AGENT_INITIALIZATION_FAILED";
        case ErrorCode::AGENT_TASK_FAILED: return "AGENT_TASK_FAILED";
        case ErrorCode::AGENT_TIMEOUT: return "AGENT_TIMEOUT";

        // Context
        case ErrorCode::CONTEXT_KEY_NOT_FOUND: return "CONTEXT_KEY_NOT_FOUND";
        case ErrorCode::CONTEXT_SERIALIZATION_FAILED: return "CONTEXT_SERIALIZATION_FAILED";
        case ErrorCode::CONTEXT_DESERIALIZATION_FAILED: return "CONTEXT_DESERIALIZATION_FAILED";
        case ErrorCode::CONTEXT_VERSION_MISMATCH: return "CONTEXT_VERSION_MISMATCH";

        // Registry
        case ErrorCode::REGISTRY_DUPLICATE_KEY: return "REGISTRY_DUPLICATE_KEY";
        case ErrorCode::REGISTRY_KEY_NOT_FOUND: return "REGISTRY_KEY_NOT_FOUND";
        case ErrorCode::REGISTRY_INVALID_TYPE: return "REGISTRY_INVALID_TYPE";

        // Configuration
        case ErrorCode::CONFIG_FILE_NOT_FOUND: return "CONFIG_FILE_NOT_FOUND";
        case ErrorCode::CONFIG_PARSE_ERROR: return "CONFIG_PARSE_ERROR";
        case ErrorCode::CONFIG_INVALID_VALUE: return "CONFIG_INVALID_VALUE";

        // I/O
        case ErrorCode::FILE_NOT_FOUND: return "FILE_NOT_FOUND";
        case ErrorCode::FILE_READ_ERROR: return "FILE_READ_ERROR";
        case ErrorCode::FILE_WRITE_ERROR: return "FILE_WRITE_ERROR";
        case ErrorCode::NETWORK_ERROR: return "NETWORK_ERROR";

        // Resource
        case ErrorCode::RESOURCE_EXHAUSTED: return "RESOURCE_EXHAUSTED";
        case ErrorCode::RESOURCE_LOCKED: return "RESOURCE_LOCKED";
        case ErrorCode::RESOURCE_UNAVAILABLE: return "RESOURCE_UNAVAILABLE";

        default: return "UNKNOWN_ERROR_CODE";
    }
}

std::string errorSeverityToString(ErrorSeverity severity) {
    switch (severity) {
        case ErrorSeverity::LOW: return "LOW";
        case ErrorSeverity::MEDIUM: return "MEDIUM";
        case ErrorSeverity::HIGH: return "HIGH";
        case ErrorSeverity::CRITICAL: return "CRITICAL";
        default: return "UNKNOWN";
    }
}

void logException(const Exception& ex, const std::string& additionalContext) {
    auto& logger = Logger::getInstance();

    // Determine log level based on severity
    LogLevel level;
    switch (ex.getSeverity()) {
        case ErrorSeverity::LOW:
            level = LogLevel::WARNING;
            break;
        case ErrorSeverity::MEDIUM:
            level = LogLevel::ERROR;
            break;
        case ErrorSeverity::HIGH:
        case ErrorSeverity::CRITICAL:
            level = LogLevel::CRITICAL;
            break;
    }

    // Create log entry
    LogEntry entry(level, ex.getMessage(), ex.getComponent());

    // Add error code and severity
    entry.addContext("error_code", errorCodeToString(ex.getErrorCode()));
    entry.addContext("error_code_value", std::to_string(static_cast<int>(ex.getErrorCode())));
    entry.addContext("severity", errorSeverityToString(ex.getSeverity()));

    // Add exception context
    for (const auto& [key, value] : ex.getContext()) {
        entry.addContext(key, value);
    }

    // Add additional context if provided
    if (!additionalContext.empty()) {
        entry.addContext("additional_context", additionalContext);
    }

    // Log the entry
    logger.log(entry);

    // For high/critical severity, also log stack trace as separate entries
    if (ex.getSeverity() >= ErrorSeverity::HIGH && !ex.getStackTrace().empty()) {
        logger.debug("Stack trace for " + errorCodeToString(ex.getErrorCode()) + ":",
                     ex.getComponent());
        for (size_t i = 0; i < ex.getStackTrace().size(); ++i) {
            logger.debug("  #" + std::to_string(i) + " " + ex.getStackTrace()[i],
                        ex.getComponent());
        }
    }
}

} // namespace VersaAI
