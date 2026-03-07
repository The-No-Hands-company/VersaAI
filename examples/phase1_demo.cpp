/**
 * @file phase1_demo.cpp
 * @brief Demonstration of Phase 1 infrastructure components
 * 
 * Shows how to use:
 * - Memory pools for performance
 * - Dependency injection for flexibility
 * - Component registry for lifecycle management
 * - Enhanced context for state management
 */

#include "VersaAIMemoryPool.hpp"
#include "VersaAIDependencyInjection.hpp"
#include "VersaAIRegistry.hpp"
#include "VersaAIContext_v2.hpp"
#include "VersaAILogger.hpp"
#include <iostream>
#include <memory>
#include <string>

using namespace VersaAI;
using namespace VersaAI::Memory;
using namespace VersaAI::DI;
using namespace VersaAI::Registry;

// ============================================================================
// Example Components
// ============================================================================

/**
 * @brief Logger interface
 */
class ILogger {
public:
    virtual ~ILogger() = default;
    virtual void log(const std::string& message) = 0;
};

/**
 * @brief Console logger implementation
 */
class ConsoleLogger : public ILogger {
public:
    void log(const std::string& message) override {
        std::cout << "[LOG] " << message << std::endl;
    }
};

/**
 * @brief Database interface
 */
class IDatabase {
public:
    virtual ~IDatabase() = default;
    virtual bool connect(const std::string& connectionString) = 0;
    virtual void disconnect() = 0;
    virtual bool isConnected() const = 0;
};

/**
 * @brief Mock database implementation with lifecycle hooks
 */
class MockDatabase : public IDatabase, 
                      public IInitializable, 
                      public IShutdownable,
                      public IHotReloadable {
public:
    MockDatabase() = default;
    
    // IDatabase implementation
    bool connect(const std::string& connectionString) override {
        connectionString_ = connectionString;
        connected_ = true;
        std::cout << "Connected to database: " << connectionString << std::endl;
        return true;
    }
    
    void disconnect() override {
        connected_ = false;
        std::cout << "Disconnected from database" << std::endl;
    }
    
    bool isConnected() const override {
        return connected_;
    }
    
    // IInitializable implementation
    bool initialize() override {
        std::cout << "Initializing MockDatabase..." << std::endl;
        return connect("mock://localhost:5432/versaai");
    }
    
    int getInitializationPriority() const override {
        return 100; // Initialize early
    }
    
    // IShutdownable implementation
    void shutdown() override {
        std::cout << "Shutting down MockDatabase..." << std::endl;
        disconnect();
    }
    
    int getShutdownPriority() const override {
        return 900; // Shutdown late (let others use it first)
    }
    
    // IHotReloadable implementation
    bool reload() override {
        std::cout << "Reloading database configuration..." << std::endl;
        disconnect();
        return connect(connectionString_);
    }
    
private:
    bool connected_ = false;
    std::string connectionString_;
};

/**
 * @brief Service that uses pooled objects
 */
struct Message {
    std::string content;
    int priority;
    
    Message(const std::string& c = "", int p = 0)
        : content(c), priority(p)
    {
        std::cout << "Message constructed: " << content << std::endl;
    }
    
    ~Message() {
        std::cout << "Message destructed: " << content << std::endl;
    }
};

/**
 * @brief Message processor with DI dependencies
 */
class MessageProcessor : public IInitializable {
public:
    MessageProcessor(
        std::shared_ptr<ILogger> logger,
        std::shared_ptr<IDatabase> database
    )
        : logger_(logger)
        , database_(database)
        , messagePool_(PoolConfig{
            .initialBlockCount = 32,
            .maxBlockCount = 128,
            .trackLeaks = true
        })
    {
        std::cout << "MessageProcessor constructed" << std::endl;
    }
    
    bool initialize() override {
        std::cout << "Initializing MessageProcessor..." << std::endl;
        logger_->log("MessageProcessor initialized");
        return true;
    }
    
    int getInitializationPriority() const override {
        return 200; // After database
    }
    
    void processMessage(const std::string& content, int priority) {
        logger_->log("Processing message: " + content);
        
        // Get message from pool
        auto message = messagePool_.acquire(content, priority);
        
        // Simulate processing
        if (database_->isConnected()) {
            logger_->log("Stored message in database");
        }
        
        // Return to pool
        messagePool_.release(message);
        
        // Show pool stats
        auto stats = messagePool_.getStats();
        std::cout << "Pool stats - Used: " << stats.usedBlocks 
                  << ", Free: " << stats.freeBlocks 
                  << ", Total: " << stats.totalBlocks << std::endl;
    }
    
