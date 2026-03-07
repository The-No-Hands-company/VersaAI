/**
 * @file VersaAIDependencyInjection.hpp
 * @brief Production-grade Dependency Injection framework for VersaAI
 * 
 * Features:
 * - Type-safe dependency registration
 * - Singleton and transient lifetimes
 * - Lazy initialization
 * - Circular dependency detection
 * - Constructor injection
 * - Factory-based creation
 * - Thread-safe operations
 * - Hierarchical containers (scopes)
 */

#pragma once

#include "VersaAIException.hpp"
#include <any>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <type_traits>
#include <typeindex>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace VersaAI {
namespace DI {

// ============================================================================
// Service Lifetime
// ============================================================================

/**
 * @brief Defines how long a service instance lives
 */
enum class ServiceLifetime {
    /**
     * @brief Single instance shared across all requests
     * Created on first request, destroyed on container destruction
     */
    Singleton,
    
    /**
     * @brief New instance created for each request
     */
    Transient,
    
    /**
     * @brief Single instance per scope
     * Each scope has its own instance
     */
    Scoped
};

// ============================================================================
// Service Descriptor
// ============================================================================

/**
 * @brief Describes how to create and manage a service
 */
class ServiceDescriptor {
public:
    using Factory = std::function<std::any(class ServiceProvider&)>;
    
    ServiceDescriptor(
        std::type_index serviceType,
        Factory factory,
        ServiceLifetime lifetime
    )
        : serviceType_(serviceType)
        , factory_(std::move(factory))
        , lifetime_(lifetime)
    {}
    
    std::type_index getServiceType() const { return serviceType_; }
    ServiceLifetime getLifetime() const { return lifetime_; }
    
    std::any create(ServiceProvider& provider) const {
        return factory_(provider);
    }
    
private:
    std::type_index serviceType_;
    Factory factory_;
    ServiceLifetime lifetime_;
};

// ============================================================================
// Service Provider (Resolver)
// ============================================================================

/**
 * @brief Resolves and creates service instances
 * 
 * Thread-safe service resolution with:
 * - Lifetime management
 * - Circular dependency detection
 * - Lazy initialization
 * - Scope support
 */
class ServiceProvider {
public:
    explicit ServiceProvider(std::vector<ServiceDescriptor> descriptors)
        : descriptors_(std::move(descriptors))
        , isDisposed_(false)
    {
        // Build service type index
        for (size_t i = 0; i < descriptors_.size(); ++i) {
            serviceIndex_[descriptors_[i].getServiceType()] = i;
        }
    }
    
    ~ServiceProvider() {
        dispose();
    }
    
    // No copying, allow moving
    ServiceProvider(const ServiceProvider&) = delete;
    ServiceProvider& operator=(const ServiceProvider&) = delete;
    ServiceProvider(ServiceProvider&&) noexcept = default;
    ServiceProvider& operator=(ServiceProvider&&) noexcept = default;
    
    /**
     * @brief Get service instance
     * 
     * @tparam T Service type
     * @return Pointer to service instance
     * @throws RegistryException if service not registered
     * @throws RegistryException if circular dependency detected
     */
    template<typename T>
    std::shared_ptr<T> getService() {
        return getService<T>(std::type_index(typeid(T)));
    }
    
    /**
     * @brief Try to get service instance
     * 
     * @tparam T Service type
     * @return Pointer to service instance, or nullptr if not found
     */
    template<typename T>
    std::shared_ptr<T> tryGetService() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (isDisposed_) {
            return nullptr;
        }
        
        auto it = serviceIndex_.find(std::type_index(typeid(T)));
        if (it == serviceIndex_.end()) {
            return nullptr;
        }
        
        try {
            return getServiceInternal<T>(it->second);
        } catch (...) {
            return nullptr;
        }
    }
    
    /**
     * @brief Get all services of a type
     * 
     * Useful for getting all registered implementations of an interface
     */
    template<typename T>
    std::vector<std::shared_ptr<T>> getServices() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        std::vector<std::shared_ptr<T>> services;
        auto typeIndex = std::type_index(typeid(T));
        
        for (size_t i = 0; i < descriptors_.size(); ++i) {
            if (descriptors_[i].getServiceType() == typeIndex) {
                services.push_back(getServiceInternal<T>(i));
            }
        }
        
