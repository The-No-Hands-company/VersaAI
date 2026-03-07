#!/bin/bash
set -e  # Exit on error

echo "=== VersaAI Build Script ==="
echo ""

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Create build directory if it doesn't exist
if [ ! -d "build" ]; then
    echo "Creating build directory..."
    mkdir -p build
fi

cd build

# Configure with CMake using Ninja generator
echo "Configuring CMake..."
cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_STANDARD=23 \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    ..

# Build the project
echo ""
echo "Building VersaAI..."
ninja -v

echo ""
echo "=== Build completed successfully ==="
echo "Executable: build/VersaAIApp"
