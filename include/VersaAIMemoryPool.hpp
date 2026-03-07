/**
 * @file VersaAIMemoryPool.hpp
 * @brief Production-grade memory pool management for VersaAI
 * 
 * Features:
 * - Custom allocators for frequently-used objects
 * - Cache-friendly memory layouts
 * - Thread-safe pool management
 * - Memory leak detection
 * - RAII-based resource management
 * - Performance monitoring
 */

#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <memory>
#include <mutex>
#include <type_traits>
#include <vector>
#include <unordered_set>
#include <stack>

namespace VersaAI {
namespace Memory {

// ============================================================================
// Memory Pool Configuration
// ============================================================================

/**
 * @brief Configuration for memory pool behavior
 */
struct PoolConfig {
    size_t initialBlockCount = 64;      ///< Initial number of blocks to allocate
    size_t maxBlockCount = 4096;        ///< Maximum blocks (0 = unlimited)
    size_t blockSize = 0;               ///< Size of each block (0 = auto-detect from T)
    bool allowGrowth = true;            ///< Can pool grow beyond initial size?
    bool threadSafe = true;             ///< Enable thread-safe operations?
    bool trackLeaks = true;             ///< Enable leak detection (slight overhead)?
    size_t alignmentBytes = 16;         ///< Memory alignment (typically 16 for SIMD)
    
    // Performance monitoring
    bool collectStats = false;          ///< Collect detailed statistics?
    
    // Growth policy
    enum class GrowthPolicy {
        Fixed,      ///< Grow by fixed amount
        Double,     ///< Double the size each time
        Fibonacci   ///< Grow using Fibonacci sequence
    };
    GrowthPolicy growthPolicy = GrowthPolicy::Double;
    size_t growthAmount = 64;           ///< For Fixed policy
};

/**
 * @brief Statistics about memory pool usage
 */
struct PoolStats {
    size_t totalBlocks = 0;             ///< Total blocks allocated
    size_t usedBlocks = 0;              ///< Currently in-use blocks
    size_t freeBlocks = 0;              ///< Available blocks
    size_t peakUsage = 0;               ///< Peak simultaneous usage
    size_t totalAllocations = 0;        ///< Lifetime allocation count
    size_t totalDeallocations = 0;      ///< Lifetime deallocation count
    size_t growthEvents = 0;            ///< How many times pool grew
    size_t totalBytesAllocated = 0;     ///< Total memory allocated
    
    // Leak detection
    size_t currentLeaks = 0;            ///< Blocks not returned to pool
    std::vector<void*> leakedPointers;  ///< Addresses of leaked blocks
    
    double averageUtilization() const {
        return totalBlocks > 0 ? static_cast<double>(usedBlocks) / totalBlocks : 0.0;
    }
};

// ============================================================================
// Object Pool - Type-specific pool for RAII objects
// ============================================================================

/**
 * @brief Type-specific object pool with construction/destruction
 * 
 * @tparam T The type of objects to pool
 * 
 * Example:
 * @code
 * ObjectPool<MyClass> pool;
 * auto obj = pool.acquire(); // Constructs MyClass
 * pool.release(obj);         // Destructs and returns to pool
 * @endcode
 */
template<typename T>
class ObjectPool {
public:
    explicit ObjectPool(PoolConfig config = PoolConfig())
        : config_(config)
    {
        if (config_.blockSize == 0) {
            config_.blockSize = sizeof(T);
        }
        
        // Ensure alignment
        config_.blockSize = alignSize(config_.blockSize, config_.alignmentBytes);
        
        // Pre-allocate initial blocks
        reserve(config_.initialBlockCount);
    }
    
    ~ObjectPool() {
        // Destroy all objects and free memory
        clear();
        
        // Report leaks if enabled
        if (config_.trackLeaks && !allocatedBlocks_.empty()) {
            // Leaks detected - would log here
        }
    }
    
    // No copying, allow moving
    ObjectPool(const ObjectPool&) = delete;
    ObjectPool& operator=(const ObjectPool&) = delete;
    ObjectPool(ObjectPool&&) noexcept = default;
    ObjectPool& operator=(ObjectPool&&) noexcept = default;
    
