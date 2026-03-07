#include "BehaviorPolicy.hpp"
#include <algorithm>
#include <cctype>
#include <iostream>

namespace VersaAI {

BehaviorPolicy::BehaviorPolicy() {
  initializePatterns();

  // Set default core principles
  core_principles_ = R"(
PRODUCTION-GRADE MANDATE:
- Default to expert-level, complete implementations
- No placeholders, TODOs, or incomplete code
- No simplifications unless explicitly requested
- Apply SOLID principles and industry best practices
- Comprehensive error handling for all edge cases
- Complete documentation with usage examples
- Optimal algorithms and data structures
- Thread-safe and memory-efficient
)";
}

BehaviorPolicy& BehaviorPolicy::getInstance() {
  static BehaviorPolicy instance;
  return instance;
}

bool BehaviorPolicy::loadMandate(const std::string& mandate_file_path) {
  std::ifstream file(mandate_file_path);
  if (!file.is_open()) {
    std::cerr << "Warning: Could not load AI Behavior Mandate from: "
              << mandate_file_path << std::endl;
    return false;
  }

  std::stringstream buffer;
  buffer << file.rdbuf();
  mandate_content_ = buffer.str();

  // Extract core principles section
  size_t principles_start = mandate_content_.find("## Core Principle:");
  size_t principles_end = mandate_content_.find("## Forbidden Behaviors");
  if (principles_start != std::string::npos && principles_end != std::string::npos) {
    core_principles_ = mandate_content_.substr(principles_start,
                                                principles_end - principles_start);
  }

  return true;
}

void BehaviorPolicy::initializePatterns() {
  // Placeholder patterns (CRITICAL violations)
  placeholder_patterns_ = {
    std::regex(R"(//\s*placeholder)", std::regex::icase),
    std::regex(R"(#\s*placeholder)", std::regex::icase),
    std::regex(R"(\bplaceholder\s+for\b)", std::regex::icase),
    std::regex(R"(\bstub\s+implementation\b)", std::regex::icase),
    std::regex(R"(\btemporary\s+implementation\b)", std::regex::icase),
    std::regex(R"(pass\s*#\s*stub)", std::regex::icase)
  };

  // TODO patterns (CRITICAL violations)
  todo_patterns_ = {
    std::regex(R"(//\s*TODO)", std::regex::icase),
    std::regex(R"(#\s*TODO)", std::regex::icase),
    std::regex(R"(/\*\s*TODO)", std::regex::icase),
    std::regex(R"(\bFIXME\b)", std::regex::icase),
    std::regex(R"(\bHACK\b)", std::regex::icase),
    std::regex(R"(\bXXX\b)"),
    std::regex(R"(implement\s+this\s+later)", std::regex::icase),
    std::regex(R"(add\s+this\s+later)", std::regex::icase),
    std::regex(R"(we\s+can\s+add.*later)", std::regex::icase)
  };

  // Simplification language (HIGH violations)
  simplification_patterns_ = {
    std::regex(R"(let'?s\s+start\s+with\s+a?\s*simpler?)", std::regex::icase),
    std::regex(R"(for\s+now,?\s+we\s+can\s+just)", std::regex::icase),
    std::regex(R"(to\s+make\s+this\s+easier)", std::regex::icase),
    std::regex(R"(a\s+basic\s+implementation)", std::regex::icase),
    std::regex(R"(simple\s+version)", std::regex::icase),
    std::regex(R"(simplified\s+approach)", std::regex::icase),
    std::regex(R"(quick\s+and\s+dirty)", std::regex::icase),
    std::regex(R"(good\s+enough\s+for\s+now)", std::regex::icase)
  };

  // Workaround language (HIGH violations)
  workaround_patterns_ = {
    std::regex(R"(we\s+can\s+work\s*around)", std::regex::icase),
    std::regex(R"(a\s+quick\s+fix)", std::regex::icase),
    std::regex(R"(this\s+hack)", std::regex::icase),
    std::regex(R"(temporary\s+fix)", std::regex::icase),
    std::regex(R"(work\s*around\s+this\s+by)", std::regex::icase),
    std::regex(R"(as\s+a\s+workaround)", std::regex::icase)
  };

  // MVP/Prototype thinking (HIGH violations)
  mvp_patterns_ = {
    std::regex(R"(let'?s\s+get\s+it\s+working\s+first)", std::regex::icase),
    std::regex(R"(we\s+can\s+optimize\s+later)", std::regex::icase),
    std::regex(R"(for\s+version\s+1)", std::regex::icase),
    std::regex(R"(minimum\s+viable)", std::regex::icase),
    std::regex(R"(\bMVP\b)"),
    std::regex(R"(prototype\s+implementation)", std::regex::icase),
    std::regex(R"(meets\s+the\s+minimum\s+requirements)", std::regex::icase),
    std::regex(R"(sufficient\s+for\s+now)", std::regex::icase)
  };

  // User exception requests (these are ALLOWED)
  exception_request_patterns_ = {
    std::regex(R"(give\s+me\s+a\s+quick\s+prototype)", std::regex::icase),
    std::regex(R"(just\s+a\s+minimal.*example)", std::regex::icase),
    std::regex(R"(simplified\s+version\s+for\s+learning)", std::regex::icase),
    std::regex(R"(placeholder.*is\s+fine)", std::regex::icase),
    std::regex(R"(MVP\s+approach)", std::regex::icase),
    std::regex(R"(quick\s+hack\s+for\s+testing)", std::regex::icase),
    std::regex(R"(temporary.*is\s+okay)", std::regex::icase)
  };
}

