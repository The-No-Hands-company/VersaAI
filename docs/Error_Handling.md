# VersaAI Error Handling Framework

## Overview

VersaAI implements a production-grade error handling framework with rich exception hierarchies, automatic logging, recovery strategies, and circuit breakers for fault tolerance.

**Status:** ✅ Production-ready (Phase 1.3 Complete)

## Architecture

### Core Components

1. **Exception Hierarchy** (`VersaAI::Exception`)
   - Base exception class with error codes, severity levels, and context
   - Domain-specific exceptions (Model, Agent, Context, Registry, Config, IO, Resource)
   - Stack trace capture (GNU platforms)
   - Exception chaining for cause tracking

2. **Error Codes** (`VersaAI::ErrorCode`)
   - Categorized error codes (0-99: Generic, 100-199: Model, 200-299: Agent, etc.)
   - Human-readable error code strings
   - Enables programmatic error handling

3. **Error Severity** (`VersaAI::ErrorSeverity`)
   - LOW: Minor issues, can continue
   - MEDIUM: Significant issues, degraded functionality
   - HIGH: Major issues, feature unavailable
   - CRITICAL: System-level failure, cannot continue

4. **Recovery Strategies**
   - **RetryStrategy**: Exponential backoff with configurable attempts
   - **FallbackStrategy**: Primary operation with fallback
   - **CircuitBreaker**: Fail-fast pattern for cascading failures

5. **Automatic Logging**
   - All exceptions logged through `VersaAI::Logger`
   - Stack traces for HIGH/CRITICAL severity
   - Context data preserved in logs

## Exception Hierarchy

```
std::exception
    └── VersaAI::Exception (base)
            ├── ModelException
            ├── AgentException
            ├── ContextException
            ├── RegistryException
            ├── ConfigException
            ├── IOException
            └── ResourceException
```

## Usage Examples

### Basic Exception Throwing

```cpp
#include "VersaAIException.hpp"

// Throw with message and error code
throw VersaAI::Exception(
    "Operation failed",
    VersaAI::ErrorCode::INVALID_ARGUMENT
);

// Domain-specific exception with context
throw VersaAI::ModelException(
    "Failed to load model",
    VersaAI::ErrorCode::MODEL_LOAD_FAILED
).setModelName("gpt-model")
 .setModelPath("/models/gpt.gguf")
 .addContext("file_size", "3.5GB");
```

### Catching and Handling Exceptions

```cpp
try {
    auto result = riskyOperation();
} catch (const VersaAI::ModelException& ex) {
    std::cerr << "Model error: " << ex.getMessage() << std::endl;
    std::cerr << "Error code: " << VersaAI::errorCodeToString(ex.getErrorCode()) << std::endl;
    
    // Check severity
    if (ex.getSeverity() >= VersaAI::ErrorSeverity::HIGH) {
        // Take remedial action
        loadFallbackModel();
    }
    
} catch (const VersaAI::Exception& ex) {
    // Generic VersaAI exception
    VersaAI::logException(ex, "Caught in main handler");
    
} catch (const std::exception& ex) {
    std::cerr << "Standard exception: " << ex.what() << std::endl;
}
```

### Structured Exception with Context

```cpp
VersaAI::AgentException ex(
    "Agent task failed",
    VersaAI::ErrorCode::AGENT_TASK_FAILED
);

ex.setAgentName("ModelingAgent")
  .setTaskDescription("Generate 3D model from description")
  .addContext("input_length", "256")
  .addContext("timeout_ms", "5000")
  .addContext("retry_count", "3");

throw ex;
```

### Exception Chaining

```cpp
try {
    loadDatabase();
} catch (const std::exception& cause) {
    throw VersaAI::IOException(
        "Failed to initialize system",
        VersaAI::ErrorCode::FILE_READ_ERROR,
        VersaAI::ErrorSeverity::CRITICAL,
        std::current_exception()  // Chain the cause
    ).setFilePath("/data/db.sqlite");
}
```

## Recovery Strategies

### Retry with Exponential Backoff

```cpp
#include "VersaAIErrorRecovery.hpp"

VersaAI::RetryStrategy::Config config;
config.maxRetries = 5;
config.initialDelay = std::chrono::milliseconds(100);
config.backoffMultiplier = 2.0;
config.maxDelay = std::chrono::milliseconds(5000);

VersaAI::RetryStrategy retry(config);

bool success = retry.execute([&]() {
    connectToServer();  // May throw
});

if (!success) {
    std::cerr << "Failed after retries: " << retry.getLastError().value() << std::endl;
}

// Or using convenience function
auto result = VersaAI::withRetry([]() {
    return fetchData();
}, config);
```

### Fallback Strategy

