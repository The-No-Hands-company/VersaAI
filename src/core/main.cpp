#include "core/VersaAICore.hpp"
#include "VersaAILogger.hpp"
#include "VersaAIException.hpp"
#include <iostream>

int main() {
    std::string appName;
    std::cout << "Enter app name (VersaOS, VersaModeling): ";
    std::cout.flush();

    if (!std::getline(std::cin, appName)) {
        std::cerr << "Failed to read app name" << std::endl;
        return 1;
    }

    std::cout << "Selected application: " << appName << std::endl;

    std::string input;
    while (true) {
        std::cout << "Enter command: ";
        std::cout.flush();

        if (!std::getline(std::cin, input)) {
            // EOF or input error
            std::cout << "\nExiting..." << std::endl;
            break;
        }

        if (input == "exit") {
            std::cout << "Exiting " << appName << ". Goodbye!" << std::endl;
            break;
        }

        auto& core = VersaAICore::getInstance();

        // Special command for testing agents directly
        if (input.rfind("@agent ", 0) == 0) {
            std::string agentCommand = input.substr(7);
            try {
                std::string response = core.invokeAgent(appName, agentCommand);
                std::cout << response << std::endl;
            } catch (const VersaAI::Exception& ex) {
                std::cerr << "\n[AGENT ERROR] " << ex.getMessage() << std::endl;
            }
            continue;
        }

        try {
            std::string response = core.processInput(appName, input);
            std::cout << response << std::endl;
        } catch (const VersaAI::Exception& ex) {
            std::cerr << "\n[ERROR] " << ex.getMessage() << std::endl;
            if (ex.getSeverity() >= VersaAI::ErrorSeverity::CRITICAL) {
                std::cerr << "Critical error occurred. Exiting..." << std::endl;
                break;
            }
        } catch (const std::exception& ex) {
            std::cerr << "\n[UNEXPECTED ERROR] " << ex.what() << std::endl;
        }
    }

    VersaAI::Logger::getInstance().shutdown();

    return 0;
}
