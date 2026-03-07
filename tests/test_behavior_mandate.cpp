#include <cassert>
#include <iostream>
#include <string>
#include "../include/BehaviorPolicy.hpp"
#include "../src/agents/DevelopmentAgent.hpp"

/**
 * @brief Comprehensive test suite for AI Behavior Mandate enforcement
 *
 * Tests validate that the system properly enforces production-grade standards
 * and rejects placeholder/TODO/MVP approaches.
 */

void test_behavior_policy_initialization() {
  std::cout << "Testing BehaviorPolicy initialization..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Test that singleton works
  auto& policy2 = VersaAI::BehaviorPolicy::getInstance();
  assert(&policy == &policy2);

  std::cout << "✓ BehaviorPolicy singleton initialized" << std::endl;
}

void test_placeholder_detection() {
  std::cout << "\nTesting placeholder detection..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Test code with placeholder
  std::string bad_code = R"(
    void processData() {
      // Placeholder for actual implementation
      std::cout << "Processing...\n";
    }
  )";

  auto result = policy.validateCode(bad_code, "cpp");
  assert(!result.is_compliant);
  assert(!result.violations.empty());
  assert(result.violations[0].severity == VersaAI::BehaviorPolicy::ViolationSeverity::CRITICAL);

  std::cout << "✓ Placeholder detected correctly" << std::endl;
  std::cout << "  Violation: " << result.violations[0].description << std::endl;
}

void test_todo_detection() {
  std::cout << "\nTesting TODO detection..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string bad_code = R"(
    void fetchData() {
      // TODO: implement this later
      return;
    }
  )";

  auto result = policy.validateCode(bad_code, "cpp");
  assert(!result.is_compliant);
  assert(!result.violations.empty());

  std::cout << "✓ TODO comment detected correctly" << std::endl;
}

void test_simplification_language_detection() {
  std::cout << "\nTesting simplification language detection..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string bad_response = "Let's start with a simpler version and iterate later.";

  auto result = policy.validateResponse(bad_response, "general");
  assert(!result.is_compliant);
  assert(!result.violations.empty());
  assert(result.violations[0].severity == VersaAI::BehaviorPolicy::ViolationSeverity::HIGH);

  std::cout << "✓ Simplification language detected" << std::endl;
}

void test_workaround_detection() {
  std::cout << "\nTesting workaround detection..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string bad_response = "We can work around this issue by using a global variable.";

  auto result = policy.validateResponse(bad_response, "general");
  assert(!result.is_compliant);

  std::cout << "✓ Workaround language detected" << std::endl;
}

void test_mvp_thinking_detection() {
  std::cout << "\nTesting MVP thinking detection..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string bad_response = "Let's get it working first, then optimize later.";

  auto result = policy.validateResponse(bad_response, "general");
  assert(!result.is_compliant);

  std::cout << "✓ MVP thinking detected" << std::endl;
}

void test_production_quality_code() {
  std::cout << "\nTesting production-quality code validation..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string good_code = R"(
    /**
     * @brief Processes data with comprehensive error handling
     * @param data Input data to process
     * @return Processed result
     * @throws std::invalid_argument if data is invalid
     */
    Result processData(const Data& data) {
      // Validate input
      if (!data.isValid()) {
        throw std::invalid_argument("Invalid data provided");
      }

      Result result;
      try {
        // Process with proper error handling
        result = performProcessing(data);

        // Validate output
        if (!result.isValid()) {
          throw std::runtime_error("Processing produced invalid result");
        }

      } catch (const std::exception& e) {
        logger_.error("Processing failed: " + std::string(e.what()));
        throw;
      }

      return result;
    }
  )";

  auto result = policy.validateCode(good_code, "cpp");
  assert(result.is_compliant);
  assert(result.quality_score > 90.0);

  std::cout << "✓ Production-quality code validated" << std::endl;
  std::cout << "  Quality score: " << result.quality_score << std::endl;
}

void test_user_exception_detection() {
  std::cout << "\nTesting user exception request detection..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string user_input = "Give me a quick prototype for testing";

  bool is_exception = policy.detectUserException(user_input);
  assert(is_exception);

  std::cout << "✓ User exception request detected" << std::endl;
}

void test_system_prompt_generation() {
  std::cout << "\nTesting system prompt generation..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string prompt = policy.generateSystemPrompt(
    "a senior software engineer",
    "implementing a new feature"
  );

  assert(prompt.find("PRODUCTION-GRADE") != std::string::npos);
  assert(prompt.find("NO placeholders") != std::string::npos);
  assert(prompt.find("NO TODO") != std::string::npos);
  assert(prompt.find("Complete") != std::string::npos);

  std::cout << "✓ System prompt generated with mandate" << std::endl;
}