```cpp
VersaAI::FallbackStrategy fallback(
    []() { return loadCachedData(); },
    "cached_data_fallback"
);

bool success = fallback.execute([&]() {
    fetchFromNetwork();  // May throw
});

if (fallback.didFallback()) {
    std::cout << "Used fallback" << std::endl;
}

// Or using convenience function
auto data = VersaAI::withFallback(
    []() { return fetchFromNetwork(); },
    []() { return loadCachedData(); }
);
```

### Circuit Breaker

```cpp
#include "VersaAIErrorRecovery.hpp"

// Get or create circuit breaker
VersaAI::CircuitBreaker::Config config;
config.failureThreshold = 5;          // Open after 5 failures
config.openTimeout = std::chrono::seconds(30);
config.halfOpenSuccesses = 2;         // Close after 2 successes

auto breaker = VersaAI::CircuitBreakerRegistry::getInstance()
    .getOrCreate("external_api", config);

// Use circuit breaker
try {
    auto result = breaker->call([&]() {
        return callExternalAPI();
    });
} catch (const VersaAI::ResourceException& ex) {
    if (ex.getErrorCode() == VersaAI::ErrorCode::RESOURCE_UNAVAILABLE) {
        std::cerr << "Circuit breaker is OPEN" << std::endl;
    }
}

// Or using convenience function
auto result = VersaAI::withCircuitBreaker("external_api", [&]() {
    return callExternalAPI();
});

// Circuit breaker states
std::cout << "State: " << static_cast<int>(breaker->getState()) << std::endl;
std::cout << "Failures: " << breaker->getFailureCount() << std::endl;

// Manual control
breaker->reset();  // Force close
breaker->trip();   // Force open
```

## Error Codes

### Generic Errors (0-99)
- `UNKNOWN = 0`
- `INVALID_ARGUMENT = 1`
- `NULL_POINTER = 2`
- `OUT_OF_RANGE = 3`
- `INVALID_STATE = 4`

### Model Errors (100-199)
- `MODEL_NOT_FOUND = 100`
- `MODEL_LOAD_FAILED = 101`
- `MODEL_INVALID_FORMAT = 102`
- `MODEL_INFERENCE_FAILED = 103`
- `MODEL_OUT_OF_MEMORY = 104`

### Agent Errors (200-299)
- `AGENT_NOT_REGISTERED = 200`
- `AGENT_INITIALIZATION_FAILED = 201`
- `AGENT_TASK_FAILED = 202`
- `AGENT_TIMEOUT = 203`

### Context Errors (300-399)
- `CONTEXT_KEY_NOT_FOUND = 300`
- `CONTEXT_SERIALIZATION_FAILED = 301`
- `CONTEXT_DESERIALIZATION_FAILED = 302`
- `CONTEXT_VERSION_MISMATCH = 303`

### Registry Errors (400-499)
- `REGISTRY_DUPLICATE_KEY = 400`
- `REGISTRY_KEY_NOT_FOUND = 401`
- `REGISTRY_INVALID_TYPE = 402`

### Configuration Errors (500-599)
- `CONFIG_FILE_NOT_FOUND = 500`
- `CONFIG_PARSE_ERROR = 501`
- `CONFIG_INVALID_VALUE = 502`

### I/O Errors (600-699)
- `FILE_NOT_FOUND = 600`
- `FILE_READ_ERROR = 601`
- `FILE_WRITE_ERROR = 602`
- `NETWORK_ERROR = 603`

### Resource Errors (700-799)
- `RESOURCE_EXHAUSTED = 700`
- `RESOURCE_LOCKED = 701`
- `RESOURCE_UNAVAILABLE = 702`

## Integration with VersaAICore

VersaAICore now throws exceptions instead of returning error strings:

```cpp
// Before (return-value error handling)
std::string response = core.processInput(appName, input);
if (response == "[No chatbot registered for this app.]") {
    // Handle error
}

// After (exception-based error handling)
try {
    std::string response = core.processInput(appName, input);
    std::cout << response << std::endl;
} catch (const VersaAI::RegistryException& ex) {
    std::cerr << "Chatbot not found: " << ex.getMessage() << std::endl;
}
```

## Automatic Logging

All exceptions are automatically logged through `VersaAI::Logger`:

```cpp
try {
    throw VersaAI::ModelException(
        "Model load failed",
        VersaAI::ErrorCode::MODEL_LOAD_FAILED
    ).setModelPath("/models/gpt.gguf");
    
} catch (const VersaAI::Exception& ex) {
    VersaAI::logException(ex, "Model initialization");
    // Logs to console and file with full context
}
```

Log output:
```
2025-11-14 01:00:00.123 [CRITICAL] [Model] [12345] Model load failed {error_code=MODEL_LOAD_FAILED, model_path=/models/gpt.gguf, severity=HIGH}
```

## Best Practices

### 1. Use Domain-Specific Exceptions

