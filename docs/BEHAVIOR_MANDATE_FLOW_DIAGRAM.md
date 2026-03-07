# AI Behavior Mandate - System Flow Diagram

## Complete Request Processing Flow

```
┌──────────────────────────────────────────────────────────────────────────┐
│                           USER REQUEST                                    │
│  "Implement a cache manager with thread-safety and TTL support"          │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      VersaAICore::processInput()                          │
│  - Routes to appropriate chatbot/agent                                    │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       AgentBase::performTask()                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ STEP 1: Input Augmentation                                         │  │
│  │ BehaviorPolicy::augmentUserInput(input)                            │  │
│  │                                                                     │  │
│  │ Input: "Implement a cache manager..."                              │  │
│  │ Output: "Implement a cache manager...                              │  │
│  │          [MANDATE: Provide complete, production-grade              │  │
│  │           implementation. No placeholders, TODOs, or               │  │
│  │           simplifications. Include comprehensive error              │  │
│  │           handling and documentation.]"                            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 │                                         │
│                                 ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ STEP 2: Exception Detection                                        │  │
│  │ BehaviorPolicy::detectUserException(input)                         │  │
│  │                                                                     │  │
│  │ Checks for keywords:                                               │  │
│  │ - "quick prototype"     ❌ Not found                               │  │
│  │ - "minimal example"     ❌ Not found                               │  │
│  │ - "simplified version"  ❌ Not found                               │  │
│  │                                                                     │  │
│  │ Result: NO EXCEPTION - Enforce strict standards                    │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 │                                         │
│                                 ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ STEP 3: Task Execution                                             │  │
│  │ DevelopmentAgent::executeTask(augmented_input)                     │  │
│  │                                                                     │  │
│  │ - Analyzes task type: "implementation"                             │  │
│  │ - Generates complete implementation                                │  │
│  │ - Includes error handling                                          │  │
│  │ - Adds documentation                                               │  │
│  │ - Optimizes for production                                         │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 │                                         │
│                                 ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ STEP 4: Response Validation                                        │  │
│  │ BehaviorPolicy::validateResponse(response)                         │  │
│  │                                                                     │  │
│  │ Checks for FORBIDDEN patterns:                                     │  │
│  │ ✓ No "TODO" comments                                               │  │
│  │ ✓ No placeholders                                                  │  │
│  │ ✓ No simplification language                                       │  │
│  │ ✓ No workarounds                                                   │  │
│  │ ✓ No MVP thinking                                                  │  │
│  │                                                                     │  │
│  │ Checks for REQUIRED patterns:                                      │  │
│  │ ✓ Has error handling                                               │  │
│  │ ✓ Has documentation                                                │  │
│  │ ✓ Complete implementation                                          │  │
│  │                                                                     │  │
│  │ Quality Score: 95.0/100 ✅                                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 │                                         │
│                                 ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ STEP 5: Self-Correction (if needed)                                │  │
│  │ AgentBase::attemptSelfCorrection(response, validation)             │  │
│  │                                                                     │  │
│  │ If violations detected:                                            │  │
│  │ - Remove TODO comments                                             │  │
│  │ - Remove placeholder text                                          │  │
│  │ - Add missing error handling                                       │  │
│  │ - Re-validate                                                      │  │
│  │                                                                     │  │
│  │ Result: PASSED - No corrections needed                             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                 │                                         │
│                                 ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ STEP 6: Quality Warnings (if applicable)                           │  │
│  │                                                                     │  │
│  │ If quality_score < 90:                                             │  │
│  │   response += "[QUALITY WARNING: ...]"                             │  │
│  │                                                                     │  │
│  │ Result: No warnings - quality score is 95.0                        │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────┬─────────────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      FINAL RESPONSE TO USER                               │
│                                                                           │
│  /**                                                                      │
│   * @brief Thread-safe LRU cache with TTL support                        │
│   * @tparam K Key type                                                   │
│   * @tparam V Value type                                                 │
│   */                                                                     │
│  template<typename K, typename V>                                        │
│  class CacheManager {                                                    │
│  public:                                                                 │
│    struct Config {                                                       │
│      size_t max_size = 1000;                                            │
│      std::chrono::seconds ttl = std::chrono::seconds(3600);             │
│    };                                                                    │
│                                                                           │
│    explicit CacheManager(const Config& config)                           │
│      : config_(config), access_count_(0) {                              │
│      if (config.max_size == 0) {                                        │
│        throw std::invalid_argument("Cache size must be > 0");           │
│      }                                                                   │
│    }                                                                     │
│                                                                           │
│    void put(const K& key, const V& value) {                             │
│      std::lock_guard<std::mutex> lock(mutex_);                          │
│      // ... [complete implementation with error handling]               │
│    }                                                                     │
│                                                                           │
│    std::optional<V> get(const K& key) {                                 │
│      std::lock_guard<std::mutex> lock(mutex_);                          │
│      // ... [complete implementation with error handling]               │
│    }                                                                     │
│                                                                           │
│  private:                                                                │
│    // ... [complete private members and helper methods]                 │
│  };                                                                      │
│                                                                           │
│  [200+ lines of production-ready code]                                   │
│  Quality Score: 95.0/100 ✅                                               │
└──────────────────────────────────────────────────────────────────────────┘
```

## Component Interaction Diagram

