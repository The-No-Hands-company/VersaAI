# AI Behavior Mandate - User Quick Reference

## What This Means for You

When you ask VersaAI to help with development tasks, it will **automatically provide production-grade, expert-level solutions** instead of simplified or placeholder code.

## Default Behavior

### ✅ What You Get (ALWAYS)

- **Complete implementations** (never placeholders or TODOs)
- **Comprehensive error handling** (all edge cases covered)
- **Full documentation** (clear comments and usage examples)
- **Optimal algorithms** (best performance and efficiency)
- **Production-ready code** (what you'd ship to customers)
- **Expert-level design** (SOLID principles, best practices)

### ❌ What You WON'T Get (Unless You Ask)

- ~~Simplified versions "to get started"~~
- ~~TODO comments or placeholders~~
- ~~"Quick fixes" or workarounds~~
- ~~MVP/prototype implementations~~
- ~~Missing error handling~~
- ~~Incomplete features~~

## Example Interactions

### Request: "Create a data cache"

**OLD AI Response:**
```cpp
// TODO: Implement cache logic
class Cache {
  void put(string key, string value) {
    // Placeholder for now
  }
};
```

**VersaAI Response (with Mandate):**
```cpp
/**
 * @brief Thread-safe LRU cache with TTL support
 * @tparam K Key type
 * @tparam V Value type
 */
template<typename K, typename V>
class Cache {
public:
  struct Config {
    size_t max_size = 1000;
    std::chrono::seconds ttl = std::chrono::seconds(3600);
  };

  explicit Cache(const Config& config) 
    : config_(config), access_count_(0) {}

  /**
   * @brief Stores value with automatic TTL and LRU eviction
   * @throws std::invalid_argument if key is empty
   */
  void put(const K& key, const V& value) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    if (key.empty()) {
      throw std::invalid_argument("Cache key cannot be empty");
    }
    
    // Evict expired entries
    evictExpired();
    
    // Evict LRU if at capacity
    if (cache_.size() >= config_.max_size) {
      evictLRU();
    }
    
    cache_[key] = Entry{value, Clock::now(), ++access_count_};
  }

  std::optional<V> get(const K& key) {
    std::lock_guard<std::mutex> lock(mutex_);
    
    auto it = cache_.find(key);
    if (it == cache_.end()) {
      return std::nullopt;
    }
    
    // Check TTL
    if (isExpired(it->second)) {
      cache_.erase(it);
      return std::nullopt;
    }
    
    // Update access time for LRU
    it->second.last_access = ++access_count_;
    
    return it->second.value;
  }

private:
  struct Entry {
    V value;
    Clock::time_point timestamp;
    uint64_t last_access;
  };

  void evictExpired() { /* implementation */ }
  void evictLRU() { /* implementation */ }
  bool isExpired(const Entry& entry) const { /* implementation */ }

  Config config_;
  std::unordered_map<K, Entry> cache_;
  mutable std::mutex mutex_;
  uint64_t access_count_;
};
```

## When You Want Something Different

### Exception Keywords

Use these phrases to get simplified versions:

- **"Give me a quick prototype"**
- **"Just a minimal example"**
- **"Simplified version for learning"**
- **"Placeholder is fine for now"**
- **"MVP approach"**
- **"Quick hack for testing"**

### Example

```
You: "Give me a quick prototype of a cache for testing"

VersaAI: [Provides simplified version with notation:]
         "Note: This is a simplified prototype. Missing:
          - Thread safety
          - Error handling
          - TTL support
          - Production-grade features
          
         Would you like the complete production implementation?"
```

## Common Scenarios

### Scenario 1: Implementing a Feature

**You Ask:** "Implement user authentication"

**VersaAI Provides:**
- Complete authentication system
- Password hashing (bcrypt/argon2)
- Token management (JWT with refresh)
- Session handling
- Rate limiting
- Comprehensive error handling
- Security best practices
- Full documentation

### Scenario 2: Fixing a Bug

**You Ask:** "Fix the memory leak in DataProcessor"

**VersaAI Provides:**
- Root cause analysis
- Proper fix (not workaround)
- RAII implementation
- Smart pointer usage
- Tests to prevent regression
- Documentation of the fix

### Scenario 3: Refactoring Code

**You Ask:** "Refactor this function"

**VersaAI Provides:**
- SOLID principles applied
- Optimal design patterns
- Performance improvements
- Maintainability enhancements
- Complete documentation
- Before/after comparison

### Scenario 4: Architecture Design

**You Ask:** "Design a microservices architecture"

**VersaAI Provides:**
- Complete architecture
- Scalability considered
- Fault tolerance built-in
- Monitoring/observability
- Security layers
- Deployment strategy
- Complete diagrams and docs

## Quality Guarantees

Every response is validated for:

✓ **Completeness** - No partial implementations  
✓ **Correctness** - Handles all edge cases  
✓ **Clarity** - Well-documented and readable  
✓ **Optimality** - Uses best algorithms  
✓ **Robustness** - Comprehensive error handling  
✓ **Maintainability** - Easy to extend and modify  

## Why This Matters

### Before (Typical AI Assistant)
```
Question: "Create a file reader"
Answer: "Here's a simple version to get you started..."
Result: You spend hours adding error handling, edge cases, optimization
```

### After (VersaAI with Mandate)
```
Question: "Create a file reader"
Answer: Complete production-ready implementation with:
        - Buffering for performance
        - Error handling for all scenarios
        - Support for large files
        - Memory-efficient streaming
        - Complete documentation
Result: Copy, paste, ship to production
```

## Tips for Best Results

### ✅ DO

- Ask for what you actually need in production
- Provide context about constraints (performance, memory, etc.)
- Mention specific requirements (thread-safety, etc.)
- Ask for explanations if implementation is complex

### ❌ DON'T

- Ask to "simplify" unless you actually want a simplified version
- Request "basic" versions if you need production code
- Ask for "quick" solutions if you need robust ones
- Use MVP terminology unless prototyping

## FAQ

**Q: Is VersaAI slower because it generates more complete code?**  
A: Slightly, but you save significantly more time not having to complete implementations yourself.

**Q: What if I'm just learning and want simple examples?**  
A: Use exception keywords: "simplified version for learning"

**Q: Can I customize the quality level?**  
A: Yes, use exception keywords or contact your VersaAI administrator for custom policies.

**Q: What if VersaAI's solution is too complex for my needs?**  
A: Ask for "a simplified version" and VersaAI will reduce complexity while noting trade-offs.

**Q: Does this work for all programming languages?**  
A: Yes, the mandate applies to all languages (C++, Python, JavaScript, etc.)

**Q: What about non-code tasks (documentation, design)?**  
A: The mandate applies there too - you get complete, production-grade deliverables.

## Support

If VersaAI's responses don't meet production standards:

1. Report the issue with the specific request and response
2. VersaAI will self-correct and improve
3. Violations are logged and used to enhance the system

---

**Remember:** VersaAI is designed to be your expert colleague, not a helpful tutor. It defaults to giving you production-ready solutions that you can ship immediately.