    void processMessageRAII(const std::string& content, int priority) {
        logger_->log("Processing message (RAII): " + content);
        
        // Use RAII wrapper - automatically returned to pool
        auto message = makePooled(messagePool_, content, priority);
        
        // Simula processing
        if (database_->isConnected()) {
            logger_->log("Stored message in database");
        }
        
        // Automatically returned to pool when message goes out of scope
    }
    
private:
    std::shared_ptr<ILogger> logger_;
    std::shared_ptr<IDatabase> database_;
    ObjectPool<Message> messagePool_;
};

// ============================================================================
// Demo Functions
// ============================================================================

void demo_memory_pools() {
    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "DEMO 1: Memory Pools" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    
    // Create pool
    PoolConfig config;
    config.initialBlockCount = 4;
    config.trackLeaks = true;
    config.collectStats = true;
    
    ObjectPool<Message> pool(config);
    
    std::cout << "\n1. Manual allocation/deallocation:" << std::endl;
    auto msg1 = pool.acquire("Hello", 1);
    auto msg2 = pool.acquire("World", 2);
    
    pool.release(msg1);
    pool.release(msg2);
    
    std::cout << "\n2. RAII style (automatic return):" << std::endl;
    {
        auto msg = makePooled(pool, "RAII Message", 5);
        std::cout << "  Message in scope: " << msg->content << std::endl;
    }
    std::cout << "  Message returned to pool automatically" << std::endl;
    
    std::cout << "\n3. Pool statistics:" << std::endl;
    auto stats = pool.getStats();
    std::cout << "  Total blocks: " << stats.totalBlocks << std::endl;
    std::cout << "  Used blocks: " << stats.usedBlocks << std::endl;
    std::cout << "  Free blocks: " << stats.freeBlocks << std::endl;
    std::cout << "  Total allocations: " << stats.totalAllocations << std::endl;
    std::cout << "  Peak usage: " << stats.peakUsage << std::endl;
}

void demo_dependency_injection() {
    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "DEMO 2: Dependency Injection" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    
    ServiceCollection services;
    
    // Register services
    std::cout << "\n1. Registering services:" << std::endl;
    services.addSingleton<ILogger, ConsoleLogger>();
    services.addSingleton<IDatabase, MockDatabase>();
    
    // Register with factory for custom construction
    services.add<MessageProcessor>(
        [](ServiceProvider& sp) {
            return std::make_shared<MessageProcessor>(
                sp.getService<ILogger>(),
                sp.getService<IDatabase>()
            );
        },
        ServiceLifetime::Singleton
    );
    
    std::cout << "  Registered " << services.count() << " services" << std::endl;
    
    // Build provider
    std::cout << "\n2. Building service provider:" << std::endl;
    auto provider = services.buildServiceProvider();
    
    // Resolve services (dependencies auto-injected)
    std::cout << "\n3. Resolving services:" << std::endl;
    auto processor = provider->getService<MessageProcessor>();
    
    // Verify singleton behavior
    std::cout << "\n4. Verifying singleton lifetime:" << std::endl;
    auto processor2 = provider->getService<MessageProcessor>();
    std::cout << "  Same instance? " << (processor.get() == processor2.get() ? "Yes" : "No") << std::endl;
    
    // Create scope
    std::cout << "\n5. Creating scope:" << std::endl;
    auto scope = provider->createScope();
    auto scopedProcessor = scope->getService<MessageProcessor>();
    std::cout << "  Same as root? " << (processor.get() == scopedProcessor.get() ? "Yes" : "No") << std::endl;
}

void demo_component_registry() {
    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "DEMO 3: Component Registry with Lifecycle" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    
    auto& registry = ComponentRegistry::getInstance();
    
    // Register components
    std::cout << "\n1. Registering components:" << std::endl;
    registry.registerComponent<ILogger, ConsoleLogger>("logger", ServiceLifetime::Singleton);
    registry.registerComponent<IDatabase, MockDatabase>("database", ServiceLifetime::Singleton);
    registry.registerComponent<MessageProcessor>(
        "processor",
        [](ServiceProvider& sp) {
            return std::make_shared<MessageProcessor>(
                sp.getService<ILogger>(),
                sp.getService<IDatabase>()
            );
        },
        ServiceLifetime::Singleton
    );
    
    // Initialize all components (in priority order)
    std::cout << "\n2. Initializing all components:" << std::endl;
    bool success = registry.initializeAll();
    std::cout << "  Initialization " << (success ? "succeeded" : "failed") << std::endl;
    
    // Get and use component
    std::cout << "\n3. Using components:" << std::endl;
    auto processor = registry.getComponent<MessageProcessor>();
    processor->processMessage("Test message", 1);
    
    // Show metadata
    std::cout << "\n4. Component metadata:" << std::endl;
    auto meta = registry.getMetadata("database");
    std::cout << "  Name: " << meta.name << std::endl;
    std::cout << "  State: " << static_cast<int>(meta.state) << std::endl;
    std::cout << "  Access count: " << meta.accessCount << std::endl;
    std::cout << "  Is initializable: " << (meta.isInitializable ? "Yes" : "No") << std::endl;
    std::cout << "  Is shutdownable: " << (meta.isShutdownable ? "Yes" : "No") << std::endl;
    std::cout << "  Is hot-reloadable: " << (meta.isHotReloadable ? "Yes" : "No") << std::endl;
    
    // Shutdown all
    std::cout << "\n5. Shutting down components:" << std::endl;
    registry.shutdownAll();
}

