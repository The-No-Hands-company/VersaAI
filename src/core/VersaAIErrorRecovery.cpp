#include "VersaAIErrorRecovery.hpp"
#include "VersaAILogger.hpp"
#include <thread>

namespace VersaAI {

// ============================================================================
// RetryStrategy Implementation
// ============================================================================

RetryStrategy::RetryStrategy(const Config& config)
    : config_(config), attemptCount_(0) {}

bool RetryStrategy::execute(std::function<void()> operation) {
    std::chrono::milliseconds currentDelay = config_.initialDelay;

    for (int attempt = 0; attempt <= config_.maxRetries; ++attempt) {
        try {
            attemptCount_ = attempt + 1;
            operation();

            if (config_.resetOnSuccess) {
                attemptCount_ = 0;
            }
            lastError_.reset();
            return true;

        } catch (const Exception& ex) {
            lastError_ = ex.getMessage();

            if (attempt < config_.maxRetries) {
                Logger::getInstance().warning(
                    "Retry attempt " + std::to_string(attempt + 1) + "/" +
                    std::to_string(config_.maxRetries) + " failed: " + ex.getMessage() +
                    ", retrying in " + std::to_string(currentDelay.count()) + "ms",
                    "RetryStrategy"
                );

                std::this_thread::sleep_for(currentDelay);

                // Exponential backoff
                currentDelay = std::chrono::milliseconds(
                    static_cast<long>(currentDelay.count() * config_.backoffMultiplier)
                );
                if (currentDelay > config_.maxDelay) {
                    currentDelay = config_.maxDelay;
                }
            } else {
                Logger::getInstance().error(
                    "All retry attempts exhausted (" + std::to_string(config_.maxRetries + 1) +
                    " attempts): " + ex.getMessage(),
                    "RetryStrategy"
                );
            }

        } catch (const std::exception& ex) {
            lastError_ = ex.what();

            if (attempt < config_.maxRetries) {
                Logger::getInstance().warning(
                    "Retry attempt " + std::to_string(attempt + 1) + "/" +
                    std::to_string(config_.maxRetries) + " failed: " + ex.what() +
                    ", retrying in " + std::to_string(currentDelay.count()) + "ms",
                    "RetryStrategy"
                );

                std::this_thread::sleep_for(currentDelay);
                currentDelay = std::chrono::milliseconds(
                    static_cast<long>(currentDelay.count() * config_.backoffMultiplier)
                );
                if (currentDelay > config_.maxDelay) {
                    currentDelay = config_.maxDelay;
                }
            }
        }
    }

    return false;
}

void RetryStrategy::reset() {
    attemptCount_ = 0;
    lastError_.reset();
}

// ============================================================================
// FallbackStrategy Implementation
// ============================================================================

FallbackStrategy::FallbackStrategy(
    std::function<void()> fallbackOperation,
    const std::string& fallbackName
) : fallbackOperation_(std::move(fallbackOperation)),
    fallbackName_(fallbackName),
    usedFallback_(false) {}

bool FallbackStrategy::execute(std::function<void()> operation) {
    try {
        operation();
        usedFallback_ = false;
        lastError_.reset();
        return true;

    } catch (const Exception& ex) {
        lastError_ = ex.getMessage();

        Logger::getInstance().warning(
            "Primary operation failed: " + ex.getMessage() +
            ", using fallback: " + fallbackName_,
            "FallbackStrategy"
        );

        try {
            fallbackOperation_();
            usedFallback_ = true;
            return true;

        } catch (const Exception& fallbackEx) {
            Logger::getInstance().error(
                "Fallback operation '" + fallbackName_ + "' also failed: " +
                fallbackEx.getMessage(),
                "FallbackStrategy"
            );
            lastError_ = "Primary: " + ex.getMessage() + "; Fallback: " + fallbackEx.getMessage();
            return false;
        }

    } catch (const std::exception& ex) {
        lastError_ = ex.what();

        Logger::getInstance().warning(
            "Primary operation failed: " + std::string(ex.what()) +
            ", using fallback: " + fallbackName_,
            "FallbackStrategy"
        );

        try {
            fallbackOperation_();
            usedFallback_ = true;
            return true;
        } catch (const std::exception& fallbackEx) {
            lastError_ = "Primary: " + std::string(ex.what()) +
                        "; Fallback: " + fallbackEx.what();
            return false;
        }
    }
}

// ============================================================================
// CircuitBreaker Implementation
// ============================================================================

CircuitBreaker::CircuitBreaker(const std::string& name, const Config& config)
    : name_(name), config_(config) {
    Logger::getInstance().info(
        "Circuit breaker created: " + name +
        " (threshold: " + std::to_string(config.failureThreshold) +
        ", timeout: " + std::to_string(config.openTimeout.count()) + "s)",
        "CircuitBreaker"
    );
}

void CircuitBreaker::onSuccess() {
    std::lock_guard lock(mutex_);

    if (state_ == CircuitState::HALF_OPEN) {
        successCount_++;

        if (successCount_ >= config_.halfOpenSuccesses) {
            transitionTo(CircuitState::CLOSED);
            failureCount_ = 0;
            successCount_ = 0;
        }
    } else if (state_ == CircuitState::CLOSED) {
        // Reset failure count on success
        failureCount_ = 0;
    }
}

void CircuitBreaker::onFailure() {
    std::lock_guard lock(mutex_);

    failureCount_++;

    if (state_ == CircuitState::HALF_OPEN) {
        // Failed in half-open state, reopen circuit
        transitionTo(CircuitState::OPEN);
        successCount_ = 0;

    } else if (state_ == CircuitState::CLOSED) {
        if (failureCount_ >= config_.failureThreshold) {
            transitionTo(CircuitState::OPEN);
        }
    }
}

void CircuitBreaker::transitionTo(CircuitState newState) {
    CircuitState oldState = state_.load();
    state_ = newState;

    if (newState == CircuitState::OPEN) {
        openedAt_ = std::chrono::steady_clock::now();
    }

    Logger::getInstance().warning(
        "Circuit breaker '" + name_ + "' state transition: " +
        std::to_string(static_cast<int>(oldState)) + " -> " +
        std::to_string(static_cast<int>(newState)) +
        " (failures: " + std::to_string(failureCount_.load()) + ")",
        "CircuitBreaker"
    );
}

void CircuitBreaker::reset() {
    std::lock_guard lock(mutex_);
    failureCount_ = 0;
    successCount_ = 0;
    transitionTo(CircuitState::CLOSED);

    Logger::getInstance().info(
        "Circuit breaker '" + name_ + "' manually reset",
        "CircuitBreaker"
    );
}

void CircuitBreaker::trip() {
    std::lock_guard lock(mutex_);
    transitionTo(CircuitState::OPEN);

    Logger::getInstance().warning(
        "Circuit breaker '" + name_ + "' manually tripped",
        "CircuitBreaker"
    );
}

// ============================================================================
// CircuitBreakerRegistry Implementation
// ============================================================================

CircuitBreakerRegistry& CircuitBreakerRegistry::getInstance() {
    static CircuitBreakerRegistry instance;
    return instance;
}

std::shared_ptr<CircuitBreaker> CircuitBreakerRegistry::getOrCreate(
    const std::string& name
) {
    return getOrCreate(name, CircuitBreaker::Config{});
}

std::shared_ptr<CircuitBreaker> CircuitBreakerRegistry::getOrCreate(
    const std::string& name,
    const CircuitBreaker::Config& config
) {
    std::lock_guard lock(mutex_);

    auto it = breakers_.find(name);
    if (it != breakers_.end()) {
        return it->second;
    }

    auto breaker = std::make_shared<CircuitBreaker>(name, config);
    breakers_[name] = breaker;
    return breaker;
}

std::shared_ptr<CircuitBreaker> CircuitBreakerRegistry::get(const std::string& name) {
    std::lock_guard lock(mutex_);

    auto it = breakers_.find(name);
    if (it != breakers_.end()) {
        return it->second;
    }

    return nullptr;
}

void CircuitBreakerRegistry::remove(const std::string& name) {
    std::lock_guard lock(mutex_);
    breakers_.erase(name);
}

std::vector<std::string> CircuitBreakerRegistry::getAllNames() const {
    std::lock_guard lock(mutex_);

    std::vector<std::string> names;
    names.reserve(breakers_.size());
    for (const auto& [name, _] : breakers_) {
        names.push_back(name);
    }
    return names;
}

void CircuitBreakerRegistry::resetAll() {
    std::lock_guard lock(mutex_);

    for (auto& [name, breaker] : breakers_) {
        breaker->reset();
    }

    Logger::getInstance().info(
        "All circuit breakers reset (" + std::to_string(breakers_.size()) + " breakers)",
        "CircuitBreakerRegistry"
    );
}

} // namespace VersaAI
