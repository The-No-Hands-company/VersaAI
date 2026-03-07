#include "src/core/VersaAICore.hpp"
#include "include/BehaviorPolicy.hpp"
#include "include/VersaAILogger.hpp"
#include <iostream>
#include <string>

int main() {
    // Initialize logger
    VersaAI::LoggerConfig logConfig;
    logConfig.minLevel = VersaAI::LogLevel::INFO;
    logConfig.enableConsole = true;
    VersaAI::Logger::getInstance().initialize(logConfig);

    auto& core = VersaAICore::getInstance();

    std::cout << "\n=== Testing AI Behavior Mandate Enforcement ===\n\n";

    // Test 1: Request with placeholders (should be rejected or corrected)
    std::cout << "Test 1: Request code with TODO placeholders\n";
    std::cout << "Input: \"Write a function that TODO: implement later\"\n\n";

    std::string response1 = core.invokeAgent("Development", "Write a function that TODO: implement later");
    std::cout << "Response:\n" << response1 << "\n\n";
    std::cout << "---\n\n";

    // Test 2: Request complete implementation
    std::cout << "Test 2: Request complete implementation\n";
    std::cout << "Input: \"Implement a complete binary search function in C++\"\n\n";

    std::string response2 = core.invokeAgent("Development", "Implement a complete binary search function in C++");
    std::cout << "Response:\n" << response2 << "\n\n";
    std::cout << "---\n\n";

    // Test 3: User explicitly requests simplified version (should allow via exception)
    std::cout << "Test 3: User explicitly requests simplified version\n";
    std::cout << "Input: \"Please give me a SIMPLE and EASY example of a hash map\"\n\n";

    std::string response3 = core.invokeAgent("Development", "Please give me a SIMPLE and EASY example of a hash map");
    std::cout << "Response:\n" << response3 << "\n\n";
    std::cout << "---\n\n";

    std::cout << "=== All Tests Complete ===\n";

    return 0;
}
