#include "../../include/VersaAILogger.hpp"
#include <ctime>
#include <iomanip>
#include <iostream>

namespace VersaAI {

// LogEntry implementation

std::string LogEntry::format() const {
    std::ostringstream oss;

    // Format timestamp
    auto time_t = std::chrono::system_clock::to_time_t(timestamp);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()) % 1000;

    std::tm tm_buf;
    #ifdef _WIN32
        localtime_s(&tm_buf, &time_t);
    #else
        localtime_r(&time_t, &tm_buf);
    #endif

    oss << std::put_time(&tm_buf, "%Y-%m-%d %H:%M:%S")
        << '.' << std::setfill('0') << std::setw(3) << ms.count()
        << " [" << logLevelToString(level) << "]";

    if (!component.empty()) {
        oss << " [" << component << "]";
    }

    oss << " [" << threadId << "] " << message;

    // Add context if present
    if (!context.empty()) {
        oss << " {";
        bool first = true;
        for (const auto& [key, value] : context) {
            if (!first) oss << ", ";
            oss << key << "=" << value;
            first = false;
        }
        oss << "}";
    }

    return oss.str();
}

std::string LogEntry::toJson() const {
    std::ostringstream oss;

    // Get timestamp in ISO 8601 format
    auto time_t = std::chrono::system_clock::to_time_t(timestamp);
    auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
        timestamp.time_since_epoch()) % 1000;

    std::tm tm_buf;
    #ifdef _WIN32
        localtime_s(&tm_buf, &time_t);
    #else
        localtime_r(&time_t, &tm_buf);
    #endif

    oss << "{";
    oss << "\"timestamp\":\"";
    oss << std::put_time(&tm_buf, "%Y-%m-%dT%H:%M:%S");
    oss << '.' << std::setfill('0') << std::setw(3) << ms.count() << "Z\",";
    oss << "\"level\":\"" << logLevelToString(level) << "\",";
    oss << "\"message\":\"" << message << "\",";
    oss << "\"component\":\"" << component << "\",";
    oss << "\"thread\":\"" << threadId << "\"";

    // Add context
    if (!context.empty()) {
        oss << ",\"context\":{";
        bool first = true;
        for (const auto& [key, value] : context) {
            if (!first) oss << ",";
            oss << "\"" << key << "\":\"" << value << "\"";
            first = false;
        }
        oss << "}";
    }

    oss << "}";
    return oss.str();
}

// Logger implementation

Logger& Logger::getInstance() {
    static Logger instance;
    return instance;
}

void Logger::initialize(const LoggerConfig& config) {
    if (initialized_) {
        return;  // Already initialized
    }

    {
        std::lock_guard lock(queueMutex_);
        config_ = config;

        // Open log file if file logging is enabled
        if (config_.enableFile) {
            logFile_.open(config_.logFilePath, std::ios::out | std::ios::app);
            if (!logFile_.is_open()) {
                std::cerr << "Failed to open log file: " << config_.logFilePath << std::endl;
                config_.enableFile = false;
            }
        }

        // Start worker thread for async logging
        running_ = true;
        workerThread_ = std::make_unique<std::thread>(&Logger::workerThread, this);

        initialized_ = true;
    }  // Lock released here

    // Log initialization message AFTER releasing the lock
    info("Logger initialized", "VersaAI::Logger");
}

void Logger::shutdown() {
    if (!initialized_) {
        return;
    }

    info("Logger shutting down", "VersaAI::Logger");

    // Stop worker thread
    {
        std::lock_guard lock(queueMutex_);
        running_ = false;
    }
    queueCondition_.notify_all();

    if (workerThread_ && workerThread_->joinable()) {
        workerThread_->join();
    }

    // Flush remaining logs
    flush();

    // Close log file
    if (logFile_.is_open()) {
        logFile_.close();
    }

    initialized_ = false;
}

Logger::~Logger() {
    shutdown();
}

void Logger::log(LogLevel level, const std::string& message, const std::string& component) {
    if (level < config_.minLevel) {
        return;  // Below minimum level
    }

    LogEntry entry(level, message, component);
    log(entry);
}

void Logger::log(const LogEntry& entry) {
    if (entry.level < config_.minLevel) {
        return;
    }

    std::lock_guard lock(queueMutex_);

    // Drop logs if queue is too large
    if (logQueue_.size() >= config_.maxQueueSize) {
        return;
    }

    logQueue_.push(entry);
    queueCondition_.notify_one();
}

void Logger::trace(const std::string& message, const std::string& component) {
    log(LogLevel::TRACE, message, component);
}

void Logger::debug(const std::string& message, const std::string& component) {
    log(LogLevel::DEBUG, message, component);
}

void Logger::info(const std::string& message, const std::string& component) {
    log(LogLevel::INFO, message, component);
}

void Logger::warning(const std::string& message, const std::string& component) {
    log(LogLevel::WARNING, message, component);
}

void Logger::error(const std::string& message, const std::string& component) {
    log(LogLevel::ERROR, message, component);
}

void Logger::critical(const std::string& message, const std::string& component) {
    log(LogLevel::CRITICAL, message, component);
}

void Logger::setMinLevel(LogLevel level) {
    std::lock_guard lock(queueMutex_);
    config_.minLevel = level;
}

void Logger::flush() {
    std::vector<LogEntry> batch;

    {
        std::lock_guard lock(queueMutex_);
        while (!logQueue_.empty()) {
            batch.push_back(logQueue_.front());
            logQueue_.pop();
        }
    }

    if (!batch.empty()) {
        writeBatch(batch);
    }
}

void Logger::workerThread() {
    std::vector<LogEntry> batch;
    batch.reserve(config_.batchSize);

    while (running_) {
        std::unique_lock lock(queueMutex_);

        // Wait for logs or timeout
        queueCondition_.wait_for(lock, config_.flushInterval, [this] {
            return !logQueue_.empty() || !running_;
        });

        // Collect batch
        while (!logQueue_.empty() && batch.size() < config_.batchSize) {
            batch.push_back(logQueue_.front());
            logQueue_.pop();
        }

        lock.unlock();

        // Write batch if we have entries
        if (!batch.empty()) {
            writeBatch(batch);
            batch.clear();
        }
    }
}

void Logger::writeEntry(const LogEntry& entry) {
    std::string formatted = config_.jsonFormat ? entry.toJson() : entry.format();

    // Write to console
    if (config_.enableConsole) {
        if (entry.level >= LogLevel::ERROR) {
            std::cerr << formatted << std::endl;
        } else {
            std::cout << formatted << std::endl;
        }
    }

    // Write to file
    if (config_.enableFile && logFile_.is_open()) {
        logFile_ << formatted << std::endl;
    }
}

void Logger::writeBatch(const std::vector<LogEntry>& batch) {
    for (const auto& entry : batch) {
        writeEntry(entry);
    }

    // Flush file stream
    if (config_.enableFile && logFile_.is_open()) {
        logFile_.flush();
    }
}

} // namespace VersaAI
