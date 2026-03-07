#pragma once

#include "VersaAIException.hpp"
#include <string>
#include <vector>
#include <unordered_map>
#include <memory>
#include <optional>
#include <cstdint>

namespace VersaAI {

/**
 * @brief Token representation
 */
struct Token {
    int32_t id;                    // Token ID
    std::string text;              // Token text
    float score = 0.0f;            // Token score/probability
    uint32_t offset = 0;           // Character offset in original text
    uint32_t length = 0;           // Length in characters
};

/**
 * @brief Tokenizer type
 */
enum class TokenizerType {
    BPE,            // Byte-Pair Encoding (GPT-2, GPT-3)
    WORDPIECE,      // WordPiece (BERT)
    UNIGRAM,        // Unigram (SentencePiece)
    SENTENCEPIECE,  // SentencePiece (LLaMA, Mistral)
    TIKTOKEN,       // TikToken (GPT-4)
    CUSTOM
};

/**
 * @brief Special tokens used by models
 */
struct SpecialTokens {
    std::optional<int32_t> bos;     // Beginning of sequence
    std::optional<int32_t> eos;     // End of sequence
    std::optional<int32_t> pad;     // Padding
    std::optional<int32_t> unk;     // Unknown token
    std::optional<int32_t> mask;    // Mask token (BERT)
    std::optional<int32_t> cls;     // Classification token (BERT)
    std::optional<int32_t> sep;     // Separator token (BERT)
    
    std::unordered_map<std::string, int32_t> additional;  // Model-specific tokens
};

/**
 * @brief Tokenization configuration
 */
struct TokenizerConfig {
    TokenizerType type = TokenizerType::BPE;
    uint32_t vocabularySize = 0;
    uint32_t maxLength = 2048;
    bool addBos = true;
    bool addEos = true;
    bool lowercase = false;
    bool normalizeUnicode = true;
    std::string unknownToken = "<unk>";
    std::string padToken = "<pad>";
    
    // BPE-specific
    std::string mergesFile;
    
    // SentencePiece-specific
    std::string modelFile;
    
    // Custom patterns
    std::string preTokenizationPattern;
};

/**
 * @brief Production-grade tokenizer base class
 *
 * Features:
 * - Fast BPE/SentencePiece/WordPiece tokenization
 * - Unicode normalization
 * - Special token handling
 * - Batch processing
 * - Vocabulary management
 */
class Tokenizer {
public:
    explicit Tokenizer(const TokenizerConfig& config);
    virtual ~Tokenizer() = default;

    // Disable copy, enable move
    Tokenizer(const Tokenizer&) = delete;
    Tokenizer& operator=(const Tokenizer&) = delete;
    Tokenizer(Tokenizer&&) = default;
    Tokenizer& operator=(Tokenizer&&) = default;

    // ========================================================================
    // Tokenization
    // ========================================================================

    /**
     * @brief Encode text to token IDs
     * @param text Input text
     * @param addSpecialTokens Whether to add BOS/EOS tokens
     * @return Vector of token IDs
     */
    virtual std::vector<int32_t> encode(const std::string& text, bool addSpecialTokens = true);

    /**
     * @brief Encode text with full token information
     * @param text Input text
     * @param addSpecialTokens Whether to add BOS/EOS tokens
     * @return Vector of Token objects with metadata
     */
    virtual std::vector<Token> tokenize(const std::string& text, bool addSpecialTokens = true);

    /**
     * @brief Decode token IDs to text
     * @param ids Token IDs
     * @param skipSpecialTokens Whether to skip special tokens
     * @return Decoded text
     */
    virtual std::string decode(const std::vector<int32_t>& ids, bool skipSpecialTokens = true);

    /**
     * @brief Batch encode multiple texts
     * @param texts Input texts
     * @param addSpecialTokens Whether to add BOS/EOS tokens
     * @param padding Whether to pad to same length
     * @return Batch of token ID vectors
     */
    virtual std::vector<std::vector<int32_t>> encodeBatch(
        const std::vector<std::string>& texts,
        bool addSpecialTokens = true,
        bool padding = false
    );

    /**
     * @brief Batch decode multiple token sequences
     * @param batch Batch of token ID vectors
     * @param skipSpecialTokens Whether to skip special tokens
     * @return Vector of decoded texts
     */
    virtual std::vector<std::string> decodeBatch(
        const std::vector<std::vector<int32_t>>& batch,
        bool skipSpecialTokens = true
    );

    // ========================================================================
    // Vocabulary
    // ========================================================================

    /**
     * @brief Get token ID for text
     * @param token Token text
     * @return Token ID or UNK if not found
     */
    int32_t tokenToId(const std::string& token) const;

    /**
     * @brief Get text for token ID
     * @param id Token ID
     * @return Token text or UNK if invalid
     */
    std::string idToToken(int32_t id) const;

    /**
     * @brief Get vocabulary size
     */
    uint32_t getVocabularySize() const { return config_.vocabularySize; }

    /**
     * @brief Check if token exists in vocabulary
     */
    bool hasToken(const std::string& token) const;

    /**
     * @brief Check if ID is valid
     */
    bool isValidId(int32_t id) const;

    // ========================================================================
    // Special Tokens
    // ========================================================================

    const SpecialTokens& getSpecialTokens() const { return specialTokens_; }

    void setSpecialTokens(const SpecialTokens& tokens) { specialTokens_ = tokens; }

    /**
     * @brief Check if token ID is a special token
     */
    bool isSpecialToken(int32_t id) const;