        return services;
    }
    
    /**
     * @brief Create a scope for scoped services
     * 
     * @return New service provider with scoped lifetime
     */
    std::unique_ptr<ServiceProvider> createScope() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        // Create new provider with same descriptors
        auto scope = std::make_unique<ServiceProvider>(descriptors_);
        scope->rootProvider_ = rootProvider_ ? rootProvider_ : this;
        
        return scope;
    }
    
    /**
     * @brief Dispose of all singleton instances
     */
    void dispose() {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (isDisposed_) return;
        
        singletonInstances_.clear();
        scopedInstances_.clear();
        
        isDisposed_ = true;
    }
    
    /**
     * @brief Check if a service is registered
     */
    template<typename T>
    bool isRegistered() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return serviceIndex_.find(std::type_index(typeid(T))) != serviceIndex_.end();
    }
    
private:
    std::vector<ServiceDescriptor> descriptors_;
    std::unordered_map<std::type_index, size_t> serviceIndex_;
    
    // Singleton storage
    std::unordered_map<size_t, std::any> singletonInstances_;
    
    // Scoped storage
    std::unordered_map<size_t, std::any> scopedInstances_;
    
    // Circular dependency detection
    std::unordered_set<size_t> resolutionStack_;
    
    // Thread safety
    mutable std::mutex mutex_;
    
    // Disposed flag
    bool isDisposed_;
    
    // Root provider (for scoped services)
    ServiceProvider* rootProvider_ = nullptr;
    
    /**
     * @brief Internal service resolution
     */
    template<typename T>
    std::shared_ptr<T> getService(std::type_index typeIndex) {
        std::lock_guard<std::mutex> lock(mutex_);
        
        if (isDisposed_) {
            throw RegistryException(
                "ServiceProvider has been disposed",
                ErrorCode::REGISTRY_DISPOSED
            );
        }
        
        auto it = serviceIndex_.find(typeIndex);
        if (it == serviceIndex_.end()) {
            throw RegistryException(
                "Service not registered: " + std::string(typeIndex.name()),
                ErrorCode::REGISTRY_NOT_FOUND
            );
        }
        
        return getServiceInternal<T>(it->second);
    }
    
    /**
     * @brief Internal service creation with lifetime management
     */
    template<typename T>
    std::shared_ptr<T> getServiceInternal(size_t descriptorIndex) {
        const auto& descriptor = descriptors_[descriptorIndex];
        auto lifetime = descriptor.getLifetime();
        
        // Check for circular dependency
        if (resolutionStack_.find(descriptorIndex) != resolutionStack_.end()) {
            throw RegistryException(
                "Circular dependency detected for service: " + 
                std::string(descriptor.getServiceType().name()),
                ErrorCode::REGISTRY_CIRCULAR_DEPENDENCY
            );
        }
        
        // Handle based on lifetime
        switch (lifetime) {
            case ServiceLifetime::Singleton:
                return getSingleton<T>(descriptorIndex, descriptor);
                
            case ServiceLifetime::Scoped:
                return getScoped<T>(descriptorIndex, descriptor);
                
            case ServiceLifetime::Transient:
                return createTransient<T>(descriptorIndex, descriptor);
        }
        
        throw RegistryException(
            "Unknown service lifetime",
            ErrorCode::REGISTRY_INTERNAL_ERROR
        );
    }
    
    /**
     * @brief Get or create singleton instance
     */
    template<typename T>
    std::shared_ptr<T> getSingleton(size_t descriptorIndex, const ServiceDescriptor& descriptor) {
        auto it = singletonInstances_.find(descriptorIndex);
        if (it != singletonInstances_.end()) {
            return std::any_cast<std::shared_ptr<T>>(it->second);
        }
        
        // Create new singleton
        auto instance = createInstance<T>(descriptorIndex, descriptor);
        singletonInstances_[descriptorIndex] = instance;
        
        return instance;
    }
    
    /**
     * @brief Get or create scoped instance
     */
    template<typename T>
    std::shared_ptr<T> getScoped(size_t descriptorIndex, const ServiceDescriptor& descriptor) {
        auto it = scopedInstances_.find(descriptorIndex);
        if (it != scopedInstances_.end()) {
            return std::any_cast<std::shared_ptr<T>>(it->second);
        }
        
        // Create new scoped instance
        auto instance = createInstance<T>(descriptorIndex, descriptor);
        scopedInstances_[descriptorIndex] = instance;
        
        return instance;
    }
    
    /**
     * @brief Create transient instance (always new)
     */
    template<typename T>
    std::shared_ptr<T> createTransient(size_t descriptorIndex, const ServiceDescriptor& descriptor) {
        return createInstance<T>(descriptorIndex, descriptor);
    }
    
    /**
     * @brief Create instance using factory
     */
    template<typename T>
    std::shared_ptr<T> createInstance(size_t descriptorIndex, const ServiceDescriptor& descriptor) {
        // Add to resolution stack
        resolutionStack_.insert(descriptorIndex);
        
        try {
            // Call factory
            std::any instance = descriptor.create(*this);
            
            // Remove from resolution stack
            resolutionStack_.erase(descriptorIndex);
            
            return std::any_cast<std::shared_ptr<T>>(instance);
            
        } catch (...) {
            // Clean up resolution stack
            resolutionStack_.erase(descriptorIndex);
            throw;
        }
    }
};

