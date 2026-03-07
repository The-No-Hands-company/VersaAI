#pragma once

#include "VersaAITensor.hpp"
#include "VersaAITokenizer.hpp"
#include "VersaAIModel.hpp"
#include "VersaAIMemoryPool.hpp"
#include "VersaAIException.hpp"
#include <memory>
#include <vector>
#include <string>
#include <optional>
#include <functional>
#include <unordered_map>
#include <queue>
#include <mutex>
#include <condition_variable>

namespace VersaAI {

// ============================================================================
// KV-Cache Management
// ============================================================================

/**
 * @brief Key-Value cache for transformer attention
 *
 * Stores computed attention keys and values to avoid recomputation
 * during autoregressive generation.
 */
class KVCache {
public:
    KVCache(uint32_t numLayers, uint32_t maxSeqLen, uint32_t numHeads, uint32_t headDim);

    /**
     * @brief Store key-value tensors for a layer
     */
    void store(uint32_t layer, const Tensor& key, const Tensor& value, uint32_t seqPos);

    /**
     * @brief Retrieve cached keys for a layer
     */
    Tensor getKeys(uint32_t layer, uint32_t startPos, uint32_t endPos) const;

    /**
     * @brief Retrieve cached values for a layer
     */
    Tensor getValues(uint32_t layer, uint32_t startPos, uint32_t endPos) const;

    /**
     * @brief Clear cache for specific layer
     */
    void clearLayer(uint32_t layer);

    /**
     * @brief Clear all cached data
     */
    void clear();

    /**
     * @brief Get current sequence length
     */
    uint32_t getSequenceLength() const { return currentSeqLen_; }

    /**
     * @brief Get memory usage in bytes
     */
    size_t getMemoryUsage() const;

    /**
     * @brief Check if cache is full
     */
    bool isFull() const { return currentSeqLen_ >= maxSeqLen_; }

private:
    uint32_t numLayers_;
    uint32_t maxSeqLen_;
    uint32_t numHeads_;
    uint32_t headDim_;
    uint32_t currentSeqLen_;

    // keys[layer] = Tensor of shape [maxSeqLen, numHeads, headDim]
    std::vector<Tensor> keys_;
    
    // values[layer] = Tensor of shape [maxSeqLen, numHeads, headDim]
    std::vector<Tensor> values_;
};

// ============================================================================
// Batch Request
// ============================================================================

/**
 * @brief Single inference request
 */
struct InferenceRequest {
    uint64_t id;                            // Unique request ID
    std::string prompt;                     // Input prompt
    std::vector<int32_t> tokens;            // Tokenized input
    uint32_t maxTokens;                     // Max tokens to generate
    double temperature;                     // Sampling temperature
    double topP;                            // Nucleus sampling threshold
    uint32_t topK;                          // Top-K sampling
    double repetitionPenalty;               // Repetition penalty
    std::vector<int32_t> stopTokens;        // Stop generation tokens
    
    // State
    uint32_t generatedTokens;               // Tokens generated so far
    std::vector<int32_t> outputTokens;      // Generated tokens
    bool finished;                          // Generation complete
    
    // Timing
    std::chrono::system_clock::time_point createdAt;
    std::chrono::system_clock::time_point startedAt;
    std::chrono::system_clock::time_point finishedAt;
    
    // Callback for streaming
    std::function<void(int32_t token)> streamCallback;
};

/**
 * @brief Inference result
 */
struct InferenceResult {
    uint64_t requestId;
    std::string text;                       // Generated text
    std::vector<int32_t> tokens;            // Generated tokens
    uint32_t promptTokens;                  // Input tokens count
    uint32_t completionTokens;              // Output tokens count
    double tokensPerSecond;                 // Generation speed
    double firstTokenLatencyMs;             // Time to first token
    std::chrono::milliseconds totalTime;    // Total inference time
    bool success;
    std::string error;
};

// ============================================================================
// Generation Parameters
// ============================================================================

/**
 * @brief Parameters for text generation
 */
struct GenerationConfig {
    uint32_t maxTokens = 512;               // Maximum tokens to generate
    double temperature = 0.7;               // Sampling temperature (0.0-2.0)
    double topP = 0.9;                      // Nucleus sampling threshold
    uint32_t topK = 40;                     // Top-K sampling
    double repetitionPenalty = 1.0;         // Repetition penalty (1.0 = off)
    uint32_t numBeams = 1;                  // Beam search width (1 = greedy)
    std::vector<int32_t> stopTokens;        // Stop generation tokens
    bool streamOutput = false;              // Stream tokens as generated
    uint32_t seed = 0;                      // Random seed (0 = random)
};

// ============================================================================
// Batch Scheduler
// ============================================================================

/**
 * @brief Continuous batching scheduler for inference
 *
 * Features:
 * - Dynamic batching of requests
 * - Continuous batching (add/remove requests mid-batch)
 * - Priority queue scheduling
 * - KV-cache sharing across requests
 */
class BatchScheduler {
public:
    BatchScheduler(uint32_t maxBatchSize, uint32_t maxSequenceLength);