    /**
     * @brief Get BOS token ID
     */
    std::optional<int32_t> getBosTokenId() const { return specialTokens_.bos; }

    /**
     * @brief Get EOS token ID
     */
    std::optional<int32_t> getEosTokenId() const { return specialTokens_.eos; }

    /**
     * @brief Get PAD token ID
     */
    std::optional<int32_t> getPadTokenId() const { return specialTokens_.pad; }

    // ========================================================================
    // Configuration
    // ========================================================================

    const TokenizerConfig& getConfig() const { return config_; }

    TokenizerType getType() const { return config_.type; }

    // ========================================================================
    // Loading & Saving
    // ========================================================================

    /**
     * @brief Load vocabulary from file
     * @param path Path to vocabulary file
     */
    virtual void loadVocabulary(const std::string& path);

    /**
     * @brief Save vocabulary to file
     * @param path Output path
     */
    virtual void saveVocabulary(const std::string& path) const;

    /**
     * @brief Load from HuggingFace tokenizer.json
     * @param path Path to tokenizer.json
     */
    static std::unique_ptr<Tokenizer> fromHuggingFace(const std::string& path);

    /**
     * @brief Load from SentencePiece model
     * @param path Path to .model file
     */
    static std::unique_ptr<Tokenizer> fromSentencePiece(const std::string& path);

protected:
    TokenizerConfig config_;
    SpecialTokens specialTokens_;
    
    // Vocabulary: token -> ID
    std::unordered_map<std::string, int32_t> tokenToId_;
    
    // Reverse vocabulary: ID -> token
    std::vector<std::string> idToToken_;

    /**
     * @brief Pre-tokenization (split on whitespace, punctuation, etc.)
     */
    virtual std::vector<std::string> preTokenize(const std::string& text);

    /**
     * @brief Normalize text (unicode, lowercase, etc.)
     */
    virtual std::string normalize(const std::string& text);

    /**
     * @brief Post-process token IDs (add special tokens, truncate, etc.)
     */
    virtual std::vector<int32_t> postProcess(std::vector<int32_t> ids, bool addSpecialTokens);

    /**
     * @brief Build vocabulary from token-ID map
     */
    void buildVocabulary();
};

/**
 * @brief BPE (Byte-Pair Encoding) tokenizer implementation
 *
 * Used by GPT-2, GPT-3, RoBERTa, etc.
 */
class BPETokenizer : public Tokenizer {
public:
    explicit BPETokenizer(const TokenizerConfig& config);

    std::vector<int32_t> encode(const std::string& text, bool addSpecialTokens = true) override;
    std::string decode(const std::vector<int32_t>& ids, bool skipSpecialTokens = true) override;

    /**
     * @brief Load BPE merges from file
     * @param path Path to merges file (e.g., merges.txt)
     */
    void loadMerges(const std::string& path);

private:
    // BPE merge rules: (token1, token2) -> merged_token
    std::vector<std::pair<std::string, std::string>> merges_;
    std::unordered_map<std::pair<std::string, std::string>, int32_t, PairHash> mergePriority_;

    struct PairHash {
        size_t operator()(const std::pair<std::string, std::string>& p) const {
            return std::hash<std::string>{}(p.first) ^ (std::hash<std::string>{}(p.second) << 1);
        }
    };

    /**
     * @brief Apply BPE merges to token sequence
     */
    std::vector<std::string> applyBPE(const std::vector<std::string>& tokens);
};

/**
 * @brief SentencePiece tokenizer implementation
 *
 * Used by LLaMA, Mistral, T5, etc.
 */
class SentencePieceTokenizer : public Tokenizer {
public:
    explicit SentencePieceTokenizer(const TokenizerConfig& config);

    std::vector<int32_t> encode(const std::string& text, bool addSpecialTokens = true) override;
    std::string decode(const std::vector<int32_t>& ids, bool skipSpecialTokens = true) override;

    /**
     * @brief Load SentencePiece model
     * @param path Path to .model file
     */
    void loadModel(const std::string& path);

private:
    // Unigram language model probabilities
    std::unordered_map<std::string, float> tokenScores_;

    /**
     * @brief Viterbi algorithm for unigram tokenization
     */
    std::vector<std::string> viterbiTokenize(const std::string& text);
};

/**
 * @brief WordPiece tokenizer implementation
 *
 * Used by BERT, DistilBERT, etc.
 */
class WordPieceTokenizer : public Tokenizer {
public:
    explicit WordPieceTokenizer(const TokenizerConfig& config);

    std::vector<int32_t> encode(const std::string& text, bool addSpecialTokens = true) override;
    std::string decode(const std::vector<int32_t>& ids, bool skipSpecialTokens = true) override;

private:
    std::string wordPiecePrefix_ = "##";  // Continuation marker

    /**
     * @brief Apply WordPiece algorithm
     */
    std::vector<std::string> applyWordPiece(const std::vector<std::string>& tokens);
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * @brief Pad token sequence to length
 */
std::vector<int32_t> padSequence(const std::vector<int32_t>& seq, uint32_t maxLength, int32_t padId);

/**
 * @brief Truncate token sequence to length
 */
std::vector<int32_t> truncateSequence(const std::vector<int32_t>& seq, uint32_t maxLength);

/**
 * @brief Pad batch to same length
 */
std::vector<std::vector<int32_t>> padBatch(const std::vector<std::vector<int32_t>>& batch, int32_t padId);

} // namespace VersaAI
