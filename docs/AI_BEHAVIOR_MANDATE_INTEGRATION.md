# AI Behavior Mandate Integration - Implementation Complete

## Overview

The AI Behavior Mandate has been successfully integrated into VersaAI's core architecture, ensuring that all development-related responses adhere to production-grade, expert-level standards as defined in `AI_BEHAVIOR_MANDATE.md`.

## Architecture

### Components Implemented

#### 1. **BehaviorPolicy** (`include/BehaviorPolicy.hpp`, `src/core/BehaviorPolicy.cpp`)

**Purpose:** Centralized singleton that enforces the AI Behavior Mandate across all VersaAI components.

**Key Features:**
- **Violation Detection:** Detects forbidden patterns (placeholders, TODOs, simplifications, workarounds, MVP thinking)
- **Code Validation:** Validates code against production quality standards (error handling, documentation, optimal algorithms)
- **System Prompt Generation:** Creates system prompts embedded with mandate principles
- **Input Augmentation:** Adds mandate reminders to development requests
- **User Exception Detection:** Recognizes when users explicitly request simplified versions
- **Quality Scoring:** Calculates quality scores (0-100) based on violations

**Configuration:**
```cpp
struct PolicyConfig {
  bool allow_placeholders = false;
  bool allow_todos = false;
  bool allow_simplifications = false;
  bool enforce_error_handling = true;
  bool enforce_documentation = true;
  bool enforce_production_quality = true;
  ViolationSeverity minimum_severity_to_reject = ViolationSeverity::CRITICAL;
  
  // User override flags
  bool user_requested_mvp = false;
  bool user_requested_prototype = false;
  bool user_requested_simplified = false;
};
```

**Violation Severity Levels:**
- **CRITICAL:** Must be rejected (placeholders, TODOs, empty implementations)
- **HIGH:** Strongly discouraged (simplifications, workarounds, MVP thinking)
- **MEDIUM:** Warning level (missing documentation)
- **LOW:** Advisory (style preferences)

#### 2. **Enhanced AgentBase** (`src/agents/AgentBase.hpp`)

**Purpose:** Base class for all agents with automatic mandate enforcement.

**Behavior:**
1. **Input Augmentation:** Automatically augments user input with mandate reminders for development requests
2. **Exception Detection:** Checks if user explicitly requested MVP/prototype/simplified version
3. **Response Validation:** Validates all responses against the behavior policy
4. **Self-Correction:** Attempts to automatically fix violations (removes TODOs, placeholders)
5. **Quality Warnings:** Adds warnings to responses that don't meet production standards

**Key Methods:**
- `performTask(input)`: Public interface with automatic enforcement
- `executeTask(input)`: Protected method that derived classes override
- `initializeBehaviorPolicy()`: Configure agent-specific policy settings
- `attemptSelfCorrection()`: Automatically fix common violations

#### 3. **DevelopmentAgent** (`src/agents/DevelopmentAgent.hpp`)

**Purpose:** Specialized agent for code generation and development tasks.

**Features:**
- **Task Classification:** Automatically classifies requests (implementation, refactoring, bug fix, architecture)
- **Strict Enforcement:** Uses strictest policy configuration for code generation
- **Code Quality Validation:** Double-validates code blocks against production standards
- **Context-Aware:** Provides "code" context for enhanced validation

**Handles:**
- Implementation requests
- Refactoring tasks
- Bug fixes (root cause analysis enforced)
- Architecture design
- General development requests

#### 4. **VersaAICore Integration** (`src/core/VersaAICore.cpp`)

**Behavior:**
- **Automatic Loading:** Loads `AI_BEHAVIOR_MANDATE.md` on initialization
- **System-Wide Enforcement:** Mandate applied to all registered agents
- **DevelopmentAgent Registration:** Automatically registers specialized development agent
- **Fallback:** Uses built-in defaults if mandate file not found

## Usage

### For End Users