    /**
     * @brief Add inference request to queue
     */
    uint64_t addRequest(const InferenceRequest& request);

    /**
     * @brief Get next batch of requests to process
     */
    std::vector<InferenceRequest*> getNextBatch();

    /**
     * @brief Mark request as completed
     */
    void completeRequest(uint64_t requestId);

    /**
     * @brief Cancel pending request
     */
    bool cancelRequest(uint64_t requestId);

    /**
     * @brief Get number of pending requests
     */
    size_t getPendingCount() const;

    /**
     * @brief Get number of active requests
     */
    size_t getActiveCount() const;

private:
    uint32_t maxBatchSize_;
    uint32_t maxSequenceLength_;
    uint64_t nextRequestId_;
    
    std::queue<InferenceRequest> pendingRequests_;
    std::unordered_map<uint64_t, InferenceRequest> activeRequests_;
    
    mutable std::mutex mutex_;
    std::condition_variable cv_;
};

// ============================================================================
// Inference Engine
// ============================================================================

/**
 * @brief Production-grade inference engine
 *
 * Features:
 * - Efficient tensor operations
 * - KV-cache management
 * - Continuous batching
 * - Multiple sampling strategies
 * - GPU acceleration support
 * - Speculative decoding ready
 */
class InferenceEngine {
public:
    /**
     * @brief Construct inference engine for a model
     */
    explicit InferenceEngine(std::shared_ptr<ModelBase> model);
    ~InferenceEngine();

    // Disable copy, enable move
    InferenceEngine(const InferenceEngine&) = delete;
    InferenceEngine& operator=(const InferenceEngine&) = delete;
    InferenceEngine(InferenceEngine&&) = default;
    InferenceEngine& operator=(InferenceEngine&&) = default;

    // ========================================================================
    // Synchronous Inference
    // ========================================================================

    /**
     * @brief Generate text from prompt (blocking)
     */
    std::string generate(const std::string& prompt, const GenerationConfig& config = {});

    /**
     * @brief Generate with full result metadata
     */
    InferenceResult generateWithMetrics(const std::string& prompt, const GenerationConfig& config = {});

    /**
     * @brief Get embeddings for text
     */
    Tensor getEmbeddings(const std::string& text);

    // ========================================================================
    // Asynchronous Inference
    // ========================================================================

    /**
     * @brief Submit generation request (non-blocking)
     * @return Request ID for tracking
     */
    uint64_t generateAsync(const std::string& prompt, const GenerationConfig& config,
                           std::function<void(const InferenceResult&)> callback);

    /**
     * @brief Check if async request is complete
     */
    bool isComplete(uint64_t requestId) const;

    /**
     * @brief Get async request result (blocks until complete)
     */
    InferenceResult getResult(uint64_t requestId);

    /**
     * @brief Cancel async request
     */
    bool cancel(uint64_t requestId);

    // ========================================================================
    // Batch Inference
    // ========================================================================

    /**
     * @brief Generate for multiple prompts (batched)
     */
    std::vector<InferenceResult> generateBatch(const std::vector<std::string>& prompts,
                                                const GenerationConfig& config = {});

    // ========================================================================
    // Low-Level Operations
    // ========================================================================

    /**
     * @brief Forward pass through model
     * @param inputIds Token IDs [batchSize, seqLen]
     * @param pastKVCache Optional cached key-values
     * @return Logits tensor [batchSize, seqLen, vocabSize]
     */
    Tensor forward(const Tensor& inputIds, KVCache* pastKVCache = nullptr);

    /**
     * @brief Apply attention layer
     */
    Tensor attention(const Tensor& query, const Tensor& key, const Tensor& value,
                    const Tensor* mask = nullptr);

    /**
     * @brief Apply feed-forward network
     */
    Tensor feedForward(const Tensor& input, const Tensor& weights1,
                      const Tensor& weights2, const Tensor& bias = Tensor());

    /**
     * @brief Apply layer normalization
     */
    Tensor layerNorm(const Tensor& input, const Tensor& weight, const Tensor& bias,
                    double eps = 1e-5);

    // ========================================================================
    // Sampling Strategies
    // ========================================================================

    /**
     * @brief Sample next token using configured strategy
     */
    int32_t sampleToken(const Tensor& logits, const GenerationConfig& config);

    /**
     * @brief Greedy sampling (argmax)
     */
    int32_t greedySample(const Tensor& logits);

    /**
     * @brief Top-K sampling
     */
    int32_t topKSample(const Tensor& logits, uint32_t k, double temperature);