void test_input_augmentation() {
  std::cout << "\nTesting input augmentation..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  std::string user_input = "Implement a data processor class";
  std::string augmented = policy.augmentUserInput(user_input);

  assert(augmented.find("MANDATE") != std::string::npos);
  assert(augmented.find("production-grade") != std::string::npos);

  std::cout << "✓ Input augmented with mandate reminder" << std::endl;
}

void test_development_agent_integration() {
  std::cout << "\nTesting DevelopmentAgent with mandate enforcement..." << std::endl;

  DevelopmentAgent agent;

  // Test that agent has behavior policy
  std::string prompt = agent.getSystemPrompt();
  assert(prompt.find("MANDATE") != std::string::npos);

  // Test response to implementation request
  std::string response = agent.performTask("Implement a cache manager");
  assert(response.find("production-grade") != std::string::npos);
  assert(response.find("MANDATE") != std::string::npos);

  std::cout << "✓ DevelopmentAgent integrated with mandate" << std::endl;
}

void test_quality_score_calculation() {
  std::cout << "\nTesting quality score calculation..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Code with multiple violations
  std::string bad_code = R"(
    void process() {
      // TODO: implement
      // placeholder
    }
  )";

  auto result = policy.validateCode(bad_code, "cpp");
  assert(result.quality_score < 50.0);

  std::cout << "✓ Quality score calculated correctly" << std::endl;
  std::cout << "  Score: " << result.quality_score << " (expected < 50)" << std::endl;
}

void test_error_handling_validation() {
  std::cout << "\nTesting error handling validation..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Code without error handling
  std::string bad_code = R"(
    void processFile(const std::string& filename) {
      std::ifstream file(filename);
      std::string data;
      file >> data;
      process(data);
    }
  )";

  auto result = policy.validateCode(bad_code, "cpp");

  // Should have violation for missing error handling
  bool has_error_handling_violation = false;
  for (const auto& v : result.violations) {
    if (v.rule_name == "MISSING_ERROR_HANDLING") {
      has_error_handling_violation = true;
      break;
    }
  }

  assert(has_error_handling_violation);

  std::cout << "✓ Missing error handling detected" << std::endl;
}

void test_documentation_validation() {
  std::cout << "\nTesting documentation validation..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Code without documentation
  std::string bad_code = R"(
    void process(const Data& data) {
      if (data.isValid()) {
        doSomething(data);
      }
    }
  )";

  auto result = policy.validateCode(bad_code, "cpp");

  // Should have violation for missing documentation
  bool has_doc_violation = false;
  for (const auto& v : result.violations) {
    if (v.rule_name == "MISSING_DOCUMENTATION") {
      has_doc_violation = true;
      break;
    }
  }

  assert(has_doc_violation);

  std::cout << "✓ Missing documentation detected" << std::endl;
}

void test_mandate_loading() {
  std::cout << "\nTesting mandate file loading..." << std::endl;

  auto& policy = VersaAI::BehaviorPolicy::getInstance();

  // Try to load the actual mandate file
  bool loaded = policy.loadMandate(".github/AI_BEHAVIOR_MANDATE.md");

  if (loaded) {
    std::string principles = policy.getMandatePrinciples();
    assert(!principles.empty());
    std::cout << "✓ Mandate file loaded successfully" << std::endl;
  } else {
    std::cout << "⚠ Mandate file not found (using defaults)" << std::endl;
  }
}

int main() {
  std::cout << "=== AI Behavior Mandate Enforcement Test Suite ===\n" << std::endl;

  try {
    test_behavior_policy_initialization();
    test_placeholder_detection();
    test_todo_detection();
    test_simplification_language_detection();
    test_workaround_detection();
    test_mvp_thinking_detection();
    test_production_quality_code();
    test_user_exception_detection();
    test_system_prompt_generation();
    test_input_augmentation();
    test_development_agent_integration();
    test_quality_score_calculation();
    test_error_handling_validation();
    test_documentation_validation();
    test_mandate_loading();

    std::cout << "\n=== ALL TESTS PASSED ✓ ===\n" << std::endl;
    std::cout << "AI Behavior Mandate is properly enforced across VersaAI." << std::endl;

    return 0;

  } catch (const std::exception& e) {
    std::cerr << "\n=== TEST FAILED ✗ ===" << std::endl;
    std::cerr << "Error: " << e.what() << std::endl;
    return 1;
  }
}
