#pragma once

#include <exception>
#include <string>
#include <map>
#include <memory>
#include <chrono>
#include <sstream>
#include <vector>

namespace VersaAI {

// Forward declaration
class Logger;

/**
 * @brief Error severity levels for exceptions
 */
enum class ErrorSeverity {
    LOW,         // Minor issue, can continue
    MEDIUM,      // Significant issue, degraded functionality
    HIGH,        // Major issue, feature unavailable
    CRITICAL     // System-level failure, cannot continue
};

/**
 * @brief Error codes for categorizing exceptions
 */
enum class ErrorCode {
    // Generic errors (0-99)
    UNKNOWN = 0,
    INVALID_ARGUMENT = 1,
    NULL_POINTER = 2,
    OUT_OF_RANGE = 3,
    INVALID_STATE = 4,

    // Model errors (100-199)
    MODEL_NOT_FOUND = 100,
    MODEL_LOAD_FAILED = 101,
    MODEL_INVALID_FORMAT = 102,
    MODEL_INFERENCE_FAILED = 103,
    MODEL_OUT_OF_MEMORY = 104,
    MODEL_INVALID_FILE = 105,
    MODEL_UNSUPPORTED_FORMAT = 106,
    MODEL_LOADER_NOT_FOUND = 107,
    MODEL_FILE_NOT_FOUND = 108,
    MODEL_VALIDATION_FAILED = 109,
    MODEL_TENSOR_NOT_FOUND = 110,

    // Agent errors (200-299)
    AGENT_NOT_REGISTERED = 200,
    AGENT_INITIALIZATION_FAILED = 201,
    AGENT_TASK_FAILED = 202,
    AGENT_TIMEOUT = 203,

    // Context errors (300-399)
    CONTEXT_KEY_NOT_FOUND = 300,
    CONTEXT_SERIALIZATION_FAILED = 301,
    CONTEXT_DESERIALIZATION_FAILED = 302,
    CONTEXT_VERSION_MISMATCH = 303,

    // Registry errors (400-499)
    REGISTRY_DUPLICATE_KEY = 400,
    REGISTRY_DUPLICATE = 400,  // Alias for REGISTRY_DUPLICATE_KEY
    REGISTRY_KEY_NOT_FOUND = 401,
    REGISTRY_NOT_FOUND = 401,  // Alias for REGISTRY_KEY_NOT_FOUND
    REGISTRY_INVALID_TYPE = 402,
    REGISTRY_DISPOSED = 403,
    REGISTRY_CIRCULAR_DEPENDENCY = 404,
    REGISTRY_INTERNAL_ERROR = 405,

    // Configuration errors (500-599)
    CONFIG_FILE_NOT_FOUND = 500,
    CONFIG_PARSE_ERROR = 501,
    CONFIG_INVALID_VALUE = 502,

    // I/O errors (600-699)
    FILE_NOT_FOUND = 600,
    FILE_READ_ERROR = 601,
    FILE_WRITE_ERROR = 602,
    NETWORK_ERROR = 603,

    // Resource errors (700-799)
    RESOURCE_EXHAUSTED = 700,
    RESOURCE_LOCKED = 701,
    RESOURCE_UNAVAILABLE = 702
};

/**
 * @brief Base exception class for VersaAI
 *
 * Provides rich error context, error codes, severity levels, and chaining support.
 * All VersaAI exceptions should derive from this class.
 */
class Exception : public std::exception {
public:
    /**
     * @brief Construct exception with message and error code
     */
    explicit Exception(
        const std::string& message,
        ErrorCode code = ErrorCode::UNKNOWN,
        ErrorSeverity severity = ErrorSeverity::MEDIUM
    );

    /**
     * @brief Construct exception with chained cause
     */
    Exception(
        const std::string& message,
        ErrorCode code,
        ErrorSeverity severity,
        std::exception_ptr cause
    );

    virtual ~Exception() noexcept = default;

    // Standard exception interface
    const char* what() const noexcept override;

    // VersaAI-specific interface
    ErrorCode getErrorCode() const noexcept { return errorCode_; }
    ErrorSeverity getSeverity() const noexcept { return severity_; }
    const std::string& getMessage() const noexcept { return message_; }
    const std::string& getComponent() const noexcept { return component_; }

    /**
     * @brief Add contextual key-value data to the exception
     */
    Exception& addContext(const std::string& key, const std::string& value);

    /**
     * @brief Get all context data
     */
    const std::map<std::string, std::string>& getContext() const noexcept { return context_; }

    /**
     * @brief Set the component that threw this exception
     */
    Exception& setComponent(const std::string& component);

    /**
     * @brief Get the chained cause exception
     */
    std::exception_ptr getCause() const noexcept { return cause_; }

    /**
     * @brief Get timestamp when exception was created
     */
    std::chrono::system_clock::time_point getTimestamp() const noexcept { return timestamp_; }

    /**
     * @brief Format exception with all context as a detailed string
     */
    std::string format() const;