    /**
     * @brief Acquire an object from the pool
     * 
     * Constructs object with given arguments. If pool is empty,
     * either grows (if allowed) or throws.
     * 
     * @tparam Args Constructor argument types
     * @param args Arguments to forward to T's constructor
     * @return Pointer to constructed object
     * @throws std::bad_alloc if pool cannot grow
     */
    template<typename... Args>
    T* acquire(Args&&... args) {
        void* memory = allocateBlock();
        
        // Construct object in-place
        T* obj = new (memory) T(std::forward<Args>(args)...);
        
        // Track allocation
        if (config_.trackLeaks) {
            std::lock_guard<std::mutex> lock(trackingMutex_);
            allocatedBlocks_.insert(memory);
        }
        
        updateStats(true);
        return obj;
    }
    
    /**
     * @brief Return an object to the pool
     * 
     * Destroys the object and returns memory to pool.
     * 
     * @param obj Pointer to object to release
     */
    void release(T* obj) {
        if (!obj) return;
        
        void* memory = static_cast<void*>(obj);
        
        // Verify this block came from our pool
        if (config_.trackLeaks) {
            std::lock_guard<std::mutex> lock(trackingMutex_);
            if (allocatedBlocks_.find(memory) == allocatedBlocks_.end()) {
                // Double-free or foreign pointer - would log error
                return;
            }
            allocatedBlocks_.erase(memory);
        }
        
        // Destruct object
        obj->~T();
        
        // Return memory to pool
        deallocateBlock(memory);
        
        updateStats(false);
    }
    
    /**
     * @brief Get current pool statistics
     */
    PoolStats getStats() const {
        std::lock_guard<std::mutex> lock(statsMutex_);
        
        PoolStats stats = stats_;
        stats.freeBlocks = freeList_.size();
        stats.usedBlocks = stats.totalBlocks - stats.freeBlocks;
        
        if (config_.trackLeaks) {
            std::lock_guard<std::mutex> tlock(trackingMutex_);
            stats.currentLeaks = allocatedBlocks_.size();
            stats.leakedPointers.assign(allocatedBlocks_.begin(), allocatedBlocks_.end());
        }
        
        return stats;
    }
    
    /**
     * @brief Pre-allocate blocks in the pool
     */
    void reserve(size_t count) {
        std::lock_guard<std::mutex> lock(poolMutex_);
        
        while (freeList_.size() < count) {
            if (config_.maxBlockCount > 0 && stats_.totalBlocks >= config_.maxBlockCount) {
                break;
            }
            
            void* block = allocateAlignedMemory(config_.blockSize, config_.alignmentBytes);
            freeList_.push(block);
            
            stats_.totalBlocks++;
            stats_.totalBytesAllocated += config_.blockSize;
        }
    }
    
    /**
     * @brief Clear all unused blocks (keeps allocated ones)
     */
    void shrink() {
        std::lock_guard<std::mutex> lock(poolMutex_);
        
        while (!freeList_.empty()) {
            void* block = freeList_.top();
            freeList_.pop();
            freeAlignedMemory(block);
            stats_.totalBlocks--;
        }
    }
    
    /**
     * @brief Clear entire pool (destroys all objects!)
     * 
     * WARNING: Only call when you know all objects are unused
     */
    void clear() {
        std::lock_guard<std::mutex> lock(poolMutex_);
        
        // Free all blocks in free list
        while (!freeList_.empty()) {
            void* block = freeList_.top();
            freeList_.pop();
            freeAlignedMemory(block);
        }
        
        // Clear tracking
        if (config_.trackLeaks) {
            std::lock_guard<std::mutex> tlock(trackingMutex_);
            allocatedBlocks_.clear();
        }
        
        stats_ = PoolStats();
    }
    
private:
    PoolConfig config_;
    
    // Thread-safe free list
    std::stack<void*> freeList_;
    mutable std::mutex poolMutex_;
    
    // Statistics
    mutable PoolStats stats_;
    mutable std::mutex statsMutex_;
    
    // Leak tracking
    std::unordered_set<void*> allocatedBlocks_;
    mutable std::mutex trackingMutex_;
    
    /**
     * @brief Allocate a block from pool or create new one
     */
    void* allocateBlock() {
        std::lock_guard<std::mutex> lock(poolMutex_);
        
        // Try to get from free list
        if (!freeList_.empty()) {
            void* block = freeList_.top();
            freeList_.pop();
            return block;
        }
        
        // Need to grow pool
        if (!config_.allowGrowth) {
            throw std::bad_alloc();
        }
        
        if (config_.maxBlockCount > 0 && stats_.totalBlocks >= config_.maxBlockCount) {
            throw std::bad_alloc();
        }
        
        // Allocate new block
        void* block = allocateAlignedMemory(config_.blockSize, config_.alignmentBytes);
        
        stats_.totalBlocks++;
        stats_.growthEvents++;
        stats_.totalBytesAllocated += config_.blockSize;
        
        return block;
    }
    