When a user asks VersaAI to implement something:

```
User: "Implement a data cache manager"

VersaAI Internal Process:
1. Input augmented with: "[MANDATE: Provide complete, production-grade implementation...]"
2. Agent generates response
3. Response validated for:
   - No placeholders or TODOs
   - Comprehensive error handling
   - Complete documentation
   - Optimal algorithms
4. If violations detected:
   - Self-correction attempted
   - Quality warnings added to response
5. User receives production-grade solution
```

### User Override

Users can explicitly request exceptions:

```
User: "Give me a quick prototype for testing"

VersaAI: Recognizes exception request
        - Disables strict validation
        - Still notes what's missing
        - Offers to implement full solution
```

### For Developers Extending VersaAI

#### Creating a New Agent

```cpp
class MyAgent : public AgentBase {
public:
  explicit MyAgent() : AgentBase("MyAgent") {
    initializeBehaviorPolicy();
  }

  std::string getTaskContext() const override {
    return "code";  // or "design", "documentation", etc.
  }

protected:
  std::string executeTask(const std::string& input) override {
    // Your agent logic here
    // Response will be automatically validated
    return generateResponse(input);
  }

  void initializeBehaviorPolicy() override {
    // Customize policy for your agent
    VersaAI::BehaviorPolicy::PolicyConfig config;
    config.enforce_error_handling = true;
    config.enforce_documentation = true;
    behavior_policy_.setConfig(config);
  }
};
```

#### Validating Code Programmatically

```cpp
auto& policy = VersaAI::BehaviorPolicy::getInstance();

std::string code = generateCode();
auto result = policy.validateCode(code, "cpp");

if (!result.is_compliant) {
  std::cout << "Quality Score: " << result.quality_score << std::endl;
  std::cout << "Violations: " << std::endl;
  for (const auto& v : result.violations) {
    std::cout << "  - " << v.description << std::endl;
  }
  std::cout << "Suggestions: " << result.suggestion << std::endl;
}
```

## Validation Patterns

### Forbidden Patterns (Detected & Rejected)

**Placeholders:**
- `// placeholder`
- `// stub implementation`
- `// temporary implementation`
- `pass # stub`

**TODOs:**
- `// TODO: implement this`
- `// FIXME:`
- `// HACK:`
- `implement this later`
- `we can add this later`

**Simplification Language:**
- `let's start with a simpler version`
- `for now, we can just`
- `to make this easier`
- `a basic implementation`
- `good enough for now`

**Workarounds:**
- `we can work around this`
- `a quick fix`
- `this hack`
- `temporary fix`

**MVP Thinking:**
- `let's get it working first`
- `we can optimize later`
- `for version 1`
- `minimum viable`
- `sufficient for now`

### Required Patterns (Enforced)

**For Code:**
- Error handling (`try-catch`, `if (ptr != nullptr)`, validation)
- Documentation (`/** @brief */`, `@param`, `@return`)
- Complete implementations (no empty function bodies)

**For Responses:**
- Complete solutions (not partial)
- Production-ready quality
- Optimal approaches
- Comprehensive edge case handling

## Testing

Run the comprehensive test suite:

```bash
./build/tests/test_behavior_mandate
```

**Tests validate:**
- Placeholder detection
- TODO detection
- Simplification language detection
- Workaround detection
- MVP thinking detection
- Production-quality code validation
- User exception detection
- System prompt generation
- Input augmentation
- DevelopmentAgent integration
- Quality score calculation
- Error handling validation
- Documentation validation
- Mandate file loading

## Integration Points

### 1. VersaAICore Initialization
```cpp
VersaAICore::VersaAICore() {
  // ...
  VersaAI::BehaviorPolicy::getInstance().loadMandate(".github/AI_BEHAVIOR_MANDATE.md");
  // ...
  registerAgent("Development", std::make_shared<DevelopmentAgent>());
}
```