void demo_context_system() {
    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "DEMO 4: Enhanced Context System" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    
    VersaAIContextV2 context;
    
    // Store different types
    std::cout << "\n1. Storing values:" << std::endl;
    context.set("username", std::string("alice"), "session.user");
    context.set("score", int64_t(42), "game.stats");
    context.set("ratio", 3.14, "game.stats");
    context.set("isActive", true, "session");
    
    // Retrieve typed values
    std::cout << "\n2. Retrieving typed values:" << std::endl;
    auto username = context.getTyped<std::string>("username", "session.user");
    auto score = context.getTyped<int64_t>("score", "game.stats");
    auto ratio = context.getTyped<double>("ratio", "game.stats");
    auto isActive = context.getTyped<bool>("isActive", "session");
    
    std::cout << "  Username: " << (username ? *username : "not found") << std::endl;
    std::cout << "  Score: " << (score ? std::to_string(*score) : "not found") << std::endl;
    std::cout << "  Ratio: " << (ratio ? std::to_string(*ratio) : "not found") << std::endl;
    std::cout << "  Active: " << (isActive ? (*isActive ? "true" : "false") : "not found") << std::endl;
    
    // Create snapshot
    std::cout << "\n3. Creating snapshot:" << std::endl;
    auto snapshotId = context.createSnapshot();
    std::cout << "  Snapshot ID: " << snapshotId << std::endl;
    
    // Modify context
    std::cout << "\n4. Modifying context:" << std::endl;
    context.set("score", int64_t(100), "game.stats");
    auto newScore = context.getTyped<int64_t>("score", "game.stats");
    std::cout << "  New score: " << *newScore << std::endl;
    
    // Rollback
    std::cout << "\n5. Rolling back to snapshot:" << std::endl;
    context.rollbackToSnapshot(snapshotId);
    auto rolledBackScore = context.getTyped<int64_t>("score", "game.stats");
    std::cout << "  Rolled back score: " << *rolledBackScore << std::endl;
    
    // Statistics
    std::cout << "\n6. Context statistics:" << std::endl;
    auto stats = context.getStats();
    std::cout << "  Total entries: " << stats.totalEntries << std::endl;
    std::cout << "  Total namespaces: " << stats.totalNamespaces << std::endl;
    std::cout << "  Total snapshots: " << stats.totalSnapshots << std::endl;
}

void demo_integrated_system() {
    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "DEMO 5: Integrated System" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    
    // Initialize logger
    Logger::getInstance().initialize({
        .minLevel = LogLevel::DEBUG,
        .outputFile = "",  // Console only
        .enableAsync = true
    });
    
    // Set up registry
    auto& registry = ComponentRegistry::getInstance();
    registry.registerComponent<ILogger, ConsoleLogger>("logger");
    registry.registerComponent<IDatabase, MockDatabase>("database");
    registry.registerComponent<MessageProcessor>(
        "processor",
        [](ServiceProvider& sp) {
            return std::make_shared<MessageProcessor>(
                sp.getService<ILogger>(),
                sp.getService<IDatabase>()
            );
        }
    );
    
    // Initialize all
    registry.initializeAll();
    
    // Use context
    VersaAIContextV2 context;
    context.set("session_id", std::string("sess_12345"), "session");
    
    // Process messages
    auto processor = registry.getComponent<MessageProcessor>();
    processor->processMessageRAII("Integrated message 1", 1);
    processor->processMessageRAII("Integrated message 2", 2);
    
    // Cleanup
    registry.shutdownAll();
    Logger::getInstance().shutdown();
}

// ============================================================================
// Main
// ============================================================================

int main() {
    std::cout << "\n" << std::string(80, '=') << std::endl;
    std::cout << "VersaAI Phase 1 Infrastructure Demo" << std::endl;
    std::cout << std::string(80, '=') << std::endl;
    
    try {
        demo_memory_pools();
        demo_dependency_injection();
        demo_component_registry();
        demo_context_system();
        demo_integrated_system();
        
        std::cout << "\n" << std::string(80, '=') << std::endl;
        std::cout << "All demos completed successfully!" << std::endl;
        std::cout << std::string(80, '=') << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "\nError: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}
