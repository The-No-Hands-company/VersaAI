#!/bin/bash

#================================================================
# VersaAI Quick Launcher
# Starts the full VersaAI stack with one command
#================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Banner
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${GREEN}              VersaAI Full Stack Launcher                   ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check dependencies
echo -e "${YELLOW}⚙️  Checking dependencies...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install Python 3.8+${NC}"
    exit 1
fi

if ! command -v flutter &> /dev/null; then
    echo -e "${YELLOW}⚠️  Flutter not found. Installing Flutter UI will be skipped.${NC}"
    FLUTTER_AVAILABLE=false
else
    FLUTTER_AVAILABLE=true
fi

echo -e "${GREEN}✅ Dependencies OK${NC}"
echo ""

# Show menu
echo -e "${BLUE}Select launch mode:${NC}"
echo ""
echo "  1. 🚀 Full Stack (Backend + Flutter UI)"
echo "  2. 🔧 Backend Only (WebSocket server)"
echo "  3. 🎨 Flutter UI Only (requires backend running)"
echo "  4. 🧪 Run Tests"
echo "  5. ❌ Exit"
echo ""
read -p "Choice [1-5]: " CHOICE

case $CHOICE in
    1)
        echo -e "${GREEN}🚀 Starting Full Stack...${NC}"
        if [ "$FLUTTER_AVAILABLE" = false ]; then
            echo -e "${RED}❌ Flutter not available. Cannot start full stack.${NC}"
            exit 1
        fi
        cd ui && ./scripts/run_with_backend.sh
        ;;
    2)
        echo -e "${GREEN}🔧 Starting Backend Only...${NC}"
        echo -e "${YELLOW}Server will run on: ws://localhost:8765${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        python3 start_editor_bridge.py
        ;;
    3)
        echo -e "${GREEN}🎨 Starting Flutter UI...${NC}"
        if [ "$FLUTTER_AVAILABLE" = false ]; then
            echo -e "${RED}❌ Flutter not installed.${NC}"
            exit 1
        fi
        echo -e "${YELLOW}⚠️  Make sure backend is running on port 8765${NC}"
        echo -e "${YELLOW}Starting in 3 seconds...${NC}"
        sleep 3
        cd ui && flutter run -d linux
        ;;
    4)
        echo -e "${GREEN}🧪 Running Tests...${NC}"
        echo ""
        python3 test_integration.py
        ;;
    5)
        echo -e "${YELLOW}Goodbye!${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Invalid choice${NC}"
        exit 1
        ;;
esac
