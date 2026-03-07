#pragma once
#include <string>
#include <vector>
#include <unordered_set>
#include <regex>
#include <memory>
#include <mutex>
#include <fstream>
#include <sstream>

namespace VersaAI {

/**
 * @brief Enforces the AI Behavior Mandate across all VersaAI components
 *
 * This class implements production-grade behavior enforcement for AI agents,
 * ensuring that all responses adhere to expert-level, production-grade standards
 * as defined in AI_BEHAVIOR_MANDATE.md.
 *
 * Thread-safety: This class is thread-safe for concurrent access.
 */
class BehaviorPolicy {
public:
  /**
   * @brief Severity levels for policy violations
   */
  enum class ViolationSeverity {
    CRITICAL,   // Must be rejected (placeholders, TODO comments)
    HIGH,       // Strong discouraged (simplifications, workarounds)
    MEDIUM,     // Warning level (incomplete documentation)
    LOW         // Advisory (style preferences)
  };

  /**
   * @brief Represents a detected policy violation
   */
  struct Violation {
    ViolationSeverity severity;
    std::string rule_name;
    std::string description;
    std::string detected_pattern;
    size_t position;  // Position in text where violation occurs

    Violation(ViolationSeverity sev, const std::string& rule,
              const std::string& desc, const std::string& pattern, size_t pos)
      : severity(sev), rule_name(rule), description(desc),
        detected_pattern(pattern), position(pos) {}
  };

  /**
   * @brief Policy enforcement result
   */
  struct ValidationResult {
    bool is_compliant;
    std::vector<Violation> violations;
    double quality_score;  // 0.0 to 100.0
    std::string suggestion;  // How to fix violations

    ValidationResult()
      : is_compliant(true), quality_score(100.0) {}
  };

  /**
   * @brief Configuration for policy enforcement
   */
  struct PolicyConfig {
    bool allow_placeholders = false;
    bool allow_todos = false;
    bool allow_simplifications = false;
    bool enforce_error_handling = true;
    bool enforce_documentation = true;
    bool enforce_production_quality = true;
    ViolationSeverity minimum_severity_to_reject = ViolationSeverity::CRITICAL;

    // User can explicitly request exceptions
    bool user_requested_mvp = false;
    bool user_requested_prototype = false;
    bool user_requested_simplified = false;
  };

  static BehaviorPolicy& getInstance();

  /**
   * @brief Loads the AI Behavior Mandate from file
   * @param mandate_file_path Path to AI_BEHAVIOR_MANDATE.md
   * @return true if successfully loaded
   */
  bool loadMandate(const std::string& mandate_file_path);

  /**
   * @brief Validates agent response against behavior mandate
   * @param response The agent's response text
   * @param context_type Type of task (code, documentation, design, etc.)
   * @return Validation result with violations and suggestions
   */
  ValidationResult validateResponse(const std::string& response,
                                     const std::string& context_type = "general") const;

  /**
   * @brief Validates code against production quality standards
   * @param code Code snippet to validate
   * @param language Programming language (cpp, python, etc.)
   * @return Validation result specific to code quality
   */
  ValidationResult validateCode(const std::string& code,
                                 const std::string& language) const;

  /**
   * @brief Generates system prompt incorporating behavior mandate
   * @param base_role Base role description for the agent
   * @param task_context Specific task context
   * @return Complete system prompt with mandate enforcement
   */
  std::string generateSystemPrompt(const std::string& base_role,
                                    const std::string& task_context = "") const;

  /**
   * @brief Augments user input with mandate reminders when appropriate
   * @param user_input Original user input
   * @return Augmented input with context-appropriate mandate guidance
   */
  std::string augmentUserInput(const std::string& user_input) const;

  /**
   * @brief Sets policy configuration
   */
  void setConfig(const PolicyConfig& config);

  /**
   * @brief Gets current policy configuration
   */
  const PolicyConfig& getConfig() const { return config_; }

  /**
   * @brief Detects if user explicitly requested an exception (MVP, prototype, etc.)
   * @param user_input User's message
   * @return true if user requested exception
   */
  bool detectUserException(const std::string& user_input) const;

  /**
   * @brief Gets the core mandate principles as a string
   */
  std::string getMandatePrinciples() const;

  /**
   * @brief Gets forbidden patterns for a specific context
   */
  std::vector<std::string> getForbiddenPatterns(const std::string& context_type) const;

  /**
   * @brief Gets required patterns for a specific context
   */
  std::vector<std::string> getRequiredPatterns(const std::string& context_type) const;

private:
  BehaviorPolicy();
  ~BehaviorPolicy() = default;

  // Prevent copying
  BehaviorPolicy(const BehaviorPolicy&) = delete;
  BehaviorPolicy& operator=(const BehaviorPolicy&) = delete;

  // Validation helpers
  ValidationResult validateForbiddenBehaviors(const std::string& text) const;
  ValidationResult validateRequiredBehaviors(const std::string& text,
                                              const std::string& context_type) const;
  ValidationResult validateCodeQuality(const std::string& code,
                                        const std::string& language) const;

  // Pattern detection
  bool containsPlaceholders(const std::string& text) const;
  bool containsTODOs(const std::string& text) const;
  bool containsSimplificationLanguage(const std::string& text) const;
  bool containsWorkarounds(const std::string& text) const;
  bool containsMVPThinking(const std::string& text) const;
  bool hasProperErrorHandling(const std::string& code, const std::string& language) const;
  bool hasProperDocumentation(const std::string& code) const;

  // Score calculation
  double calculateQualityScore(const std::vector<Violation>& violations) const;
  std::string generateSuggestions(const std::vector<Violation>& violations) const;

  // Mandate content
  std::string mandate_content_;
  std::string core_principles_;
  PolicyConfig config_;

  // Compiled regex patterns for efficient matching
  mutable std::vector<std::regex> placeholder_patterns_;
  mutable std::vector<std::regex> todo_patterns_;
  mutable std::vector<std::regex> simplification_patterns_;
  mutable std::vector<std::regex> workaround_patterns_;
  mutable std::vector<std::regex> mvp_patterns_;
  mutable std::vector<std::regex> exception_request_patterns_;

  // Initialize patterns
  void initializePatterns();

  // Thread safety (if needed for future concurrent access)
  mutable std::mutex validation_mutex_;
};

} // namespace VersaAI