bool BehaviorPolicy::containsPlaceholders(const std::string& text) const {
  for (const auto& pattern : placeholder_patterns_) {
    if (std::regex_search(text, pattern)) {
      return true;
    }
  }
  return false;
}

bool BehaviorPolicy::containsTODOs(const std::string& text) const {
  for (const auto& pattern : todo_patterns_) {
    if (std::regex_search(text, pattern)) {
      return true;
    }
  }
  return false;
}

bool BehaviorPolicy::containsSimplificationLanguage(const std::string& text) const {
  for (const auto& pattern : simplification_patterns_) {
    if (std::regex_search(text, pattern)) {
      return true;
    }
  }
  return false;
}

bool BehaviorPolicy::containsWorkarounds(const std::string& text) const {
  for (const auto& pattern : workaround_patterns_) {
    if (std::regex_search(text, pattern)) {
      return true;
    }
  }
  return false;
}

bool BehaviorPolicy::containsMVPThinking(const std::string& text) const {
  for (const auto& pattern : mvp_patterns_) {
    if (std::regex_search(text, pattern)) {
      return true;
    }
  }
  return false;
}

bool BehaviorPolicy::detectUserException(const std::string& user_input) const {
  for (const auto& pattern : exception_request_patterns_) {
    if (std::regex_search(user_input, pattern)) {
      return true;
    }
  }
  return false;
}

BehaviorPolicy::ValidationResult BehaviorPolicy::validateForbiddenBehaviors(
    const std::string& text) const {

  ValidationResult result;
  std::vector<Violation> violations;

  // Check for placeholders (CRITICAL)
  if (!config_.allow_placeholders && containsPlaceholders(text)) {
    for (const auto& pattern : placeholder_patterns_) {
      std::smatch match;
      std::string::const_iterator search_start(text.cbegin());
      while (std::regex_search(search_start, text.cend(), match, pattern)) {
        violations.emplace_back(
          ViolationSeverity::CRITICAL,
          "NO_PLACEHOLDERS",
          "Placeholder code detected. Implement complete functionality.",
          match.str(),
          std::distance(text.cbegin(), search_start) + match.position()
        );
        search_start = match.suffix().first;
      }
    }
  }

  // Check for TODOs (CRITICAL)
  if (!config_.allow_todos && containsTODOs(text)) {
    for (const auto& pattern : todo_patterns_) {
      std::smatch match;
      std::string::const_iterator search_start(text.cbegin());
      while (std::regex_search(search_start, text.cend(), match, pattern)) {
        violations.emplace_back(
          ViolationSeverity::CRITICAL,
          "NO_TODOS",
          "TODO comment detected. Complete implementation now, not later.",
          match.str(),
          std::distance(text.cbegin(), search_start) + match.position()
        );
        search_start = match.suffix().first;
      }
    }
  }

  // Check for simplification language (HIGH)
  if (!config_.allow_simplifications && containsSimplificationLanguage(text)) {
    for (const auto& pattern : simplification_patterns_) {
      std::smatch match;
      if (std::regex_search(text, match, pattern)) {
        violations.emplace_back(
          ViolationSeverity::HIGH,
          "NO_SIMPLIFICATIONS",
          "Simplification language detected. Provide complete, expert-level solution.",
          match.str(),
          match.position()
        );
      }
    }
  }

  // Check for workarounds (HIGH)
  if (containsWorkarounds(text)) {
    for (const auto& pattern : workaround_patterns_) {
      std::smatch match;
      if (std::regex_search(text, match, pattern)) {
        violations.emplace_back(
          ViolationSeverity::HIGH,
          "NO_WORKAROUNDS",
          "Workaround detected. Solve the root cause properly.",
          match.str(),
          match.position()
        );
      }
    }
  }

  // Check for MVP thinking (HIGH)
  if (containsMVPThinking(text)) {
    for (const auto& pattern : mvp_patterns_) {
      std::smatch match;
      if (std::regex_search(text, match, pattern)) {
        violations.emplace_back(
          ViolationSeverity::HIGH,
          "NO_MVP_THINKING",
          "MVP/prototype thinking detected. Build production-grade from start.",
          match.str(),
          match.position()
        );
      }
    }
  }

  result.violations = violations;
  result.quality_score = calculateQualityScore(violations);
  result.is_compliant = violations.empty() ||
                        (violations[0].severity < config_.minimum_severity_to_reject);
  result.suggestion = generateSuggestions(violations);

  return result;
}

