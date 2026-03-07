/**
 * VersaAI C++ Bindings - Full Version
 *
 * Exposes C++ core infrastructure to Python via pybind11:
 * - Logger: High-performance structured logging
 * - Exceptions: Exception hierarchy with error codes
 * - ErrorRecovery: Retry strategies, fallback, circuit breakers
 * - Context: Session management
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/chrono.h>

#include "../include/VersaAILogger.hpp"
#include "../include/VersaAIException.hpp"
#include "../include/VersaAIErrorRecovery.hpp"
#include "../include/VersaAIContext_v2.hpp"

namespace py = pybind11;
using namespace VersaAI;

PYBIND11_MODULE(versaai_core, m) {
    m.doc() = "VersaAI C++ Core - High-performance infrastructure for AI systems";

    // Module metadata
    m.attr("__version__") = "0.2.0";
    m.attr("__cpp_version__") = "C++23";
    m.attr("__author__") = "VersaVerse Team";

    // ========================================================================
    // LOGGING
    // ========================================================================

    py::enum_<LogLevel>(m, "LogLevel", "Logging severity levels")
        .value("DEBUG", LogLevel::DEBUG, "Detailed debugging information")
        .value("INFO", LogLevel::INFO, "General informational messages")
        .value("WARNING", LogLevel::WARNING, "Warning messages")
        .value("ERROR", LogLevel::ERROR, "Error messages")
        .value("CRITICAL", LogLevel::CRITICAL, "Critical failures")
        .export_values();

    py::class_<Logger, std::unique_ptr<Logger, py::nodelete>>(m, "Logger",
        "High-performance structured logger (singleton)")
        .def_static("get_instance", &Logger::getInstance,
            py::return_value_policy::reference,
            "Get Logger singleton instance")
        .def("debug",
            [](Logger& self, const std::string& message, const std::string& component) {
                self.debug(message, component);
            },
            py::arg("message"), py::arg("component") = "Python",
            "Log debug message")
        .def("info",
            [](Logger& self, const std::string& message, const std::string& component) {
                self.info(message, component);
            },
            py::arg("message"), py::arg("component") = "Python",
            "Log info message")
        .def("warning",
            [](Logger& self, const std::string& message, const std::string& component) {
                self.warning(message, component);
            },
            py::arg("message"), py::arg("component") = "Python",
            "Log warning message")
        .def("error",
            [](Logger& self, const std::string& message, const std::string& component) {
                self.error(message, component);
            },
            py::arg("message"), py::arg("component") = "Python",
            "Log error message")
        .def("critical",
            [](Logger& self, const std::string& message, const std::string& component) {
                self.critical(message, component);
            },
            py::arg("message"), py::arg("component") = "Python",
            "Log critical message");

    // ========================================================================
    // EXCEPTIONS
    // ========================================================================

    py::enum_<ErrorCode>(m, "ErrorCode", "Error classification codes")
        // Generic errors
        .value("UNKNOWN", ErrorCode::UNKNOWN)
        .value("INVALID_ARGUMENT", ErrorCode::INVALID_ARGUMENT)
        .value("NULL_POINTER", ErrorCode::NULL_POINTER)
        .value("OUT_OF_RANGE", ErrorCode::OUT_OF_RANGE)
        .value("INVALID_STATE", ErrorCode::INVALID_STATE)
        // Model errors
        .value("MODEL_NOT_FOUND", ErrorCode::MODEL_NOT_FOUND)
        .value("MODEL_LOAD_FAILED", ErrorCode::MODEL_LOAD_FAILED)
        .value("MODEL_INVALID_FORMAT", ErrorCode::MODEL_INVALID_FORMAT)
        .value("MODEL_INFERENCE_FAILED", ErrorCode::MODEL_INFERENCE_FAILED)
        .value("MODEL_OUT_OF_MEMORY", ErrorCode::MODEL_OUT_OF_MEMORY)
        // Agent errors
        .value("AGENT_NOT_REGISTERED", ErrorCode::AGENT_NOT_REGISTERED)
        .value("AGENT_INITIALIZATION_FAILED", ErrorCode::AGENT_INITIALIZATION_FAILED)
        .value("AGENT_TASK_FAILED", ErrorCode::AGENT_TASK_FAILED)
        .value("AGENT_TIMEOUT", ErrorCode::AGENT_TIMEOUT)
        // Context errors
        .value("CONTEXT_KEY_NOT_FOUND", ErrorCode::CONTEXT_KEY_NOT_FOUND)
        .value("CONTEXT_SERIALIZATION_FAILED", ErrorCode::CONTEXT_SERIALIZATION_FAILED)
        // Registry errors
        .value("REGISTRY_DUPLICATE_KEY", ErrorCode::REGISTRY_DUPLICATE_KEY)
        .value("REGISTRY_KEY_NOT_FOUND", ErrorCode::REGISTRY_KEY_NOT_FOUND)
        // Configuration errors
        .value("CONFIG_FILE_NOT_FOUND", ErrorCode::CONFIG_FILE_NOT_FOUND)
        .value("CONFIG_PARSE_ERROR", ErrorCode::CONFIG_PARSE_ERROR)
        // I/O errors
        .value("FILE_NOT_FOUND", ErrorCode::FILE_NOT_FOUND)
        .value("FILE_READ_ERROR", ErrorCode::FILE_READ_ERROR)
        .value("FILE_WRITE_ERROR", ErrorCode::FILE_WRITE_ERROR)
        .value("NETWORK_ERROR", ErrorCode::NETWORK_ERROR)
        // Resource errors
        .value("RESOURCE_EXHAUSTED", ErrorCode::RESOURCE_EXHAUSTED)
        .value("RESOURCE_LOCKED", ErrorCode::RESOURCE_LOCKED)
        .export_values();

    py::enum_<ErrorSeverity>(m, "ErrorSeverity", "Error severity levels")
        .value("LOW", ErrorSeverity::LOW, "Minor issue, can continue")
        .value("MEDIUM", ErrorSeverity::MEDIUM, "Significant issue")
        .value("HIGH", ErrorSeverity::HIGH, "Major issue")
        .value("CRITICAL", ErrorSeverity::CRITICAL, "System-level failure")
        .export_values();

    // Base exception
    py::register_exception<Exception>(m, "VersaAIException");

    py::class_<Exception>(m, "Exception", "Base VersaAI exception")
        .def(py::init<const std::string&, ErrorCode, ErrorSeverity>(),
            py::arg("message"),
            py::arg("code") = ErrorCode::UNKNOWN,
            py::arg("severity") = ErrorSeverity::MEDIUM)
        .def("what", &Exception::what, "Get error message")
        .def("get_error_code", &Exception::getErrorCode, "Get error code")
        .def("get_severity", &Exception::getSeverity, "Get severity level")
        .def("get_timestamp", &Exception::getTimestamp, "Get error timestamp")
        .def("get_context_string", &Exception::getContextString, "Get full error context")
        .def("__str__", &Exception::what)
        .def("__repr__", [](const Exception& e) {
            return "<VersaAI.Exception: " + std::string(e.what()) + ">";
        });

    // ========================================================================
    // ERROR RECOVERY
    // ========================================================================

    py::enum_<RetryStrategy>(m, "RetryStrategy", "Retry strategy types")
        .value("EXPONENTIAL_BACKOFF", RetryStrategy::EXPONENTIAL_BACKOFF)
        .value("LINEAR_BACKOFF", RetryStrategy::LINEAR_BACKOFF)
        .value("FIXED_DELAY", RetryStrategy::FIXED_DELAY)
        .export_values();

    py::class_<RetryConfig>(m, "RetryConfig", "Retry configuration")
        .def(py::init<>())
        .def_readwrite("max_attempts", &RetryConfig::maxAttempts)
        .def_readwrite("base_delay_ms", &RetryConfig::baseDelayMs)
        .def_readwrite("max_delay_ms", &RetryConfig::maxDelayMs)
        .def_readwrite("backoff_multiplier", &RetryConfig::backoffMultiplier)
        .def_readwrite("strategy", &RetryConfig::strategy)
        .def("__repr__", [](const RetryConfig& cfg) {
            std::ostringstream oss;
            oss << "<RetryConfig: max_attempts=" << cfg.maxAttempts
                << ", base_delay=" << cfg.baseDelayMs << "ms>";
            return oss.str();
        });

    // Note: Full ErrorRecovery bindings would require wrapping std::function
    // For MVP, expose configuration types. Full implementation in future iteration.

    // ========================================================================
    // CONTEXT (Session Management)
    // ========================================================================

    // Note: Context v2 bindings would require template specialization
    // For MVP, Logger and Exceptions are sufficient.
    // Context can be managed in Python for now.

    m.def("version_info", []() {
        return py::dict(
            py::arg("version") = "0.2.0",
            py::arg("cpp_standard") = "C++23",
            py::arg("bindings") = "pybind11",
            py::arg("features") = py::list(py::make_tuple("Logger", "Exceptions", "ErrorRecovery"))
        );
    }, "Get version and feature information");
}
