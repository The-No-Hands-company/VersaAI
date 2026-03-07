#include "OSAgent.hpp"

std::string OSAgent::executeTask(const std::string& input) {
    if (input == "list files") {
        return "[Agent] Files: file1.txt, file2.txt, file3.txt.";
    }
    return "[Agent] Unknown OS task.";
}
