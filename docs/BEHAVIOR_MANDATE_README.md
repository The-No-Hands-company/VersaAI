# AI Behavior Mandate Integration

> **Production-Grade AI Responses by Default**

## Overview

The AI Behavior Mandate is now fully integrated into VersaAI's core architecture. This means **every development-related interaction automatically enforces expert-level, production-grade standards** as defined in `.github/AI_BEHAVIOR_MANDATE.md`.

## Quick Start

### For Users

When you ask VersaAI to implement something, you automatically get:

✅ Complete implementations (no placeholders or TODOs)  
✅ Comprehensive error handling (all edge cases)  
✅ Full documentation (with examples)  
✅ Optimal algorithms (performance-focused)  
✅ Production-ready code (ship immediately)  

**Example:**
```
You: "Create a cache manager"

VersaAI: [Provides complete production-grade implementation with:]
         - Thread-safe operations
         - TTL support
         - LRU eviction
         - Comprehensive error handling
         - Full documentation
         - 200+ lines of production code
```

### Exception Keywords

Want a simplified version? Use these phrases:
- "Give me a quick prototype"
- "Just a minimal example"  
- "Simplified version for learning"

### For Developers

```cpp
#include "agents/DevelopmentAgent.hpp"
#include "BehaviorPolicy.hpp"

// Create development agent (automatically enforces mandate)
DevelopmentAgent agent;

// Process request
std::string response = agent.performTask("Implement a data processor");

// Response is validated for:
// - No placeholders or TODOs
// - Comprehensive error handling
// - Complete documentation
// - Production quality
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      VersaAICore                            │
│  - Loads AI_BEHAVIOR_MANDATE.md on startup                  │
│  - Registers DevelopmentAgent with mandate enforcement      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    BehaviorPolicy (Singleton)                │
│  - Detects violations (placeholders, TODOs, simplifications) │
│  - Validates code quality (error handling, documentation)    │
│  - Generates system prompts with mandate                     │
│  - Calculates quality scores (0-100)                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                       AgentBase                              │
│  - Augments user input with mandate reminders               │
│  - Validates all responses                                   │
│  - Attempts self-correction                                  │
│  - Adds quality warnings                                     │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│               DevelopmentAgent (Specialized)                 │
│  - Handles code generation                                   │
│  - Classifies tasks (implementation, refactoring, etc.)      │
│  - Double validates code blocks                              │
│  - Strictest enforcement                                     │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. BehaviorPolicy

**Location:** `include/BehaviorPolicy.hpp`, `src/core/BehaviorPolicy.cpp`

**Responsibilities:**
- Load and parse AI_BEHAVIOR_MANDATE.md
- Detect forbidden patterns
- Validate code quality
- Calculate quality scores
- Generate system prompts

**API:**
```cpp
auto& policy = VersaAI::BehaviorPolicy::getInstance();

// Validate code
auto result = policy.validateCode(code, "cpp");

// Check quality
if (result.quality_score >= 90.0 && result.is_compliant) {
  // Production ready!
}

// Generate system prompt with mandate
std::string prompt = policy.generateSystemPrompt("engineer", "implementing feature");
```

### 2. Enhanced AgentBase

**Location:** `src/agents/AgentBase.hpp`

**Features:**
- Automatic input augmentation
- Response validation
- Self-correction
- Quality warnings

**Usage:**
```cpp
class MyAgent : public AgentBase {
protected:
  std::string executeTask(const std::string& input) override {
    // Your logic here - will be automatically validated
    return yourImplementation(input);
  }
  
  std::string getTaskContext() const override {
    return "code";  // or "design", "documentation"
  }
};
```

### 3. DevelopmentAgent

**Location:** `src/agents/DevelopmentAgent.hpp`

**Handles:**
- Implementation requests
- Refactoring tasks
- Bug fixes (root cause only)
- Architecture design

**Features:**
- Task classification
- Strictest enforcement
- Code block validation
- Context-aware responses

## Violation Detection

### CRITICAL (Auto-Reject)
```cpp
// TODO: implement later          ❌
// placeholder                    ❌
void process() { }                ❌ (empty)
return 0;  // stub                ❌
```

### HIGH (Strongly Discouraged)
```
"Let's start simple..."           ❌
"For now, we can just..."         ❌
"Quick fix / workaround"          ❌
"MVP approach"                    ❌
```

### MEDIUM (Warning)
```cpp
// Missing documentation          ⚠️
void process() {                  ⚠️
  // No error handling
}
```

### ALLOWED (Production-Grade)
```cpp
/**
 * @brief Processes data with error handling
 * @param data Input data
 * @throws std::invalid_argument if data invalid
 */