// ============================================================================
// Service Collection (Builder)
// ============================================================================

/**
 * @brief Builds a collection of service descriptors
 * 
 * Fluent API for service registration
 */
class ServiceCollection {
public:
    /**
     * @brief Register service with type
     * 
     * @tparam TService Service type (interface)
     * @tparam TImplementation Implementation type (concrete class)
     * @param lifetime Service lifetime
     * @return Reference to this collection (for chaining)
     */
    template<typename TService, typename TImplementation = TService>
    ServiceCollection& add(ServiceLifetime lifetime = ServiceLifetime::Transient) {
        static_assert(
            std::is_base_of<TService, TImplementation>::value ||
            std::is_same<TService, TImplementation>::value,
            "TImplementation must derive from TService"
        );
        
        auto factory = [](ServiceProvider& provider) -> std::any {
            return std::static_pointer_cast<TService>(
                std::make_shared<TImplementation>()
            );
        };
        
        descriptors_.emplace_back(
            std::type_index(typeid(TService)),
            factory,
            lifetime
        );
        
        return *this;
    }
    
    /**
     * @brief Register service with factory function
     * 
     * @tparam TService Service type
     * @param factory Factory function that creates service
     * @param lifetime Service lifetime
     */
    template<typename TService>
    ServiceCollection& add(
        std::function<std::shared_ptr<TService>(ServiceProvider&)> factory,
        ServiceLifetime lifetime = ServiceLifetime::Transient
    ) {
        auto anyFactory = [factory](ServiceProvider& provider) -> std::any {
            return std::static_pointer_cast<TService>(factory(provider));
        };
        
        descriptors_.emplace_back(
            std::type_index(typeid(TService)),
            anyFactory,
            lifetime
        );
        
        return *this;
    }
    
    /**
     * @brief Register singleton service
     */
    template<typename TService, typename TImplementation = TService>
    ServiceCollection& addSingleton() {
        return add<TService, TImplementation>(ServiceLifetime::Singleton);
    }
    
    /**
     * @brief Register singleton with factory
     */
    template<typename TService>
    ServiceCollection& addSingleton(
        std::function<std::shared_ptr<TService>(ServiceProvider&)> factory
    ) {
        return add<TService>(factory, ServiceLifetime::Singleton);
    }
    
    /**
     * @brief Register scoped service
     */
    template<typename TService, typename TImplementation = TService>
    ServiceCollection& addScoped() {
        return add<TService, TImplementation>(ServiceLifetime::Scoped);
    }
    
    /**
     * @brief Register scoped with factory
     */
    template<typename TService>
    ServiceCollection& addScoped(
        std::function<std::shared_ptr<TService>(ServiceProvider&)> factory
    ) {
        return add<TService>(factory, ServiceLifetime::Scoped);
    }
    
    /**
     * @brief Register transient service
     */
    template<typename TService, typename TImplementation = TService>
    ServiceCollection& addTransient() {
        return add<TService, TImplementation>(ServiceLifetime::Transient);
    }
    
    /**
     * @brief Register transient with factory
     */
    template<typename TService>
    ServiceCollection& addTransient(
        std::function<std::shared_ptr<TService>(ServiceProvider&)> factory
    ) {
        return add<TService>(factory, ServiceLifetime::Transient);
    }
    
    /**
     * @brief Build service provider from collection
     */
    std::unique_ptr<ServiceProvider> buildServiceProvider() {
        return std::make_unique<ServiceProvider>(std::move(descriptors_));
    }
    
    /**
     * @brief Get number of registered services
     */
    size_t count() const {
        return descriptors_.size();
    }
    
    /**
     * @brief Clear all registrations
     */
    void clear() {
        descriptors_.clear();
    }
    
private:
    std::vector<ServiceDescriptor> descriptors_;
};

// ============================================================================
// Convenience Macros for Registration
// ============================================================================

/**
 * @brief Helper to register service with dependencies
 * 
 * Example:
 * @code
 * services.add<ILogger, ConsoleLogger>()
 *         .add<IDatabase, SqlDatabase>()
 *         .add<IService>([](ServiceProvider& sp) {
 *             return std::make_shared<MyService>(
 *                 sp.getService<ILogger>(),
 *                 sp.getService<IDatabase>()
 *             );
 *         });
 * @endcode
 */

} // namespace DI
} // namespace VersaAI