```cpp
// Good
throw VersaAI::ModelException("Load failed")
    .setModelName("gpt-3.5")
    .setModelPath("/models/gpt3.5.bin");

// Avoid
throw VersaAI::Exception("Model load failed");
```

### 2. Add Context to Exceptions

```cpp
throw VersaAI::AgentException("Task timeout")
    .setAgentName("ResearchAgent")
    .setTaskDescription("Web search")
    .addContext("timeout_ms", "30000")
    .addContext("url", "https://example.com");
```

### 3. Use Appropriate Severity Levels

```cpp
// LOW: Recoverable, minor issues
throw VersaAI::ContextException("Key not found", ErrorCode::CONTEXT_KEY_NOT_FOUND);

// MEDIUM: Significant, degraded functionality
throw VersaAI::AgentException("Task failed", ErrorCode::AGENT_TASK_FAILED);

// HIGH: Major, feature unavailable
throw VersaAI::ModelException("Model load failed", ErrorCode::MODEL_LOAD_FAILED);

// CRITICAL: System failure
throw VersaAI::ResourceException("Out of memory", ErrorCode::RESOURCE_EXHAUSTED);
```

### 4. Use Circuit Breakers for External Calls

```cpp
// Protect against cascading failures
auto apiBreaker = CircuitBreakerRegistry::getInstance()
    .getOrCreate("external_api");

for (auto& request : requests) {
    try {
        apiBreaker->call([&]() {
            sendRequest(request);
        });
    } catch (const ResourceException& ex) {
        // Circuit open, skip remaining requests
        break;
    }
}
```

### 5. Use Retry for Transient Failures

```cpp
RetryStrategy::Config config;
config.maxRetries = 3;
config.initialDelay = std::chrono::milliseconds(1000);

auto data = withRetry([&]() {
    return fetchFromNetwork();  // May fail transiently
}, config);
```

## Files

- **Headers:**
  - `include/VersaAIException.hpp` (Exception classes, error codes)
  - `include/VersaAIErrorRecovery.hpp` (Recovery strategies, circuit breakers)
  
- **Implementation:**
  - `src/core/VersaAIException.cpp` (Exception implementation, stack traces)
  - `src/core/VersaAIErrorRecovery.cpp` (Retry, fallback, circuit breaker logic)

- **Integration:**
  - `src/core/VersaAICore.cpp` (Uses exceptions in processInput)
  - `src/core/main.cpp` (Catches and handles exceptions)

## Performance Characteristics

- **Exception throwing:** ~1-10 microseconds overhead
- **Stack trace capture:** ~50-100 microseconds (GNU platforms only)
- **Retry overhead:** Configurable backoff delays (100ms - 5s default)
- **Circuit breaker overhead:** Sub-microsecond state check
- **Memory:** ~1-2KB per exception object

## Advanced Features

### Custom Exception Formatting

```cpp
VersaAI::Exception ex("Error occurred");
ex.addContext("user_id", "12345");
ex.addContext("session", "abc-def-ghi");

std::string formatted = ex.format();
// Returns multi-line detailed format with timestamp, context, stack trace
```

### Exception Rethrowing with Context

```cpp
try {
    processData();
} catch (...) {
    VersaAI::rethrowWithContext<VersaAI::AgentException>(
        "Data processing failed",
        {{"data_size", "1024"}, {"format", "JSON"}}
    );
}
```

### Circuit Breaker Registry Management

```cpp
auto& registry = CircuitBreakerRegistry::getInstance();

// Get all breakers
auto names = registry.getAllNames();

// Reset all breakers
registry.resetAll();

// Remove specific breaker
registry.remove("old_api");
```

## Future Enhancements (Phase 2+)

- [ ] Custom exception handlers per component
- [ ] Exception aggregation and reporting
- [ ] Metrics collection (exception rates, recovery success rates)
- [ ] Distributed tracing integration
- [ ] Exception serialization for remote logging
- [ ] Adaptive circuit breaker thresholds
- [ ] Bulkhead pattern for resource isolation

## Troubleshooting

### Problem: No stack traces captured

**Solution:** Stack traces only available on GNU platforms (Linux, macOS with GCC/Clang). On other platforms, `getStackTrace()` returns empty vector.

### Problem: Exception not logged

**Solution:** Ensure `VersaAI::logException()` is called in catch blocks, or exceptions are allowed to propagate to a handler that logs them.

### Problem: Circuit breaker won't close

**Solution:** Check `halfOpenSuccesses` configuration. Circuit requires consecutive successes in HALF_OPEN state to transition to CLOSED.

### Problem: Retry exhausted too quickly

**Solution:** Increase `maxRetries` and adjust `backoffMultiplier` for longer retry windows.

## License & Attribution

Part of VersaAI ecosystem. See root LICENSE for details.

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-14  
**Phase:** 1.3 Complete