bool BehaviorPolicy::hasProperErrorHandling(const std::string& code,
                                             const std::string& language) const {
  if (language == "cpp" || language == "c++") {
    // Check for try-catch blocks
    bool has_try_catch = code.find("try {") != std::string::npos ||
                         code.find("try{") != std::string::npos;

    // Check for error return values
    bool has_error_checks = code.find("if (") != std::string::npos &&
                           (code.find("== nullptr") != std::string::npos ||
                            code.find("!= nullptr") != std::string::npos ||
                            code.find(".has_value()") != std::string::npos ||
                            code.find("== -1") != std::string::npos);

    return has_try_catch || has_error_checks;
  } else if (language == "python") {
    return code.find("try:") != std::string::npos ||
           code.find("except ") != std::string::npos;
  }

  return true; // Assume compliance for unknown languages
}

bool BehaviorPolicy::hasProperDocumentation(const std::string& code) const {
  // Check for doc comments
  bool has_cpp_docs = code.find("/**") != std::string::npos ||
                      code.find("///") != std::string::npos;
  bool has_python_docs = code.find("\"\"\"") != std::string::npos;

  // Check for @brief, @param, etc.
  bool has_doxygen = code.find("@brief") != std::string::npos ||
                     code.find("@param") != std::string::npos ||
                     code.find("@return") != std::string::npos;

  return has_cpp_docs || has_python_docs || has_doxygen;
}

BehaviorPolicy::ValidationResult BehaviorPolicy::validateCode(
    const std::string& code, const std::string& language) const {

  ValidationResult result = validateForbiddenBehaviors(code);

  // Additional code-specific checks
  if (config_.enforce_error_handling && !hasProperErrorHandling(code, language)) {
    result.violations.emplace_back(
      ViolationSeverity::HIGH,
      "MISSING_ERROR_HANDLING",
      "Code lacks comprehensive error handling. Add try-catch or proper validation.",
      "No error handling detected",
      0
    );
  }

  if (config_.enforce_documentation && !hasProperDocumentation(code)) {
    result.violations.emplace_back(
      ViolationSeverity::MEDIUM,
      "MISSING_DOCUMENTATION",
      "Code lacks proper documentation. Add doc comments with @brief, @param, @return.",
      "No documentation found",
      0
    );
  }

  // Check for empty or stub implementations
  std::regex empty_func(R"(\{\s*\})");
  std::regex return_empty(R"(return\s+[0\"\'\[\]\{\}];)");

  if (std::regex_search(code, empty_func) || std::regex_search(code, return_empty)) {
    result.violations.emplace_back(
      ViolationSeverity::CRITICAL,
      "EMPTY_IMPLEMENTATION",
      "Empty or stub function detected. Implement complete functionality.",
      "Empty function body",
      0
    );
  }

  result.quality_score = calculateQualityScore(result.violations);
  result.is_compliant = result.violations.empty() ||
                        (result.violations[0].severity < config_.minimum_severity_to_reject);
  result.suggestion = generateSuggestions(result.violations);

  return result;
}

BehaviorPolicy::ValidationResult BehaviorPolicy::validateResponse(
    const std::string& response, const std::string& context_type) const {

  // If user requested exception, skip validation
  if (config_.user_requested_mvp || config_.user_requested_prototype ||
      config_.user_requested_simplified) {
    ValidationResult result;
    result.is_compliant = true;
    result.quality_score = 100.0;
    result.suggestion = "User requested exception - validation skipped.";
    return result;
  }

  // Perform standard validation
  return validateForbiddenBehaviors(response);
}

