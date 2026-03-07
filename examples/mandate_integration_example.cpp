/**
 * @file mandate_integration_example.cpp
 * @brief Example demonstrating AI Behavior Mandate integration in VersaAI
 *
 * This example shows how the mandate automatically enforces production-grade
 * responses for development tasks.
 */

#include <iostream>
#include <memory>
#include "core/VersaAICore.hpp"
#include "agents/DevelopmentAgent.hpp"
#include "BehaviorPolicy.hpp"

/**
 * @brief Demonstrates basic mandate enforcement
 */
void example_basic_enforcement() {
  std::cout << "=== Example 1: Basic Mandate Enforcement ===" << std::endl;

  // Get the behavior policy singleton
  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // This code violates the mandate (has TODO)
  std::string bad_code = R"(
    void processData(const std::vector<int>& data) {
      // TODO: implement processing logic
      std::cout << "Processing " << data.size() << " items\n";
    }
  )";

  // Validate the code
  auto result = policy.validateCode(bad_code, "cpp");

  std::cout << "Code Quality Score: " << result.quality_score << "/100" << std::endl;
  std::cout << "Is Compliant: " << (result.is_compliant ? "YES" : "NO") << std::endl;

  if (!result.is_compliant) {
    std::cout << "\nViolations detected:" << std::endl;
    for (const auto& violation : result.violations) {
      std::cout << "  - [" << violation.rule_name << "] "
                << violation.description << std::endl;
    }
    std::cout << "\nSuggestion: " << result.suggestion << std::endl;
  }

  std::cout << std::endl;
}

/**
 * @brief Demonstrates production-quality code validation
 */
void example_production_quality() {
  std::cout << "=== Example 2: Production-Quality Code ===" << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // This code follows production standards
  std::string good_code = R"(
    /**
     * @brief Processes data with comprehensive error handling
     * @param data Input data vector
     * @return Number of items processed
     * @throws std::invalid_argument if data is empty
     */
    size_t processData(const std::vector<int>& data) {
      // Validate input
      if (data.empty()) {
        throw std::invalid_argument("Cannot process empty data");
      }

      size_t processed = 0;

      try {
        for (const auto& item : data) {
          // Validate each item
          if (item < 0) {
            std::cerr << "Warning: Negative value encountered: " << item << std::endl;
            continue;
          }

          // Process item
          performProcessing(item);
          ++processed;
        }
      } catch (const std::exception& e) {
        std::cerr << "Processing error: " << e.what() << std::endl;
        throw;
      }

      return processed;
    }
  )";

  auto result = policy.validateCode(good_code, "cpp");

  std::cout << "Code Quality Score: " << result.quality_score << "/100" << std::endl;
  std::cout << "Is Compliant: " << (result.is_compliant ? "YES" : "NO") << std::endl;
  std::cout << "Violations: " << result.violations.size() << std::endl;
  std::cout << std::endl;
}

/**
 * @brief Demonstrates DevelopmentAgent with mandate enforcement
 */
void example_development_agent() {
  std::cout << "=== Example 3: DevelopmentAgent with Mandate ===" << std::endl;

  DevelopmentAgent agent;

  // Get the system prompt (includes mandate)
  std::string system_prompt = agent.getSystemPrompt();
  std::cout << "System Prompt Preview:" << std::endl;
  std::cout << system_prompt.substr(0, 200) << "..." << std::endl;
  std::cout << std::endl;

  // Process an implementation request
  std::string request = "Implement a data cache manager";
  std::cout << "User Request: " << request << std::endl;
  std::cout << "\nAgent Response:" << std::endl;

  std::string response = agent.performTask(request);
  std::cout << response << std::endl;
  std::cout << std::endl;
}

/**
 * @brief Demonstrates user exception handling
 */
void example_user_exception() {
  std::cout << "=== Example 4: User Exception Request ===" << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // User explicitly requests simplified version
  std::string user_input = "Give me a quick prototype of a cache for testing";

  bool is_exception = policy.detectUserException(user_input);

  std::cout << "User Input: " << user_input << std::endl;
  std::cout << "Exception Detected: " << (is_exception ? "YES" : "NO") << std::endl;

  if (is_exception) {
    std::cout << "Note: User requested exception - simplified version allowed" << std::endl;
  }

  std::cout << std::endl;
}