    /**
     * @brief Top-P (nucleus) sampling
     */
    int32_t topPSample(const Tensor& logits, double p, double temperature);

    /**
     * @brief Beam search sampling
     */
    std::vector<int32_t> beamSearch(const std::vector<int32_t>& prefixTokens,
                                    uint32_t numBeams, uint32_t maxLength);

    // ========================================================================
    // Configuration
    // ========================================================================

    /**
     * @brief Set device for computation
     */
    void setDevice(TensorDevice device);

    /**
     * @brief Enable/disable KV-caching
     */
    void enableKVCache(bool enable);

    /**
     * @brief Set maximum batch size
     */
    void setMaxBatchSize(uint32_t size);

    /**
     * @brief Get current configuration
     */
    const GenerationConfig& getDefaultConfig() const { return defaultConfig_; }

    // ========================================================================
    // Performance Monitoring
    // ========================================================================

    /**
     * @brief Get performance metrics
     */
    struct PerformanceStats {
        uint64_t totalRequests = 0;
        uint64_t totalTokensGenerated = 0;
        double avgTokensPerSecond = 0.0;
        double avgFirstTokenLatencyMs = 0.0;
        uint64_t cacheHits = 0;
        uint64_t cacheMisses = 0;
    };

    PerformanceStats getStats() const { return stats_; }

    void resetStats();

    // ========================================================================
    // Resource Management
    // ========================================================================

    /**
     * @brief Clear KV-cache to free memory
     */
    void clearCache();

    /**
     * @brief Get current memory usage
     */
    size_t getMemoryUsage() const;

private:
    std::shared_ptr<ModelBase> model_;
    std::unique_ptr<Tokenizer> tokenizer_;
    std::unique_ptr<KVCache> kvCache_;
    std::unique_ptr<BatchScheduler> scheduler_;
    
    GenerationConfig defaultConfig_;
    TensorDevice device_;
    bool kvCacheEnabled_;
    uint32_t maxBatchSize_;
    
    PerformanceStats stats_;
    mutable std::mutex statsMutex_;

    /**
     * @brief Tokenize input text
     */
    std::vector<int32_t> tokenize(const std::string& text);

    /**
     * @brief Detokenize token IDs
     */
    std::string detokenize(const std::vector<int32_t>& tokens);

    /**
     * @brief Apply softmax with temperature
     */
    Tensor applySoftmax(const Tensor& logits, double temperature);

    /**
     * @brief Apply repetition penalty to logits
     */
    void applyRepetitionPenalty(Tensor& logits, const std::vector<int32_t>& previousTokens,
                                double penalty);

    /**
     * @brief Check if generation should stop
     */
    bool shouldStop(const std::vector<int32_t>& tokens, const GenerationConfig& config);

    /**
     * @brief Update performance statistics
     */
    void updateStats(const InferenceResult& result);
};

// ============================================================================
// Attention Mechanisms
// ============================================================================

/**
 * @brief Multi-head self-attention
 */
class MultiHeadAttention {
public:
    MultiHeadAttention(uint32_t numHeads, uint32_t headDim, uint32_t modelDim);

    /**
     * @brief Forward pass
     */
    Tensor forward(const Tensor& input, const Tensor* mask = nullptr,
                  KVCache* cache = nullptr, uint32_t layer = 0);

    /**
     * @brief Load attention weights
     */
    void loadWeights(const Tensor& qWeight, const Tensor& kWeight,
                    const Tensor& vWeight, const Tensor& outWeight);

private:
    uint32_t numHeads_;
    uint32_t headDim_;
    uint32_t modelDim_;
    
    Tensor qWeight_;     // Query projection
    Tensor kWeight_;     // Key projection
    Tensor vWeight_;     // Value projection
    Tensor outWeight_;   // Output projection

    /**
     * @brief Scaled dot-product attention
     */
    Tensor scaledDotProductAttention(const Tensor& Q, const Tensor& K, const Tensor& V,
                                     const Tensor* mask = nullptr);

    /**
     * @brief Split tensor into multiple heads
     */
    Tensor splitHeads(const Tensor& input);

    /**
     * @brief Merge multiple heads
     */
    Tensor mergeHeads(const Tensor& input);
};

/**
 * @brief Rotary positional embeddings (RoPE)
 */
class RotaryEmbedding {
public:
    RotaryEmbedding(uint32_t dim, uint32_t maxSeqLen, double base = 10000.0);

    /**
     * @brief Apply rotary embeddings to query/key
     */
    Tensor apply(const Tensor& input, uint32_t seqOffset = 0);

private:
    uint32_t dim_;
    uint32_t maxSeqLen_;
    double base_;
    
    Tensor freqs_;  // Pre-computed frequencies

    void computeFrequencies();
};

} // namespace VersaAI
