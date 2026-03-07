# VersaAI C++/Python Bindings

This directory contains pybind11 bindings that expose VersaAI's C++ core infrastructure to Python.

## Overview

The `versaai_core` module provides Python access to:

- **Logger**: High-performance structured logging
- **Exceptions**: Hierarchical error handling with error codes
- **ErrorRecovery**: Retry policies and circuit breakers
- **Context**: Session state management

## Building

### Prerequisites

```bash
# Install pybind11
uv pip install pybind11

# Or via system package manager
sudo apt install pybind11-dev  # Debian/Ubuntu
```

### Build Steps

```bash
# 1. Build main VersaAI C++ project first
cd /path/to/VersaAI
./scripts/build.sh

# 2. Build bindings
cd bindings
mkdir build && cd build
cmake .. -G Ninja
ninja

# 3. Bindings will be installed to versaai/versaai_core.so
```

## Usage Examples

### Logging from Python

```python
from versaai_core import Logger, LogLevel

# Get singleton logger
logger = Logger.get_instance()

# Set log level
logger.set_level(LogLevel.DEBUG)

# Log messages
logger.debug("Detailed debug info", "MyPythonModule")
logger.info("Informational message", "MyPythonModule")
logger.warning("Warning message", "MyPythonModule")
logger.error("Error occurred", "MyPythonModule")
logger.critical("Critical failure!", "MyPythonModule")
```

### Exception Handling

```python
from versaai_core import (
    VersaAIException,
    ModelException,
    InvalidArgumentException,
    ResourceException,
    ErrorCode
)

try:
    # Your code here
    raise ModelException("Model not found")
except ModelException as e:
    logger.error(f"Model error: {e}", "Python")
except VersaAIException as e:
    logger.error(f"General error: {e}", "Python")
```

### Error Recovery

```python
from versaai_core import (
    RetryPolicy,
    CircuitBreaker,
    CircuitBreakerConfig,
    ErrorRecoveryManager
)
import time

# Create retry policy
retry_policy = RetryPolicy(
    max_attempts=3,
    initial_delay=100,  # milliseconds
    max_delay=5000,
    backoff_multiplier=2.0
)

# Create circuit breaker
cb_config = CircuitBreakerConfig(
    failure_threshold=5,
    timeout_duration=60,  # seconds
    success_rate_threshold=0.5
)

recovery_manager = ErrorRecoveryManager.get_instance()
recovery_manager.register_circuit_breaker("api_calls", cb_config)
breaker = recovery_manager.get_circuit_breaker("api_calls")

# Use circuit breaker
if not breaker.is_open():
    try:
        # Make API call
        result = make_api_call()
        breaker.record_success()
    except Exception as e:
        breaker.record_failure()
        logger.error(f"API call failed: {e}", "APIClient")
else:
    logger.warning("Circuit breaker is open, skipping call", "APIClient")
```

### Context Management

```python
from versaai_core import Context

# Create context
ctx = Context()

# Store session data
ctx.set("user_id", "12345")
ctx.set("session_token", "abc-def-ghi")

# Retrieve data
if ctx.has("user_id"):
    user_id = ctx.get("user_id")
    print(f"User ID: {user_id}")

# Clear context
ctx.clear()
```

## Integration with Python Code

### Using C++ Logger in Python Agents

```python
from versaai_core import Logger
from versaai.models import ModelRegistry

class MyAgent:
    def __init__(self):
        # Use C++ logger for performance
        self.logger = Logger.get_instance()
        self.model = ModelRegistry.load("gpt2")
    
    def process(self, query: str) -> str:
        self.logger.info(f"Processing query: {query}", "MyAgent")
        
        try:
            result = self.model.generate(query)
            self.logger.info(f"Generated {len(result)} chars", "MyAgent")
            return result
        except Exception as e:
            self.logger.error(f"Generation failed: {e}", "MyAgent")
            raise
```

### Error Recovery Decorators

```python
from functools import wraps
from versaai_core import Logger, CircuitBreaker, CircuitBreakerConfig

logger = Logger.get_instance()

def with_circuit_breaker(name: str):
    """Decorator to protect functions with circuit breaker."""
    def decorator(func):
        # Create circuit breaker for this function
        breaker = CircuitBreaker(name, CircuitBreakerConfig())
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            if breaker.is_open():
                logger.warning(f"Circuit open for {name}", "CircuitBreaker")
                raise RuntimeError(f"Circuit breaker {name} is open")
            
            try:
                result = func(*args, **kwargs)
                breaker.record_success()
                return result
            except Exception as e:
                breaker.record_failure()
                logger.error(f"Function {name} failed: {e}", "CircuitBreaker")
                raise
        
        return wrapper
    return decorator

# Usage
@with_circuit_breaker("external_api")
def call_external_api(url: str):
    # Make API call
    pass
```

## Architecture

### C++ → Python Mapping

| C++ Type | Python Type | Notes |
|----------|-------------|-------|
| `Logger` | `Logger` | Singleton, reference semantics |
| `VersaAIException` | `VersaAIException` | Inherits from `RuntimeError` |
| `RetryPolicy` | `RetryPolicy` | Value semantics, copy on return |
| `CircuitBreaker` | `CircuitBreaker` | Reference semantics |
| `VersaAIContext` | `Context` | Value semantics |
| `std::string` | `str` | Automatic conversion |
| `std::chrono::milliseconds` | `int` (milliseconds) | Converted to int |

### Thread Safety

All C++ components exposed to Python maintain their original thread safety guarantees:

- **Logger**: Thread-safe (uses mutex)
- **CircuitBreaker**: Thread-safe (uses atomic operations)
- **Context**: NOT thread-safe (use one per thread or add locking)

### Performance Considerations

- **Logger**: C++ logger has minimal overhead (~100ns per call)
- **Exceptions**: Throwing from C++ to Python adds ~1-2μs overhead
- **Context**: HashMap lookups are O(1)
- **Circuit Breaker**: Lock-free atomic operations

## Troubleshooting

### Import Error: versaai_core not found

```bash
# Ensure bindings are built and installed
cd bindings/build
ninja install

# Check if .so file exists
ls -la ../../versaai/versaai_core*.so
```

### Symbol Not Found Errors

```bash
# Rebuild main project first
cd ../..
./scripts/build.sh

# Then rebuild bindings
cd bindings/build
ninja clean
ninja
```

### Version Mismatch

```python
import versaai_core
print(versaai_core.__version__)  # Should be 0.1.0
print(versaai_core.__cpp_version__)  # Should be C++23
```

## Development

### Adding New Bindings

1. Add C++ implementation to `src/core/`
2. Add binding code to `versaai_core.cpp`
3. Rebuild: `ninja` in `bindings/build/`
4. Test in Python

### Testing Bindings

```bash
# Run Python tests
cd /path/to/VersaAI
pytest tests/test_bindings.py -v
```

## References

- [pybind11 Documentation](https://pybind11.readthedocs.io/)
- [VersaAI Architecture](../docs/Architecture_Hybrid.md)
- [C++ Core Documentation](../docs/)