void process(const Data& data) {
  if (!data.isValid()) {
    throw std::invalid_argument("Invalid data");
  }
  
  try {
    // Process with proper error handling
    performProcessing(data);
  } catch (const std::exception& e) {
    logger_->error("Processing failed: {}", e.what());
    throw;
  }
}
```

## Quality Scoring

**Score Calculation:**
- Start at 100.0
- CRITICAL violation: -30 points
- HIGH violation: -15 points
- MEDIUM violation: -7.5 points
- LOW violation: -2.5 points

**Thresholds:**
- **90-100:** Production-ready ✅
- **70-89:** Good, minor improvements
- **50-69:** Needs work
- **<50:** Not production-ready ❌

## Testing

Run the test suite:

```bash
cd build
./tests/test_behavior_mandate
```

Run integration examples:

```bash
./examples/mandate_integration_example
```

**Expected Output:**
```
=== AI Behavior Mandate Enforcement Test Suite ===

Testing BehaviorPolicy initialization...
✓ BehaviorPolicy singleton initialized

Testing placeholder detection...
✓ Placeholder detected correctly
  Violation: Placeholder code detected. Implement complete functionality.

Testing TODO detection...
✓ TODO comment detected correctly

[... 12 more tests ...]

=== ALL TESTS PASSED ✓ ===
AI Behavior Mandate is properly enforced across VersaAI.
```

## Documentation

📚 **Complete Documentation:**

1. **[Implementation Guide](docs/AI_BEHAVIOR_MANDATE_INTEGRATION.md)**
   - Technical architecture
   - API reference
   - Integration patterns
   - Extension guide

2. **[User Guide](docs/AI_BEHAVIOR_MANDATE_USER_GUIDE.md)**
   - Quick reference
   - Example interactions
   - Exception keywords
   - FAQ

3. **[Implementation Summary](docs/AI_BEHAVIOR_MANDATE_IMPLEMENTATION_SUMMARY.md)**
   - What was built
   - Files created/modified
   - Testing status
   - Success criteria

4. **[Original Mandate](.github/AI_BEHAVIOR_MANDATE.md)**
   - Core principles
   - Forbidden behaviors
   - Required behaviors
   - Code examples

## Integration Checklist

✅ BehaviorPolicy system implemented  
✅ AgentBase enhanced with enforcement  
✅ DevelopmentAgent created  
✅ VersaAICore integration complete  
✅ Test suite created (15 tests)  
✅ Documentation complete  
✅ Example code provided  
✅ Compiles successfully  
✅ All components validated  

## Examples

See `examples/mandate_integration_example.cpp` for complete demonstrations:

1. Basic mandate enforcement
2. Production-quality code validation
3. DevelopmentAgent usage
4. User exception handling
5. Input augmentation
6. VersaAICore integration
7. Quality scoring

## Configuration

### Default (Production Mode)
```cpp
PolicyConfig config;
config.allow_placeholders = false;
config.allow_todos = false;
config.allow_simplifications = false;
config.enforce_error_handling = true;
config.enforce_documentation = true;
config.enforce_production_quality = true;
```

### Customize for Your Agent
```cpp
void MyAgent::initializeBehaviorPolicy() override {
  VersaAI::BehaviorPolicy::PolicyConfig config;
  config.enforce_error_handling = true;
  config.minimum_severity_to_reject = ViolationSeverity::HIGH;
  behavior_policy_.setConfig(config);
}
```

## Troubleshooting

**Q: Mandate file not found**  
A: System uses built-in defaults. Place `AI_BEHAVIOR_MANDATE.md` in `.github/` for full features.

**Q: Too strict for prototyping**  
A: Use exception keywords: "give me a quick prototype for testing"

**Q: False positive violation**  
A: Configure policy for your specific agent or use exception keywords

**Q: How to disable for specific tasks?**  
A: Override `initializeBehaviorPolicy()` in your agent

## Future Enhancements

- ML-based quality detection
- Auto-fix engine for violations
- Custom policy templates
- IDE integration
- Metrics dashboard
- Team-specific configurations

## Support

For issues or questions:

1. Check documentation in `docs/`
2. Review examples in `examples/`
3. Run test suite for validation
4. Check mandate file: `.github/AI_BEHAVIOR_MANDATE.md`

## License

Same as VersaAI project.

---

**Remember:** VersaAI now defaults to expert-level, production-grade responses. This is not optional—it's enforced at the core level to ensure quality consistency across all development tasks.