### 2. Agent Response Generation
```cpp
std::string AgentBase::performTask(const std::string& input) {
  // 1. Augment input with mandate
  std::string augmented = behavior_policy_.augmentUserInput(input);
  
  // 2. Execute agent logic
  std::string response = executeTask(augmented);
  
  // 3. Validate response
  auto validation = behavior_policy_.validateResponse(response);
  
  // 4. Self-correct if needed
  if (!validation.is_compliant) {
    response = attemptSelfCorrection(response, validation);
  }
  
  return response;
}
```

### 3. Code Generation
```cpp
std::string DevelopmentAgent::executeTask(const std::string& input) {
  // Generate code
  std::string code = generateCode(input);
  
  // Validate against production standards
  auto validation = behavior_policy_.validateCode(code, "cpp");
  
  if (!validation.is_compliant) {
    // Add quality warnings
    code += "\n[QUALITY ISSUES: " + validation.suggestion + "]";
  }
  
  return code;
}
```

## Performance Considerations

- **Singleton Pattern:** BehaviorPolicy uses thread-safe singleton (minimal overhead)
- **Regex Compilation:** Patterns compiled once during initialization
- **Lazy Validation:** Only validates development-related requests
- **Caching:** Can cache validation results for identical inputs (future optimization)

## Configuration

### Default Configuration (Production)
```cpp
PolicyConfig config;
config.allow_placeholders = false;
config.allow_todos = false;
config.allow_simplifications = false;
config.enforce_error_handling = true;
config.enforce_documentation = true;
config.enforce_production_quality = true;
config.minimum_severity_to_reject = ViolationSeverity::CRITICAL;
```

### Lenient Configuration (For Learning/Prototyping)
```cpp
PolicyConfig config;
config.allow_placeholders = true;
config.allow_todos = true;
config.allow_simplifications = true;
config.enforce_error_handling = false;
config.minimum_severity_to_reject = ViolationSeverity::HIGH;
```

## Logging & Debugging

The system logs violations when detected:

```
[DevelopmentAgent] Behavior Violation [NO_TODOS]: TODO comment detected. 
  Complete implementation now, not later.
```

Enable debug logging in VersaAI to see validation details:

```cpp
logConfig.minLevel = VersaAI::LogLevel::DEBUG;
```

## Future Enhancements

### Planned Features
1. **ML-Based Detection:** Train model to detect subtle quality issues
2. **Custom Rules:** Allow users to define custom quality rules
3. **Auto-Fix:** More sophisticated self-correction capabilities
4. **Performance Metrics:** Track adherence to mandate over time
5. **Team Policies:** Different policies for different teams/projects
6. **IDE Integration:** Real-time validation in code editors

### Extension Points
```cpp
// Custom violation detector
class CustomDetector {
public:
  virtual std::vector<Violation> detect(const std::string& code) = 0;
};

// Register custom detector
BehaviorPolicy::getInstance().registerDetector(std::make_unique<MyDetector>());
```

## Troubleshooting

### Mandate File Not Found
**Error:** "Could not load AI Behavior Mandate from .github/AI_BEHAVIOR_MANDATE.md"  
**Solution:** System uses built-in defaults. File is optional but recommended for full features.

### False Positives
**Issue:** Valid code flagged as violation  
**Solution:** Use user exception keywords or configure policy for specific agent

### Too Strict
**Issue:** Can't prototype quickly  
**Solution:** Use exception phrases: "give me a quick prototype", "just a minimal example"

## Summary

The AI Behavior Mandate integration ensures VersaAI consistently produces expert-level, production-grade code by:

1. **Detecting** forbidden patterns (placeholders, TODOs, simplifications)
2. **Enforcing** required patterns (error handling, documentation)
3. **Validating** all responses against production standards
4. **Self-correcting** common violations automatically
5. **Respecting** user requests for exceptions when explicitly stated

This system transforms VersaAI from a helpful assistant into an expert colleague that refuses to compromise on code quality.
