/**
 * @file versaai_bindings_v2.cpp
 * @brief Production-grade Python bindings for VersaAI C++ Core (Corrected APIs)
 * 
 * Exposes:
 * - Logger (async structured logging)
 * - VersaAIContextV2 (hierarchical context with actual API)
 * - Exception hierarchy (error handling)
 * - ErrorRecovery (circuit breaker, retry strategies)
 * 
 * @date 2025-11-18
 * @version 2.0.0
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/functional.h>
#include <pybind11/chrono.h>

// VersaAI C++ Core Headers
#include "VersaAILogger.hpp"
#include "VersaAIContext_v2.hpp"
#include "VersaAIException.hpp"
#include "VersaAIErrorRecovery.hpp"

namespace py = pybind11;
using namespace VersaAI;

// ============================================================================
// Helper: Convert ContextValue to Python object
// ============================================================================

py::object contextValueToPython(const ContextValue& value) {
    return std::visit([](auto&& arg) -> py::object {
        using T = std::decay_t<decltype(arg)>;
        if constexpr (std::is_same_v<T, std::string>) {
            return py::cast(arg);
        } else if constexpr (std::is_same_v<T, int64_t>) {
            return py::cast(arg);
        } else if constexpr (std::is_same_v<T, double>) {
            return py::cast(arg);
        } else if constexpr (std::is_same_v<T, bool>) {
            return py::cast(arg);
        } else if constexpr (std::is_same_v<T, std::vector<std::string>>) {
            return py::cast(arg);
        }
        return py::none();
    }, value);
}

// ============================================================================
// Helper: Convert Python object to ContextValue
// ============================================================================

ContextValue pythonToContextValue(const py::object& obj) {
    if (py::isinstance<py::str>(obj)) {
        return obj.cast<std::string>();
    } else if (py::isinstance<py::int_>(obj)) {
        return obj.cast<int64_t>();
    } else if (py::isinstance<py::float_>(obj)) {
        return obj.cast<double>();
    } else if (py::isinstance<py::bool_>(obj)) {
        return obj.cast<bool>();
    } else if (py::isinstance<py::list>(obj)) {
        return obj.cast<std::vector<std::string>>();
    }
    throw std::runtime_error("Unsupported Python type for ContextValue");
}

// ============================================================================
// MODULE DEFINITION
// ============================================================================

PYBIND11_MODULE(versaai_core, m) {
    m.doc() = R"doc(
        VersaAI C++ Core Bindings (v2.0)
        ================================
        
        Production-grade Python bindings with corrected APIs.
        
        Components:
            - Logger: High-performance async logging
            - ContextV2: Hierarchical context management
            - Exceptions: Comprehensive error handling
            - ErrorRecovery: Circuit breaker and retry patterns
    )doc";

    // ========================================================================
    // LOGGING
    // ========================================================================

    py::enum_<LogLevel>(m, "LogLevel", "Logging severity levels")
        .value("TRACE", LogLevel::TRACE)
        .value("DEBUG", LogLevel::DEBUG)
        .value("INFO", LogLevel::INFO)
        .value("WARNING", LogLevel::WARNING)
        .value("ERROR", LogLevel::ERROR)
        .value("CRITICAL", LogLevel::CRITICAL)
        .export_values();

    py::class_<Logger, std::unique_ptr<Logger, py::nodelete>>(m, "Logger",
        "High-performance structured logger (singleton)")
        
        .def_static("get_instance", &Logger::getInstance,
                   py::return_value_policy::reference,
                   "Get the singleton Logger instance")

        .def("trace", [](Logger& self, const std::string& message, const std::string& component) {
                 self.trace(message, component);
             }, py::arg("message"), py::arg("component") = "Python")

        .def("debug", [](Logger& self, const std::string& message, const std::string& component) {
                 self.debug(message, component);
             }, py::arg("message"), py::arg("component") = "Python")

        .def("info", [](Logger& self, const std::string& message, const std::string& component) {
                 self.info(message, component);
             }, py::arg("message"), py::arg("component") = "Python")

        .def("warning", [](Logger& self, const std::string& message, const std::string& component) {
                 self.warning(message, component);
             }, py::arg("message"), py::arg("component") = "Python")

        .def("error", [](Logger& self, const std::string& message, const std::string& component) {
                 self.error(message, component);
             }, py::arg("message"), py::arg("component") = "Python")

        .def("critical", [](Logger& self, const std::string& message, const std::string& component) {
                 self.critical(message, component);
             }, py::arg("message"), py::arg("component") = "Python")

        .def("flush", &Logger::flush, "Flush pending log messages");

    // ========================================================================
    // CONTEXT SYSTEM (Corrected API)
    // ========================================================================

    py::class_<ContextMetadata>(m, "ContextMetadata", "Metadata for context entries")
        .def(py::init<>())
        .def_readwrite("access_count", &ContextMetadata::accessCount)
        .def_readwrite("description", &ContextMetadata::description)
        .def_readwrite("persistent", &ContextMetadata::persistent)
        .def_readonly("created", &ContextMetadata::created)
        .def_readonly("last_accessed", &ContextMetadata::lastAccessed)
        .def_readonly("last_modified", &ContextMetadata::lastModified);

    py::class_<VersaAIContextV2>(m, "ContextV2",
        R"doc(
            Hierarchical context management with versioning.
            
            Features:
                - Namespace support
                - Snapshot and rollback
                - Thread-safe operations
                - JSON/binary serialization
            
            Example:
                >>> ctx = ContextV2()
                >>> ctx.set("user_id", 12345)
                >>> ctx.set("theme", "dark", namespace="preferences")
                >>> snapshot = ctx.create_snapshot()
                >>> ctx.rollback_to_snapshot(snapshot)
        )doc")
        
        .def(py::init<>())

        // Core operations (CORRECTED METHOD NAMES)
        .def("set",
             [](VersaAIContextV2& self, const std::string& key, py::object value,
                const std::string& namespace_path, bool persistent) {
                 self.set(key, pythonToContextValue(value), namespace_path, persistent);
             },
             py::arg("key"),
             py::arg("value"),
             py::arg("namespace") = "",
             py::arg("persistent") = false,
             "Set a value in the context")

        .def("get",
             [](VersaAIContextV2& self, const std::string& key, 
                const std::string& namespace_path) -> py::object {
                 auto opt = self.get(key, namespace_path);
                 if (opt.has_value()) {
                     return contextValueToPython(opt.value());
                 }
                 return py::none();
             },
             py::arg("key"),
             py::arg("namespace") = "",
             "Get a value from the context")

        .def("exists",  // CORRECTED: was "has"
             &VersaAIContextV2::exists,
             py::arg("key"),
             py::arg("namespace") = "",
             "Check if a key exists")

        .def("remove",
             &VersaAIContextV2::remove,
             py::arg("key"),
             py::arg("namespace") = "",
             "Remove a key")

        .def("clear",
             &VersaAIContextV2::clear,
             "Clear all non-persistent values")

        .def("clear_all",  // Additional method
             &VersaAIContextV2::clearAll,
             "Clear all values including persistent ones")

        // Namespace operations
        .def("get_keys_in_namespace",  // CORRECTED: was "getNamespaceKeys"
             &VersaAIContextV2::getKeysInNamespace,
             py::arg("namespace") = "",
             "Get all keys in a namespace")

        // Snapshot operations (CORRECTED)
        .def("create_snapshot",
             &VersaAIContextV2::createSnapshot,
             "Create a snapshot, returns snapshot ID")

        .def("rollback_to_snapshot",  // CORRECTED: was "restoreSnapshot"
             &VersaAIContextV2::rollbackToSnapshot,
             py::arg("snapshot_id"),
             "Rollback to a previous snapshot")

        // Serialization (CORRECTED METHOD NAMES)
        .def("serialize_to_json",  // CORRECTED: was "toJSON"
             &VersaAIContextV2::serializeToJson,
             "Serialize context to JSON string")

        .def("deserialize_from_json",  // CORRECTED: was "fromJSON"
             &VersaAIContextV2::deserializeFromJson,
             py::arg("json_str"),
             "Deserialize context from JSON string")

        .def("serialize_to_binary",
             &VersaAIContextV2::serializeToBinary,
             "Serialize to binary format")

        .def("deserialize_from_binary",
             &VersaAIContextV2::deserializeFromBinary,
             py::arg("data"),
             "Deserialize from binary format")

        // Metadata
        .def("get_metadata",
             [](VersaAIContextV2& self, const std::string& key, 
                const std::string& namespace_path) -> py::object {
                 auto opt = self.getMetadata(key, namespace_path);
                 if (opt.has_value()) {
                     return py::cast(opt.value());
                 }
                 return py::none();
             },
             py::arg("key"),
             py::arg("namespace") = "",
             "Get metadata for a key");

    // ========================================================================
    // EXCEPTION SYSTEM
    // ========================================================================

    py::enum_<ErrorSeverity>(m, "ErrorSeverity")
        .value("LOW", ErrorSeverity::LOW)
        .value("MEDIUM", ErrorSeverity::MEDIUM)
        .value("HIGH", ErrorSeverity::HIGH)
        .value("CRITICAL", ErrorSeverity::CRITICAL)
        .export_values();

    py::enum_<ErrorCode>(m, "ErrorCode")
        .value("UNKNOWN", ErrorCode::UNKNOWN)
        .value("INVALID_ARGUMENT", ErrorCode::INVALID_ARGUMENT)
        .value("MODEL_NOT_FOUND", ErrorCode::MODEL_NOT_FOUND)
        .value("MODEL_LOAD_FAILED", ErrorCode::MODEL_LOAD_FAILED)
        .value("AGENT_NOT_REGISTERED", ErrorCode::AGENT_NOT_REGISTERED)
        .value("AGENT_TASK_FAILED", ErrorCode::AGENT_TASK_FAILED)
        .value("CONTEXT_KEY_NOT_FOUND", ErrorCode::CONTEXT_KEY_NOT_FOUND)
        .value("FILE_NOT_FOUND", ErrorCode::FILE_NOT_FOUND)
        .value("RESOURCE_EXHAUSTED", ErrorCode::RESOURCE_EXHAUSTED)
        .export_values();

    // Register VersaAI exceptions as Python exceptions
    static py::exception<Exception> exc_base(m, "VersaAIException");
    static py::exception<ModelException> exc_model(m, "ModelException", exc_base.ptr());
    static py::exception<AgentException> exc_agent(m, "AgentException", exc_base.ptr());
    static py::exception<ContextException> exc_context(m, "ContextException", exc_base.ptr());

    py::register_exception_translator([](std::exception_ptr p) {
        try {
            if (p) std::rethrow_exception(p);
        } catch (const ModelException& e) {
            PyErr_SetString(PyExc_RuntimeError, e.what());
        } catch (const AgentException& e) {
            PyErr_SetString(PyExc_RuntimeError, e.what());
        } catch (const ContextException& e) {
            PyErr_SetString(PyExc_RuntimeError, e.what());
        } catch (const Exception& e) {
            PyErr_SetString(PyExc_RuntimeError, e.what());
        }
    });

    // ========================================================================
    // ERROR RECOVERY (Corrected API)
    // ========================================================================

    // RetryStrategy::Config
    py::class_<RetryStrategy::Config>(m, "RetryConfig")
        .def(py::init<>())
        .def_readwrite("max_retries", &RetryStrategy::Config::maxRetries)
        .def_readwrite("initial_delay", &RetryStrategy::Config::initialDelay)
        .def_readwrite("max_delay", &RetryStrategy::Config::maxDelay)
        .def_readwrite("backoff_multiplier", &RetryStrategy::Config::backoffMultiplier)
        .def_readwrite("reset_on_success", &RetryStrategy::Config::resetOnSuccess);

    // CircuitBreaker::Config
    py::class_<CircuitBreaker::Config>(m, "CircuitBreakerConfig")
        .def(py::init<>())
        .def_readwrite("failure_threshold", &CircuitBreaker::Config::failureThreshold)
        .def_readwrite("open_timeout", &CircuitBreaker::Config::openTimeout)
        .def_readwrite("half_open_successes", &CircuitBreaker::Config::halfOpenSuccesses)
        .def_readwrite("call_timeout", &CircuitBreaker::Config::callTimeout);

    // CircuitState enum
    py::enum_<CircuitState>(m, "CircuitState")
        .value("CLOSED", CircuitState::CLOSED)
        .value("OPEN", CircuitState::OPEN)
        .value("HALF_OPEN", CircuitState::HALF_OPEN)
        .export_values();

    // CircuitBreaker class
    py::class_<CircuitBreaker, std::shared_ptr<CircuitBreaker>>(m, "CircuitBreaker")
        .def(py::init<const std::string&>(),
             py::arg("name"))

        .def(py::init<const std::string&, const CircuitBreaker::Config&>(),
             py::arg("name"),
             py::arg("config"))

        .def("get_state", &CircuitBreaker::getState)
        .def("get_failure_count", &CircuitBreaker::getFailureCount)
        .def("get_success_count", &CircuitBreaker::getSuccessCount)
        .def("get_name", &CircuitBreaker::getName)
        .def("reset", &CircuitBreaker::reset)
        .def("trip", &CircuitBreaker::trip);

    // CircuitBreakerRegistry
    py::class_<CircuitBreakerRegistry>(m, "CircuitBreakerRegistry")
        .def_static("get_instance", &CircuitBreakerRegistry::getInstance,
                   py::return_value_policy::reference)
        
        .def("get_or_create",
             py::overload_cast<const std::string&>(&CircuitBreakerRegistry::getOrCreate),
             py::arg("name"))
        
        .def("get_or_create",
             py::overload_cast<const std::string&, const CircuitBreaker::Config&>(
                 &CircuitBreakerRegistry::getOrCreate),
             py::arg("name"),
             py::arg("config"))
        
        .def("get", &CircuitBreakerRegistry::get,
             py::arg("name"))
        
        .def("remove", &CircuitBreakerRegistry::remove,
             py::arg("name"))
        
        .def("get_all_names",  // CORRECTED: actual method name
             &CircuitBreakerRegistry::getAllNames);

    // ========================================================================
    // UTILITIES
    // ========================================================================

    m.def("get_default_retry_config",
          []() -> RetryStrategy::Config {
              return RetryStrategy::Config();
          });

    m.def("get_default_circuit_breaker_config",
          []() -> CircuitBreaker::Config {
              return CircuitBreaker::Config();
          });

    // ========================================================================
    // VERSION INFO
    // ========================================================================

    m.attr("__version__") = "2.0.0";
    m.attr("__cpp_standard__") = "C++23";
    m.attr("__build_date__") = __DATE__ " " __TIME__;
    
    m.def("version_info", []() -> py::dict {
        py::dict info;
        info["version"] = "2.0.0";
        info["cpp_standard"] = "C++23";
        info["components"] = py::make_tuple(
            "Logger", "ContextV2", "Exceptions", "ErrorRecovery"
        );
        info["api_corrections"] = py::make_tuple(
            "has() -> exists()",
            "toJSON() -> serialize_to_json()",
            "fromJSON() -> deserialize_from_json()",
            "restoreSnapshot() -> rollback_to_snapshot()"
        );
        return info;
    });
}