    /**
     * @brief Get stack trace (if available)
     */
    const std::vector<std::string>& getStackTrace() const noexcept { return stackTrace_; }

protected:
    std::string message_;
    ErrorCode errorCode_;
    ErrorSeverity severity_;
    std::string component_;
    std::map<std::string, std::string> context_;
    std::exception_ptr cause_;
    std::chrono::system_clock::time_point timestamp_;
    std::vector<std::string> stackTrace_;
    mutable std::string whatBuffer_;  // Cached what() string

    void captureStackTrace();
};

// ============================================================================
// Domain-Specific Exceptions
// ============================================================================

/**
 * @brief Exception thrown by model-related operations
 */
class ModelException : public Exception {
public:
    explicit ModelException(
        const std::string& message,
        ErrorCode code = ErrorCode::MODEL_LOAD_FAILED
    ) : Exception(message, code, ErrorSeverity::HIGH) {
        setComponent("Model");
    }

    ModelException& setModelName(const std::string& name) {
        addContext("model_name", name);
        return *this;
    }

    ModelException& setModelPath(const std::string& path) {
        addContext("model_path", path);
        return *this;
    }
};

/**
 * @brief Exception thrown by agent operations
 */
class AgentException : public Exception {
public:
    explicit AgentException(
        const std::string& message,
        ErrorCode code = ErrorCode::AGENT_TASK_FAILED
    ) : Exception(message, code, ErrorSeverity::MEDIUM) {
        setComponent("Agent");
    }

    AgentException& setAgentName(const std::string& name) {
        addContext("agent_name", name);
        return *this;
    }

    AgentException& setTaskDescription(const std::string& task) {
        addContext("task", task);
        return *this;
    }
};

/**
 * @brief Exception thrown by context operations
 */
class ContextException : public Exception {
public:
    explicit ContextException(
        const std::string& message,
        ErrorCode code = ErrorCode::CONTEXT_KEY_NOT_FOUND
    ) : Exception(message, code, ErrorSeverity::LOW) {
        setComponent("Context");
    }

    ContextException& setKey(const std::string& key) {
        addContext("key", key);
        return *this;
    }
};

/**
 * @brief Exception thrown by registry operations
 */
class RegistryException : public Exception {
public:
    explicit RegistryException(
        const std::string& message,
        ErrorCode code = ErrorCode::REGISTRY_KEY_NOT_FOUND
    ) : Exception(message, code, ErrorSeverity::MEDIUM) {
        setComponent("Registry");
    }

    RegistryException& setRegistryType(const std::string& type) {
        addContext("registry_type", type);
        return *this;
    }

    RegistryException& setKey(const std::string& key) {
        addContext("key", key);
        return *this;
    }
};

/**
 * @brief Exception thrown by configuration operations
 */
class ConfigException : public Exception {
public:
    explicit ConfigException(
        const std::string& message,
        ErrorCode code = ErrorCode::CONFIG_PARSE_ERROR
    ) : Exception(message, code, ErrorSeverity::HIGH) {
        setComponent("Config");
    }

    ConfigException& setConfigFile(const std::string& file) {
        addContext("config_file", file);
        return *this;
    }

    ConfigException& setConfigKey(const std::string& key) {
        addContext("config_key", key);
        return *this;
    }
};

/**
 * @brief Exception thrown by I/O operations
 */
class IOException : public Exception {
public:
    explicit IOException(
        const std::string& message,
        ErrorCode code = ErrorCode::FILE_READ_ERROR
    ) : Exception(message, code, ErrorSeverity::HIGH) {
        setComponent("IO");
    }

    IOException& setFilePath(const std::string& path) {
        addContext("file_path", path);
        return *this;
    }
};

/**
 * @brief Exception thrown by resource management operations
 */
class ResourceException : public Exception {
public:
    explicit ResourceException(
        const std::string& message,
        ErrorCode code = ErrorCode::RESOURCE_EXHAUSTED
    ) : Exception(message, code, ErrorSeverity::CRITICAL) {
        setComponent("Resource");
    }

    ResourceException& setResourceType(const std::string& type) {
        addContext("resource_type", type);
        return *this;
    }
};

// ============================================================================
// Exception Utilities
// ============================================================================

/**
 * @brief Convert ErrorCode to string
 */
std::string errorCodeToString(ErrorCode code);

/**
 * @brief Convert ErrorSeverity to string
 */
std::string errorSeverityToString(ErrorSeverity severity);

/**
 * @brief Log an exception with full context
 */
void logException(const Exception& ex, const std::string& additionalContext = "");

/**
 * @brief Rethrow exception with additional context
 */
template<typename ExceptionType>
[[noreturn]] void rethrowWithContext(
    const std::string& message,
    const std::map<std::string, std::string>& context = {}
) {
    try {
        throw;  // Rethrow current exception
    } catch (const Exception& ex) {
        ExceptionType newEx(message, ex.getErrorCode());
        newEx.setComponent(ex.getComponent());
        for (const auto& [key, value] : ex.getContext()) {
            newEx.addContext(key, value);
        }
        for (const auto& [key, value] : context) {
            newEx.addContext(key, value);
        }
        throw newEx;
    } catch (const std::exception& ex) {
        ExceptionType newEx(message + ": " + ex.what());
        for (const auto& [key, value] : context) {
            newEx.addContext(key, value);
        }
        throw newEx;
    }
}

} // namespace VersaAI