double BehaviorPolicy::calculateQualityScore(
    const std::vector<Violation>& violations) const {

  if (violations.empty()) {
    return 100.0;
  }

  double penalty = 0.0;
  for (const auto& violation : violations) {
    switch (violation.severity) {
      case ViolationSeverity::CRITICAL:
        penalty += 30.0;
        break;
      case ViolationSeverity::HIGH:
        penalty += 15.0;
        break;
      case ViolationSeverity::MEDIUM:
        penalty += 7.5;
        break;
      case ViolationSeverity::LOW:
        penalty += 2.5;
        break;
    }
  }

  return std::max(0.0, 100.0 - penalty);
}

std::string BehaviorPolicy::generateSuggestions(
    const std::vector<Violation>& violations) const {

  if (violations.empty()) {
    return "Code meets production quality standards.";
  }

  std::stringstream ss;
  ss << "Fix the following violations:\n";

  for (size_t i = 0; i < violations.size() && i < 5; ++i) {
    const auto& v = violations[i];
    ss << "  - [" << v.rule_name << "] " << v.description << "\n";
  }

  if (violations.size() > 5) {
    ss << "  ... and " << (violations.size() - 5) << " more violations.\n";
  }

  return ss.str();
}

std::string BehaviorPolicy::generateSystemPrompt(
    const std::string& base_role, const std::string& task_context) const {

  std::stringstream prompt;

  prompt << "You are " << base_role << ".\n\n";

  prompt << "# AI BEHAVIOR MANDATE - PRODUCTION-GRADE ONLY\n\n";
  prompt << core_principles_ << "\n\n";

  prompt << "## Forbidden Behaviors (NEVER do these):\n";
  prompt << "- NO placeholders or TODO comments\n";
  prompt << "- NO simplifications or 'basic versions'\n";
  prompt << "- NO workarounds or hacks\n";
  prompt << "- NO MVP/prototype thinking\n";
  prompt << "- NO incomplete implementations\n";
  prompt << "- NO missing error handling\n\n";

  prompt << "## Required Behaviors (ALWAYS do these):\n";
  prompt << "- Complete, production-ready implementations\n";
  prompt << "- Comprehensive error handling for all edge cases\n";
  prompt << "- Optimal algorithms and data structures\n";
  prompt << "- Full documentation with examples\n";
  prompt << "- Thread-safe and memory-efficient code\n";
  prompt << "- SOLID principles and best practices\n\n";

  if (!task_context.empty()) {
    prompt << "## Task Context:\n" << task_context << "\n\n";
  }

  prompt << "## Quality Standard:\n";
  prompt << "Ask yourself: 'Would this pass code review at Google/Meta/Microsoft?'\n";
  prompt << "If not, refactor until it does.\n\n";

  return prompt.str();
}

std::string BehaviorPolicy::augmentUserInput(const std::string& user_input) const {
  // Check if this is a development-related request
  std::regex dev_keywords(R"(\b(implement|create|build|develop|code|function|class|add)\b)",
                          std::regex::icase);

  if (!std::regex_search(user_input, dev_keywords)) {
    return user_input;  // Not a development request, no augmentation needed
  }

  // Check if user requested an exception
  if (detectUserException(user_input)) {
    return user_input + "\n\n[NOTE: User requested exception to production standards]";
  }

  // Augment with mandate reminder
  std::stringstream augmented;
  augmented << user_input << "\n\n";
  augmented << "[MANDATE: Provide complete, production-grade implementation. ";
  augmented << "No placeholders, TODOs, or simplifications. ";
  augmented << "Include comprehensive error handling and documentation.]";

  return augmented.str();
}

void BehaviorPolicy::setConfig(const PolicyConfig& config) {
  config_ = config;
}

std::string BehaviorPolicy::getMandatePrinciples() const {
  return core_principles_;
}

std::vector<std::string> BehaviorPolicy::getForbiddenPatterns(
    const std::string& context_type) const {

  std::vector<std::string> patterns;
  patterns.push_back("TODO");
  patterns.push_back("placeholder");
  patterns.push_back("stub");
  patterns.push_back("let's start simple");
  patterns.push_back("for now");
  patterns.push_back("workaround");
  patterns.push_back("quick fix");
  patterns.push_back("MVP");
  patterns.push_back("prototype");

  return patterns;
}

std::vector<std::string> BehaviorPolicy::getRequiredPatterns(
    const std::string& context_type) const {

  std::vector<std::string> patterns;

  if (context_type == "code") {
    patterns.push_back("error handling");
    patterns.push_back("validation");
    patterns.push_back("documentation");
    patterns.push_back("exception");
  }

  return patterns;
}

} // namespace VersaAI