/**
 * @brief Demonstrates input augmentation
 */
void example_input_augmentation() {
  std::cout << "=== Example 5: Input Augmentation ===" << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string user_input = "Create a file reader class";
  std::string augmented = policy.augmentUserInput(user_input);

  std::cout << "Original Input:" << std::endl;
  std::cout << user_input << std::endl;
  std::cout << "\nAugmented Input:" << std::endl;
  std::cout << augmented << std::endl;
  std::cout << std::endl;
}

/**
 * @brief Demonstrates VersaAICore integration
 */
void example_core_integration() {
  std::cout << "=== Example 6: VersaAICore Integration ===" << std::endl;

  auto& core = VersaAICore::getInstance();

  std::cout << "VersaAICore initialized with mandate enforcement" << std::endl;
  std::cout << "DevelopmentAgent automatically registered" << std::endl;
  std::cout << "Mandate loaded from: .github/AI_BEHAVIOR_MANDATE.md" << std::endl;

  // Invoke development agent through core
  try {
    std::string response = core.invokeAgent("Development",
                                            "Implement a thread-safe queue");
    std::cout << "\nAgent Response Preview:" << std::endl;
    std::cout << response.substr(0, 300) << "..." << std::endl;
  } catch (const std::exception& e) {
    std::cout << "Note: " << e.what() << std::endl;
  }

  std::cout << std::endl;
}

/**
 * @brief Demonstrates quality scoring
 */
void example_quality_scoring() {
  std::cout << "=== Example 7: Quality Scoring ===" << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Code with multiple violations
  std::string code_with_violations = R"(
    void process() {
      // TODO: implement this
      // placeholder for now
      // Quick fix - works around the issue
    }
  )";

  auto result = policy.validateCode(code_with_violations, "cpp");

  std::cout << "Quality Score: " << result.quality_score << "/100" << std::endl;
  std::cout << "Number of Violations: " << result.violations.size() << std::endl;

  std::cout << "\nViolation Breakdown:" << std::endl;
  for (const auto& v : result.violations) {
    std::string severity;
    switch (v.severity) {
      case VersaAI::BehaviorPolicy::ViolationSeverity::CRITICAL:
        severity = "CRITICAL";
        break;
      case VersaAI::BehaviorPolicy::ViolationSeverity::HIGH:
        severity = "HIGH";
        break;
      case VersaAI::BehaviorPolicy::ViolationSeverity::MEDIUM:
        severity = "MEDIUM";
        break;
      case VersaAI::BehaviorPolicy::ViolationSeverity::LOW:
        severity = "LOW";
        break;
    }

    std::cout << "  - [" << severity << "] " << v.rule_name << std::endl;
    std::cout << "    " << v.description << std::endl;
  }

  std::cout << std::endl;
}

/**
 * @brief Main demonstration function
 */
int main() {
  std::cout << "\n╔════════════════════════════════════════════════════════════════╗" << std::endl;
  std::cout << "║  AI Behavior Mandate Integration - Demonstration Examples     ║" << std::endl;
  std::cout << "╚════════════════════════════════════════════════════════════════╝\n" << std::endl;

  try {
    // Run all examples
    example_basic_enforcement();
    example_production_quality();
    example_development_agent();
    example_user_exception();
    example_input_augmentation();
    example_core_integration();
    example_quality_scoring();

    std::cout << "╔════════════════════════════════════════════════════════════════╗" << std::endl;
    std::cout << "║  All examples completed successfully!                         ║" << std::endl;
    std::cout << "╚════════════════════════════════════════════════════════════════╝\n" << std::endl;

    std::cout << "Key Takeaways:" << std::endl;
    std::cout << "  ✓ Mandate is enforced automatically for all development tasks" << std::endl;
    std::cout << "  ✓ Code is validated against production quality standards" << std::endl;
    std::cout << "  ✓ Violations are detected and reported with suggestions" << std::endl;
    std::cout << "  ✓ Users can request exceptions with specific keywords" << std::endl;
    std::cout << "  ✓ Quality scores provide measurable feedback (0-100)" << std::endl;
    std::cout << "  ✓ System-wide integration through VersaAICore" << std::endl;

    return 0;

  } catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << std::endl;
    return 1;
  }
}
