#pragma once
#include <string>
#include <regex>
#include <iostream>
#include "../../include/BehaviorPolicy.hpp"

/**
 * @brief Base class for all VersaAI agents with production-grade behavior enforcement
 *
 * All agents inherit from this class and must implement the performTask method.
 * The base class automatically enforces the AI Behavior Mandate for all responses.
 */
class AgentBase {
public:
    explicit AgentBase(const std::string& name)
      : name_(name),
        behavior_policy_(VersaAI::BehaviorPolicy::getInstance()) {
      initializeBehaviorPolicy();
    }

    virtual ~AgentBase() = default;

    /**
     * @brief Performs a task with automatic behavior mandate enforcement
     * @param input User input/task description
     * @return Response with production-grade quality guarantees
     */
    std::string performTask(const std::string& input) {
      // Augment input with mandate reminders if appropriate
      std::string augmented_input = behavior_policy_.augmentUserInput(input);

      // Check if user requested exception (MVP, prototype, etc.)
      if (behavior_policy_.detectUserException(input)) {
        auto config = behavior_policy_.getConfig();
        config.user_requested_simplified = true;
        behavior_policy_.setConfig(config);
      }

      // Execute the agent's core task logic
      std::string response = executeTask(augmented_input);

      // Validate response against behavior mandate
      auto validation = behavior_policy_.validateResponse(response, getTaskContext());

      if (!validation.is_compliant) {
        // Log violations for debugging
        logViolations(validation);

        // Attempt self-correction
        response = attemptSelfCorrection(response, validation);

        // Re-validate after correction
        validation = behavior_policy_.validateResponse(response, getTaskContext());

        if (!validation.is_compliant) {
          // Add quality warning to response
          response += "\n\n[QUALITY WARNING: " + validation.suggestion + "]";
        }
      }

      // Reset exception flags
      auto config = behavior_policy_.getConfig();
      config.user_requested_simplified = false;
      config.user_requested_mvp = false;
      config.user_requested_prototype = false;
      behavior_policy_.setConfig(config);

      return response;
    }

    const std::string& getName() const { return name_; }

    /**
     * @brief Gets the system prompt with embedded behavior mandate
     * @return Complete system prompt for this agent
     */
    virtual std::string getSystemPrompt() const {
      return behavior_policy_.generateSystemPrompt(
        "a production-grade AI agent specialized in " + name_,
        getTaskContext()
      );
    }

protected:
    /**
     * @brief Core task execution - must be implemented by derived classes
     * @param input Augmented user input with mandate enforcement
     * @return Agent's response (will be validated automatically)
     */
    virtual std::string executeTask(const std::string& input) = 0;

    /**
     * @brief Provides context about the type of task this agent handles
     * @return Task context string (e.g., "code", "design", "documentation")
     */
    virtual std::string getTaskContext() const { return "general"; }

    /**
     * @brief Initialize agent-specific behavior policy configuration
     */
    virtual void initializeBehaviorPolicy() {
      // Default configuration - can be overridden by derived classes
      VersaAI::BehaviorPolicy::PolicyConfig config;
      config.allow_placeholders = false;
      config.allow_todos = false;
      config.allow_simplifications = false;
      config.enforce_error_handling = true;
      config.enforce_documentation = true;
      config.enforce_production_quality = true;
      behavior_policy_.setConfig(config);
    }

    /**
     * @brief Attempts to self-correct response based on validation violations
     * @param original_response Original response with violations
     * @param validation Validation result with violation details
     * @return Corrected response
     */
    virtual std::string attemptSelfCorrection(
        const std::string& original_response,
        const VersaAI::BehaviorPolicy::ValidationResult& validation) {

      std::string corrected = original_response;

      // Remove TODOs and placeholders
      corrected = std::regex_replace(corrected,
        std::regex(R"(//\s*TODO.*\n)"),
        "// [REMOVED TODO - implementing complete solution]\n");

      corrected = std::regex_replace(corrected,
        std::regex(R"(//\s*placeholder.*\n)", std::regex::icase),
        "// [REMOVED PLACEHOLDER - implementing full functionality]\n");

      return corrected;
    }

    /**
     * @brief Logs behavior mandate violations for monitoring
     */
    virtual void logViolations(const VersaAI::BehaviorPolicy::ValidationResult& validation) {
      // TODO: Integrate with VersaAI logging system when available
      for (const auto& violation : validation.violations) {
        // Placeholder logging - will be replaced with proper logging framework
        std::cerr << "[" << name_ << "] Behavior Violation ["
                  << violation.rule_name << "]: "
                  << violation.description << std::endl;
      }
    }

    std::string name_;
    VersaAI::BehaviorPolicy& behavior_policy_;
};