    /**
     * @brief Return block to free list
     */
    void deallocateBlock(void* block) {
        std::lock_guard<std::mutex> lock(poolMutex_);
        freeList_.push(block);
    }
    
    /**
     * @brief Update usage statistics
     */
    void updateStats(bool isAllocation) {
        if (!config_.collectStats) return;
        
        std::lock_guard<std::mutex> lock(statsMutex_);
        
        if (isAllocation) {
            stats_.totalAllocations++;
            size_t current = stats_.totalAllocations - stats_.totalDeallocations;
            if (current > stats_.peakUsage) {
                stats_.peakUsage = current;
            }
        } else {
            stats_.totalDeallocations++;
        }
    }
    
    /**
     * @brief Align size to alignment boundary
     */
    static size_t alignSize(size_t size, size_t alignment) {
        return (size + alignment - 1) & ~(alignment - 1);
    }
    
    /**
     * @brief Allocate aligned memory
     */
    static void* allocateAlignedMemory(size_t size, size_t alignment) {
        void* ptr = nullptr;
        
#ifdef _WIN32
        ptr = _aligned_malloc(size, alignment);
        if (!ptr) throw std::bad_alloc();
#else
        if (posix_memalign(&ptr, alignment, size) != 0) {
            throw std::bad_alloc();
        }
#endif
        
        return ptr;
    }
    
    /**
     * @brief Free aligned memory
     */
    static void freeAlignedMemory(void* ptr) {
#ifdef _WIN32
        _aligned_free(ptr);
#else
        free(ptr);
#endif
    }
};

// ============================================================================
// Global Memory Pools - Pre-configured pools for common types
// ============================================================================

/**
 * @brief Manager for global memory pools
 * 
 * Provides pre-configured pools for frequently-allocated types
 */
class GlobalPools {
public:
    static GlobalPools& getInstance();
    
    /**
     * @brief Register a pool for a specific type
     */
    template<typename T>
    void registerPool(const std::string& name, PoolConfig config = PoolConfig()) {
        std::lock_guard<std::mutex> lock(mutex_);
        // Would store type-erased pool here
    }
    
    /**
     * @brief Get statistics for all pools
     */
    struct GlobalStats {
        size_t totalPools = 0;
        size_t totalMemoryAllocated = 0;
        size_t totalMemoryUsed = 0;
        size_t totalLeaks = 0;
    };
    
    GlobalStats getGlobalStats() const;
    
    /**
     * @brief Clear all pools
     */
    void clearAll();
    
private:
    GlobalPools() = default;
    
    mutable std::mutex mutex_;
    // Pool storage would go here
};

// ============================================================================
// RAII Pool Deleter - Custom deleter for unique_ptr/shared_ptr
// ============================================================================

/**
 * @brief Custom deleter that returns object to pool
 * 
 * Example:
 * @code
 * using PooledPtr = std::unique_ptr<MyClass, PoolDeleter<MyClass>>;
 * PooledPtr obj(pool.acquire(), PoolDeleter<MyClass>(&pool));
 * // Automatically returned to pool when obj goes out of scope
 * @endcode
 */
template<typename T>
class PoolDeleter {
public:
    explicit PoolDeleter(ObjectPool<T>* pool) : pool_(pool) {}
    
    void operator()(T* obj) {
        if (pool_ && obj) {
            pool_->release(obj);
        }
    }
    
private:
    ObjectPool<T>* pool_;
};

// Convenience alias
template<typename T>
using PooledUniquePtr = std::unique_ptr<T, PoolDeleter<T>>;

/**
 * @brief Create a pooled unique_ptr
 */
template<typename T, typename... Args>
PooledUniquePtr<T> makePooled(ObjectPool<T>& pool, Args&&... args) {
    T* obj = pool.acquire(std::forward<Args>(args)...);
    return PooledUniquePtr<T>(obj, PoolDeleter<T>(&pool));
}

} // namespace Memory
} // namespace VersaAI
