#pragma once

#include "VersaAIException.hpp"
#include <functional>
#include <chrono>
#include <atomic>
#include <mutex>
#include <optional>

namespace VersaAI {

// ============================================================================
// Error Recovery Strategies
// ============================================================================

/**
 * @brief Strategy for recovering from errors
 */
class RecoveryStrategy {
public:
    virtual ~RecoveryStrategy() = default;

    /**
     * @brief Attempt to execute operation with recovery
     * @return true if operation succeeded, false if all recovery attempts failed
     */
    virtual bool execute(std::function<void()> operation) = 0;

    /**
     * @brief Get last exception that occurred
     */
    virtual std::optional<std::string> getLastError() const = 0;
};

/**
 * @brief Retry strategy with exponential backoff
 */
class RetryStrategy : public RecoveryStrategy {
public:
    struct Config {
        int maxRetries = 3;
        std::chrono::milliseconds initialDelay{100};
        double backoffMultiplier = 2.0;
        std::chrono::milliseconds maxDelay{5000};
        bool resetOnSuccess = true;
    };

    RetryStrategy() : RetryStrategy(Config{}) {}
    explicit RetryStrategy(const Config& config);    bool execute(std::function<void()> operation) override;
    std::optional<std::string> getLastError() const override { return lastError_; }

    int getAttemptCount() const { return attemptCount_; }
    void reset();

private:
    Config config_;
    int attemptCount_ = 0;
    std::optional<std::string> lastError_;
};

/**
 * @brief Fallback strategy - try primary, then fallback operation
 */
class FallbackStrategy : public RecoveryStrategy {
public:
    FallbackStrategy(
        std::function<void()> fallbackOperation,
        const std::string& fallbackName = "fallback"
    );

    bool execute(std::function<void()> operation) override;
    std::optional<std::string> getLastError() const override { return lastError_; }

    bool didFallback() const { return usedFallback_; }

private:
    std::function<void()> fallbackOperation_;
    std::string fallbackName_;
    bool usedFallback_ = false;
    std::optional<std::string> lastError_;
};

// ============================================================================
// Circuit Breaker
// ============================================================================

/**
 * @brief Circuit breaker state
 */
enum class CircuitState {
    CLOSED,      // Normal operation, requests go through
    OPEN,        // Circuit is open, fail fast
    HALF_OPEN    // Testing if service recovered
};

/**
 * @brief Circuit breaker for protecting against cascading failures
 *
 * Implements the circuit breaker pattern to prevent repeated calls to
 * failing operations, allowing time for recovery.
 */
class CircuitBreaker {
public:
    struct Config {
        int failureThreshold = 5;              // Failures before opening
        std::chrono::seconds openTimeout{30};  // Time before half-open
        int halfOpenSuccesses = 2;             // Successes to close
        std::chrono::milliseconds callTimeout{5000};  // Per-call timeout
    };

    CircuitBreaker(const std::string& name) : CircuitBreaker(name, Config{}) {}
    CircuitBreaker(const std::string& name, const Config& config);    /**
     * @brief Execute operation through circuit breaker
     * @throws ResourceException if circuit is open
     */
    template<typename Func>
    auto call(Func&& func) -> decltype(func()) {
        if (state_ == CircuitState::OPEN) {
            auto now = std::chrono::steady_clock::now();
            if (now - openedAt_ < config_.openTimeout) {
                throw ResourceException(
                    "Circuit breaker is OPEN for " + name_,
                    ErrorCode::RESOURCE_UNAVAILABLE
                ).setResourceType("CircuitBreaker")
                 .addContext("circuit_name", name_)
                 .addContext("state", "OPEN")
                 .addContext("failures", std::to_string(failureCount_.load()));
            }
            // Transition to HALF_OPEN
            transitionTo(CircuitState::HALF_OPEN);
        }

        try {
            auto result = func();
            onSuccess();
            return result;
        } catch (...) {
            onFailure();
            throw;
        }
    }

    // State inspection
    CircuitState getState() const { return state_; }
    int getFailureCount() const { return failureCount_.load(); }
    int getSuccessCount() const { return successCount_.load(); }
    std::string getName() const { return name_; }

    // Manual control
    void reset();
    void trip();  // Force open

private:
    void onSuccess();
    void onFailure();
    void transitionTo(CircuitState newState);

    std::string name_;
    Config config_;

    std::atomic<CircuitState> state_{CircuitState::CLOSED};
    std::atomic<int> failureCount_{0};
    std::atomic<int> successCount_{0};
    std::chrono::steady_clock::time_point openedAt_;

    mutable std::mutex mutex_;  // Protects state transitions
};

/**
 * @brief Manager for multiple circuit breakers
 */
class CircuitBreakerRegistry {
public:
    static CircuitBreakerRegistry& getInstance();

    /**
     * @brief Get or create circuit breaker
     */
    std::shared_ptr<CircuitBreaker> getOrCreate(const std::string& name);
    std::shared_ptr<CircuitBreaker> getOrCreate(
        const std::string& name,
        const CircuitBreaker::Config& config
    );

    /**
     * @brief Get existing circuit breaker
     */
    std::shared_ptr<CircuitBreaker> get(const std::string& name);

    /**
     * @brief Remove circuit breaker
     */
    void remove(const std::string& name);

    /**
     * @brief Get all circuit breaker names
     */
    std::vector<std::string> getAllNames() const;

    /**
     * @brief Reset all circuit breakers
     */
    void resetAll();

private:
    CircuitBreakerRegistry() = default;

    std::map<std::string, std::shared_ptr<CircuitBreaker>> breakers_;
    mutable std::mutex mutex_;
};

// ============================================================================
// Convenience Functions
// ============================================================================

/**
 * @brief Execute operation with retry on failure
 */
template<typename Func>
auto withRetry(Func&& func) -> decltype(func()) {
    return withRetry(std::forward<Func>(func), RetryStrategy::Config{});
}

template<typename Func>
auto withRetry(Func&& func, const RetryStrategy::Config& config) -> decltype(func()) {
    RetryStrategy strategy(config);
    decltype(func()) result;
    bool success = strategy.execute([&]() { result = func(); });
    if (!success) {
        throw Exception(
            "Operation failed after " + std::to_string(config.maxRetries) + " retries: "
            + strategy.getLastError().value_or("unknown error")
        );
    }
    return result;
}

/**
 * @brief Execute operation with fallback
 */
template<typename Func, typename FallbackFunc>
auto withFallback(Func&& primaryFunc, FallbackFunc&& fallbackFunc)
    -> decltype(primaryFunc()) {
    try {
        return primaryFunc();
    } catch (const Exception& ex) {
        logException(ex, "Falling back to alternative");
        return fallbackFunc();
    }
}

/**
 * @brief Execute operation through circuit breaker
 */
template<typename Func>
auto withCircuitBreaker(const std::string& name, Func&& func)
    -> decltype(func()) {
    auto breaker = CircuitBreakerRegistry::getInstance().getOrCreate(name);
    return breaker->call(std::forward<Func>(func));
}

} // namespace VersaAI
