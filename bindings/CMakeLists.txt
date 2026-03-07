cmake_minimum_required(VERSION 3.25)
project(versaai_bindings)

# Set C++ standard
set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find Python
find_package(Python COMPONENTS Interpreter Development REQUIRED)

# Try to find pybind11 via Python (pip install pybind11)
execute_process(
    COMMAND "${Python_EXECUTABLE}" -m pybind11 --cmakedir
    OUTPUT_VARIABLE pybind11_DIR
    OUTPUT_STRIP_TRAILING_WHITESPACE
    RESULT_VARIABLE pybind11_NOTFOUND
)

if(pybind11_NOTFOUND)
    message(FATAL_ERROR "pybind11 not found. Install with: python3 -m pip install pybind11")
endif()

# Find pybind11
find_package(pybind11 CONFIG REQUIRED HINTS "${pybind11_DIR}")

# Include directories
include_directories(
    ${CMAKE_SOURCE_DIR}/../include
    ${CMAKE_SOURCE_DIR}/../src/core
    ${Python_INCLUDE_DIRS}
)

# Collect source files from VersaAI core that we need
set(VERSAAI_CORE_SOURCES
    ${CMAKE_SOURCE_DIR}/../src/core/VersaAILogger.cpp
    ${CMAKE_SOURCE_DIR}/../src/core/VersaAIException.cpp
    ${CMAKE_SOURCE_DIR}/../src/core/VersaAIErrorRecovery.cpp
    ${CMAKE_SOURCE_DIR}/../src/core/VersaAIContext_v2.cpp
)

# Create pybind11 module with comprehensive bindings (v2 - corrected APIs)
pybind11_add_module(versaai_core
    versaai_bindings_v2.cpp
    ${VERSAAI_CORE_SOURCES}  # Include C++ sources directly
)

# Set output directory to versaai package
set_target_properties(versaai_core PROPERTIES
    LIBRARY_OUTPUT_DIRECTORY ${CMAKE_SOURCE_DIR}/../versaai
    OUTPUT_NAME "versaai_core"
)

# Install target
install(TARGETS versaai_core
    LIBRARY DESTINATION ${CMAKE_SOURCE_DIR}/../versaai
)
