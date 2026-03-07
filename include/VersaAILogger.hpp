#pragma once

#include <chrono>
#include <condition_variable>
#include <fstream>
#include <memory>
#include <mutex>
#include <queue>
#include <sstream>
#include <string>
#include <thread>
#include <unordered_map>
#include <vector>

namespace VersaAI {

/// Log severity levels
enum class LogLevel {
    TRACE = 0,
    DEBUG = 1,
    INFO = 2,
    WARNING = 3,
    ERROR = 4,
    CRITICAL = 5
};

/// Convert log level to string
inline const char* logLevelToString(LogLevel level) {
    switch (level) {
        case LogLevel::TRACE: return "TRACE";
        case LogLevel::DEBUG: return "DEBUG";
        case LogLevel::INFO: return "INFO";
        case LogLevel::WARNING: return "WARNING";
        case LogLevel::ERROR: return "ERROR";
        case LogLevel::CRITICAL: return "CRITICAL";
        default: return "UNKNOWN";
    }
}

/// Structured log entry with metadata
struct LogEntry {
    LogLevel level;
    std::chrono::system_clock::time_point timestamp;
    std::string message;
    std::string component;  // Which component logged this (e.g., "VersaAICore", "ModelingAgent")
    std::string threadId;
    std::unordered_map<std::string, std::string> context;  // Additional key-value context

    LogEntry() = default;

    LogEntry(LogLevel lvl, std::string msg, std::string comp = "")
        : level(lvl)
        , timestamp(std::chrono::system_clock::now())
        , message(std::move(msg))
        , component(std::move(comp)) {
        std::ostringstream oss;
        oss << std::this_thread::get_id();
        threadId = oss.str();
    }

    /// Add context key-value pair
    LogEntry& addContext(const std::string& key, const std::string& value) {
        context[key] = value;
        return *this;
    }

    /// Format as human-readable string
    std::string format() const;

    /// Format as JSON for structured logging
    std::string toJson() const;
};

/// Logger configuration
struct LoggerConfig {
    LogLevel minLevel = LogLevel::INFO;
    bool enableConsole = true;
    bool enableFile = true;
    std::string logFilePath = "versaai.log";
    bool jsonFormat = false;
    size_t batchSize = 100;  // Flush after this many entries
    size_t maxQueueSize = 10000;  // Drop logs if queue exceeds this
    std::chrono::milliseconds flushInterval{1000};  // Flush every 1 second
};

/// Production-grade async logger with batching
class Logger {
public:
    /// Get singleton instance
    static Logger& getInstance();

    /// Initialize logger with config
    void initialize(const LoggerConfig& config);

    /// Shutdown logger (flush remaining logs)
    void shutdown();

    /// Log a message with level
    void log(LogLevel level, const std::string& message, const std::string& component = "");

    /// Log a structured entry
    void log(const LogEntry& entry);

    /// Convenience methods for each level
    void trace(const std::string& message, const std::string& component = "");
    void debug(const std::string& message, const std::string& component = "");
    void info(const std::string& message, const std::string& component = "");
    void warning(const std::string& message, const std::string& component = "");
    void error(const std::string& message, const std::string& component = "");
    void critical(const std::string& message, const std::string& component = "");

    /// Set minimum log level
    void setMinLevel(LogLevel level);

    /// Get current configuration
    const LoggerConfig& getConfig() const { return config_; }

    /// Flush logs immediately
    void flush();

    // Prevent copying
    Logger(const Logger&) = delete;
    Logger& operator=(const Logger&) = delete;

private:
    Logger() = default;
    ~Logger();

    void workerThread();
    void writeEntry(const LogEntry& entry);
    void writeBatch(const std::vector<LogEntry>& batch);

    LoggerConfig config_;
    std::queue<LogEntry> logQueue_;
    std::mutex queueMutex_;
    std::condition_variable queueCondition_;
    std::unique_ptr<std::thread> workerThread_;
    std::ofstream logFile_;
    bool running_ = false;
    bool initialized_ = false;
};

/// Scoped logger for RAII-style logging (logs duration when destroyed)
class ScopedLogger {
public:
    ScopedLogger(const std::string& operation, const std::string& component = "")
        : operation_(operation)
        , component_(component)
        , start_(std::chrono::high_resolution_clock::now()) {
        Logger::getInstance().debug("Started: " + operation_, component_);
    }

    ~ScopedLogger() {
        auto end = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(end - start_);

        LogEntry entry(LogLevel::DEBUG, "Completed: " + operation_, component_);
        entry.addContext("duration_ms", std::to_string(duration.count()));
        Logger::getInstance().log(entry);
    }

private:
    std::string operation_;
    std::string component_;
    std::chrono::high_resolution_clock::time_point start_;
};

/// Convenience macros for logging with automatic component detection
#define LOG_TRACE(msg) VersaAI::Logger::getInstance().trace(msg, __FILE__)
#define LOG_DEBUG(msg) VersaAI::Logger::getInstance().debug(msg, __FILE__)
#define LOG_INFO(msg) VersaAI::Logger::getInstance().info(msg, __FILE__)
#define LOG_WARNING(msg) VersaAI::Logger::getInstance().warning(msg, __FILE__)
#define LOG_ERROR(msg) VersaAI::Logger::getInstance().error(msg, __FILE__)
#define LOG_CRITICAL(msg) VersaAI::Logger::getInstance().critical(msg, __FILE__)

#define LOG_SCOPE(operation) VersaAI::ScopedLogger _scoped_logger_(operation, __FILE__)

} // namespace VersaAI