```
┌─────────────────┐
│   .github/      │
│ AI_BEHAVIOR_    │
│ MANDATE.md      │◄──────────┐
└─────────────────┘           │
                              │ loads on startup
                              │
        ┌─────────────────────┴────────────────────┐
        │         VersaAICore                      │
        │  - getInstance()                         │
        │  - registerAgent("Development", ...)     │
        └─────────────────┬────────────────────────┘
                          │
                          │ registers
                          ▼
        ┌──────────────────────────────────────────┐
        │      DevelopmentAgent : AgentBase        │
        │  - performTask()                         │
        │  - executeTask()                         │
        │  - getTaskContext() = "code"             │
        └─────────────────┬────────────────────────┘
                          │
                          │ uses
                          ▼
        ┌──────────────────────────────────────────┐
        │  BehaviorPolicy (Singleton)              │
        │  ┌────────────────────────────────────┐  │
        │  │ Pattern Detection                  │  │
        │  │ - placeholder_patterns_            │  │
        │  │ - todo_patterns_                   │  │
        │  │ - simplification_patterns_         │  │
        │  │ - workaround_patterns_             │  │
        │  │ - mvp_patterns_                    │  │
        │  │ - exception_request_patterns_      │  │
        │  └────────────────────────────────────┘  │
        │  ┌────────────────────────────────────┐  │
        │  │ Validation Methods                 │  │
        │  │ - validateResponse()               │  │
        │  │ - validateCode()                   │  │
        │  │ - detectUserException()            │  │
        │  └────────────────────────────────────┘  │
        │  ┌────────────────────────────────────┐  │
        │  │ Enhancement Methods                │  │
        │  │ - augmentUserInput()               │  │
        │  │ - generateSystemPrompt()           │  │
        │  │ - calculateQualityScore()          │  │
        │  └────────────────────────────────────┘  │
        └──────────────────────────────────────────┘
```

## Violation Detection Flow

```
                    Input: Code or Response
                              │
                              ▼
        ┌──────────────────────────────────────────┐
        │   CRITICAL Violations (Auto-Reject)      │
        │                                          │
        │   ✓ Check for TODO comments              │
        │   ✓ Check for placeholders               │
        │   ✓ Check for empty implementations      │
        │                                          │
        │   Penalty: -30 points per violation      │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   HIGH Violations (Strongly Discouraged) │
        │                                          │
        │   ✓ Check for simplification language    │
        │   ✓ Check for workarounds                │
        │   ✓ Check for MVP thinking               │
        │                                          │
        │   Penalty: -15 points per violation      │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   MEDIUM Violations (Warning Level)      │
        │                                          │
        │   ✓ Check for missing documentation      │
        │   ✓ Check for incomplete error handling  │
        │                                          │
        │   Penalty: -7.5 points per violation     │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   Calculate Final Quality Score          │
        │                                          │
        │   Score = 100.0 - Σ(penalties)           │
        │                                          │
        │   90-100: Production-ready ✅            │
        │   70-89:  Good, minor improvements       │
        │   50-69:  Needs work                     │
        │   <50:    Not production-ready ❌        │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   Generate Validation Result             │
        │                                          │
        │   is_compliant: bool                     │
        │   violations: vector<Violation>          │
        │   quality_score: double                  │
        │   suggestion: string                     │
        └──────────────────────────────────────────┘
```

## User Exception Handling Flow

```
        User Input: "Give me a quick prototype..."
                              │
                              ▼
        ┌──────────────────────────────────────────┐
        │  BehaviorPolicy::detectUserException()   │
        │                                          │
        │  Regex patterns checked:                 │
        │  - "quick prototype"      ✓ MATCH        │
        │  - "minimal example"                     │
        │  - "simplified version"                  │
        │  - "MVP approach"                        │
        │  - "placeholder is fine"                 │
        │                                          │
        │  Result: EXCEPTION DETECTED              │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   Update Policy Configuration            │
        │                                          │
        │   config.user_requested_simplified = true│
        │                                          │
        │   Effects:                               │
        │   - Validation relaxed                   │
        │   - Placeholders allowed                 │
        │   - TODOs allowed                        │
        │   - Simplifications allowed              │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   Generate Response                      │
        │                                          │
        │   [Simplified implementation]            │
        │                                          │
        │   Note: This is a prototype. Missing:    │
        │   - Thread safety                        │
        │   - Error handling                       │
        │   - Production features                  │
        │                                          │
        │   Would you like the complete version?   │
        └────────────┬─────────────────────────────┘
                     │
                     ▼
        ┌──────────────────────────────────────────┐
        │   Reset Configuration                    │
        │                                          │
        │   config.user_requested_simplified = false│
        │                                          │
        │   Ready for next request                 │
        └──────────────────────────────────────────┘
```

## Quality Score Calculation Example

```
Input Code:
    void process() {
      // TODO: implement this       ← CRITICAL (-30)
      // placeholder for now         ← CRITICAL (-30)
      // Quick fix - works around    ← HIGH (-15)
    }                               ← CRITICAL (-30) empty body

Calculation:
    Starting Score:     100.0
    - TODO comment:     -30.0
    - Placeholder:      -30.0
    - Workaround:       -15.0
    - Empty body:       -30.0
    ─────────────────────────
    Final Score:         -5.0  →  0.0 (minimum)

Result:
    is_compliant: false
    quality_score: 0.0
    violations: 4
    severity: CRITICAL
```

## Legend

```
✓  = Check passed
✅ = Compliant
❌ = Violation detected
⚠️  = Warning
│  = Process flow
▼  = Direction of flow
```
