#!/bin/bash

#================================================================
# VersaAI Quick Launcher
# Starts the FastAPI backend + Tauri v2 desktop app
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

API_PORT=8000
API_HOST=127.0.0.1

# Banner
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║${GREEN}              VersaAI Full Stack Launcher                   ${BLUE}║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ── Dependency checks ────────────────────────────────────────────
echo -e "${YELLOW}⚙️  Checking dependencies...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

if ! command -v cargo &> /dev/null; then
    echo -e "${YELLOW}⚠️  Cargo/Rust not found — Desktop UI will be unavailable.${NC}"
    TAURI_AVAILABLE=false
else
    TAURI_AVAILABLE=true
fi

OLLAMA_RUNNING=false
if curl -sf http://localhost:11434/ > /dev/null 2>&1; then
    OLLAMA_RUNNING=true
fi

echo -e "${GREEN}✅ Core dependencies OK${NC}"
if [ "$OLLAMA_RUNNING" = false ]; then
    echo -e "${YELLOW}⚠️  Ollama is not running — chat/agents require it.${NC}"
    echo -e "${YELLOW}   Start with:  ollama serve && ollama pull qwen2.5-coder:7b${NC}"
fi
echo ""

# ── Menu ─────────────────────────────────────────────────────────
echo -e "${BLUE}Select launch mode:${NC}"
echo ""
echo "  1. 🚀 Full Stack  (API server + Tauri desktop)"
echo "  2. 🔧 Backend Only (FastAPI on port $API_PORT)"
echo "  3. 🖥️  Desktop Only (requires backend already running)"
echo "  4. 🧪 Run Tests"
echo "  5. ❌ Exit"
echo ""
read -p "Choice [1-5]: " CHOICE

# ── Helpers ──────────────────────────────────────────────────────
start_backend() {
    echo -e "${GREEN}🔧 Starting FastAPI backend on http://${API_HOST}:${API_PORT}${NC}"
    python3 -m uvicorn versaai.api.app:app \
        --host "$API_HOST" --port "$API_PORT" --reload &
    BACKEND_PID=$!
    # Wait until the server responds
    for i in $(seq 1 30); do
        if curl -sf "http://${API_HOST}:${API_PORT}/v1/health" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Backend ready${NC}"
            return 0
        fi
        sleep 1
    done
    echo -e "${RED}❌ Backend failed to start within 30 s${NC}"
    kill "$BACKEND_PID" 2>/dev/null
    exit 1
}

start_desktop() {
    if [ "$TAURI_AVAILABLE" = false ]; then
        echo -e "${RED}❌ Cargo/Rust not installed — cannot start Tauri desktop.${NC}"
        exit 1
    fi
    echo -e "${GREEN}🖥️  Starting Tauri desktop (first build may take a few minutes)...${NC}"
    cd "$PROJECT_ROOT/desktop"
    npm install --silent 2>/dev/null
    npm run tauri dev
}

cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null
    wait 2>/dev/null
    echo -e "${GREEN}Done.${NC}"
}

# ── Dispatch ─────────────────────────────────────────────────────
case $CHOICE in
    1)
        echo -e "${GREEN}🚀 Starting Full Stack...${NC}"
        trap cleanup EXIT INT TERM
        start_backend
        echo ""
        start_desktop
        ;;
    2)
        echo -e "${YELLOW}Press Ctrl+C to stop${NC}"
        echo ""
        python3 -m uvicorn versaai.api.app:app \
            --host "$API_HOST" --port "$API_PORT" --reload
        ;;
    3)
        echo -e "${YELLOW}⚠️  Make sure backend is running on port ${API_PORT}${NC}"
        if ! curl -sf "http://${API_HOST}:${API_PORT}/v1/health" > /dev/null 2>&1; then
            echo -e "${RED}❌ Backend not reachable at http://${API_HOST}:${API_PORT}${NC}"
            exit 1
        fi
        start_desktop
        ;;
    4)
        echo -e "${GREEN}🧪 Running Tests...${NC}"
        echo ""
        python3 -m pytest tests/ -v 2>/dev/null || python3 verify_setup.py
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
