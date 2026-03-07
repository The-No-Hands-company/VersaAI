


cmake_minimum_required(VERSION 3.29)
project(VersaAI LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Fetch nlohmann/json dependency
include(FetchContent)
FetchContent_Declare(
  json
  URL https://github.com/nlohmann/json/releases/download/v3.11.3/json.tar.xz
)
FetchContent_MakeAvailable(json)

# Add include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/src
)

# Add source subdirectories
add_subdirectory(src/agents)
add_subdirectory(src/chatbots)
add_subdirectory(src/api)
add_subdirectory(src/models)

# Add main application executable
add_executable(VersaAIApp
    src/core/main.cpp
    src/core/VersaAICore.cpp
    src/core/VersaAIContext_v2.cpp
    src/core/VersaAILogger.cpp
    src/core/VersaAIException.cpp
    src/core/VersaAIErrorRecovery.cpp
    src/core/VersaAIModel.cpp
    src/core/VersaAIModelRegistry.cpp
    src/core/BehaviorPolicy.cpp
)

target_link_libraries(VersaAIApp PRIVATE Agents Chatbots ApiInterface Models nlohmann_json::nlohmann_json)
