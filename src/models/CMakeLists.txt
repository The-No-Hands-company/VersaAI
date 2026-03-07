# Models library
cmake_minimum_required(VERSION 3.29)

# Create Models library
add_library(Models STATIC
    VersaAIModelLoader.cpp
    VersaAIGGUFLoader.cpp
    VersaAIONNXLoader.cpp
    VersaAISafeTensorsLoader.cpp
)

target_include_directories(Models PUBLIC
    ${CMAKE_SOURCE_DIR}/include
    ${CMAKE_SOURCE_DIR}/src
)

# Link nlohmann_json dependency
target_link_libraries(Models PRIVATE nlohmann_json::nlohmann_json)
