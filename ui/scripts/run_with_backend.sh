#!/bin/bash
# VersaAI Full Stack Launcher (Linux/Mac)
# Starts VersaAI backend + Flutter UI together

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║              VersaAI Full Stack Launcher                      ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo "📁 Project root: $PROJECT_ROOT"
echo ""

# Start backend in background
echo "📡 Starting VersaAI WebSocket backend..."
cd "$PROJECT_ROOT"

# Check if Python virtual environment exists
if [ -d ".venv" ]; then
    echo "   Using virtual environment..."
    source .venv/bin/activate
fi

# Start backend server in background
python3 start_editor_bridge.py &
BACKEND_PID=$!

echo "   Backend PID: $BACKEND_PID"
echo "   Backend URL: ws://localhost:8765"
echo ""

# Wait for backend to start
echo "⏳ Waiting for backend to initialize (5 seconds)..."
sleep 5

# Check if backend is still running
if ps -p $BACKEND_PID > /dev/null; then
    echo "✅ Backend is running"
else
    echo "❌ Backend failed to start!"
    exit 1
fi

echo ""
echo "🎨 Starting Flutter UI..."
cd "$PROJECT_ROOT/ui"

# Install dependencies if needed
if [ ! -d ".dart_tool" ]; then
    echo "   Installing Flutter dependencies..."
    flutter pub get
fi

# Determine platform
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macos"
else
    PLATFORM="linux"
fi

echo "   Platform: $PLATFORM"
echo ""

# Start Flutter app
flutter run -d $PLATFORM

# Cleanup on exit
echo ""
echo "🛑 Stopping backend server..."
kill $BACKEND_PID 2>/dev/null || true

echo "✅ VersaAI Full Stack shut down successfully"
