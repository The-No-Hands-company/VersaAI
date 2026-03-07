#include "VersaAILogger.hpp"
#include <iostream>
#include <thread>

using namespace VersaAI;

void demonstrateBasicLogging() {
    std::cout << "\n=== Basic Logging Demo ===" << std::endl;

    Logger::getInstance().trace("This is a trace message");
    Logger::getInstance().debug("This is a debug message");
    Logger::getInstance().info("This is an info message");
    Logger::getInstance().warning("This is a warning message");
    Logger::getInstance().error("This is an error message");
    Logger::getInstance().critical("This is a critical message");
}

void demonstrateComponentLogging() {
    std::cout << "\n=== Component-Based Logging Demo ===" << std::endl;

    Logger::getInstance().info("Agent initialized", "ModelingAgent");
    Logger::getInstance().debug("Processing task", "VersaAICore");
    Logger::getInstance().warning("High memory usage detected", "MemoryManager");
}

void demonstrateStructuredLogging() {
    std::cout << "\n=== Structured Logging Demo ===" << std::endl;

    LogEntry entry(LogLevel::INFO, "User request processed", "VersaAICore");
    entry.addContext("user_id", "12345")
         .addContext("request_type", "chat")
         .addContext("duration_ms", "125");

    Logger::getInstance().log(entry);
}

void demonstrateScopedLogging() {
    std::cout << "\n=== Scoped Logging Demo ===" << std::endl;

    {
        ScopedLogger scope("Database query", "DatabaseLayer");
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
        // Automatically logs duration when scope exits
    }

    {
        LOG_SCOPE("Complex operation");
        std::this_thread::sleep_for(std::chrono::milliseconds(50));
        // Automatically logs with file name as component
    }
}

void demonstrateMultithreadedLogging() {
    std::cout << "\n=== Multithreaded Logging Demo ===" << std::endl;

    auto worker = [](int id) {
        for (int i = 0; i < 5; ++i) {
            Logger::getInstance().info(
                "Thread " + std::to_string(id) + " iteration " + std::to_string(i),
                "WorkerThread");
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }
    };

    std::thread t1(worker, 1);
    std::thread t2(worker, 2);
    std::thread t3(worker, 3);

    t1.join();
    t2.join();
    t3.join();
}

void demonstrateMacroLogging() {
    std::cout << "\n=== Macro-Based Logging Demo ===" << std::endl;

    LOG_INFO("Using convenience macros for logging");
    LOG_DEBUG("Debug information with automatic file component");
    LOG_WARNING("Warning with file location tracking");
}

int main() {
    // Configure logger
    LoggerConfig config;
    config.minLevel = LogLevel::TRACE;  // Log everything for demo
    config.enableConsole = true;
    config.enableFile = true;
    config.logFilePath = "versaai_demo.log";
    config.jsonFormat = false;  // Human-readable format
    config.batchSize = 10;
    config.flushInterval = std::chrono::milliseconds(500);

    Logger::getInstance().initialize(config);

    std::cout << "VersaAI Logger Demo - Logging to: " << config.logFilePath << std::endl;

    // Run demonstrations
    demonstrateBasicLogging();
    demonstrateComponentLogging();
    demonstrateStructuredLogging();
    demonstrateScopedLogging();
    demonstrateMultithreadedLogging();
    demonstrateMacroLogging();

    std::cout << "\n=== Flushing and shutting down ===" << std::endl;
    Logger::getInstance().flush();

    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    Logger::getInstance().shutdown();

    std::cout << "\nCheck " << config.logFilePath << " for the complete log file." << std::endl;

    return 0;
}
