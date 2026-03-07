#!/bin/bash
# VersaAI Code Assistant Launcher
# Quick launcher for the VersaAI CLI with different model configurations

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
MODELS_DIR="${HOME}/.versaai/models"
CONFIG_DIR="${HOME}/.versaai/config"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║              VersaAI Code Assistant Launcher                   ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_error() {
    echo -e "${RED}❌ Error: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

check_dependencies() {
    print_info "Checking dependencies..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found. Please install Python 3.8+"
        exit 1
    fi
    
    # Check required packages
    local missing_packages=()
    
    python3 -c "import llama_cpp" 2>/dev/null || missing_packages+=("llama-cpp-python")
    python3 -c "import rich" 2>/dev/null || missing_packages+=("rich")
    
    if [ ${#missing_packages[@]} -gt 0 ]; then
        print_warning "Missing packages: ${missing_packages[*]}"
        echo -e "\nInstall with:"
        echo -e "  ${GREEN}python scripts/download_code_models.py --install-deps${NC}"
        echo -e "Or manually:"
        echo -e "  ${GREEN}pip install ${missing_packages[*]}${NC}\n"
        
        read -p "Install now? [y/N]: " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            python3 "$PROJECT_ROOT/scripts/download_code_models.py" --install-deps
        else
            print_info "Continuing without all dependencies (some features may not work)"
        fi
    else
        print_success "All dependencies installed"
    fi
}

list_local_models() {
    print_info "Scanning for local models in: $MODELS_DIR"
    
    if [ ! -d "$MODELS_DIR" ]; then
        print_warning "Models directory not found: $MODELS_DIR"
        return 1
    fi
    
    local models=($(find "$MODELS_DIR" -name "*.gguf" 2>/dev/null))
    
    if [ ${#models[@]} -eq 0 ]; then
        print_warning "No local models found"
        return 1
    fi
    
    echo -e "\n${CYAN}Available Local Models:${NC}\n"
    local i=1
    for model in "${models[@]}"; do
        local size=$(du -h "$model" | cut -f1)
        local name=$(basename "$model")
        echo -e "  ${GREEN}$i.${NC} $name ${YELLOW}($size)${NC}"
        ((i++))
    done
    echo
    
    return 0
}

download_model() {
    print_info "Opening model download menu..."
    python3 "$PROJECT_ROOT/scripts/download_code_models.py" --list
    echo
    
    read -p "Enter model number or name (or 'skip' to continue): " choice
    
    if [ "$choice" == "skip" ] || [ -z "$choice" ]; then
        return 0
    fi
    
    # Map common choices
    case "$choice" in
        1) model_name="deepseek-coder-1.3b" ;;
        2) model_name="deepseek-coder-6.7b" ;;
        3) model_name="starcoder2-7b" ;;
        4) model_name="codellama-7b" ;;
        5) model_name="deepseek-coder-33b" ;;
        *) model_name="$choice" ;;
    esac
    
    print_info "Downloading $model_name..."
    python3 "$PROJECT_ROOT/scripts/download_code_models.py" --model "$model_name"
}

setup_api() {
    print_info "Setting up API configuration..."
    python3 "$PROJECT_ROOT/scripts/download_code_models.py" --setup-api
    
    if [ -f "$CONFIG_DIR/api_keys.env" ]; then
        print_success "API configuration saved"
        print_info "Loading API keys..."
        source "$CONFIG_DIR/api_keys.env"
    fi
}

select_model() {
    echo -e "${CYAN}Select Model Type:${NC}\n"
    echo "  1. Local Model (GGUF via llama.cpp) - Free, Private"
    echo "  2. OpenAI API (GPT-4, GPT-3.5) - Paid, Powerful"
    echo "  3. Anthropic API (Claude) - Paid, Powerful"
    echo "  4. Placeholder Mode (No LLM) - Testing Only"
    echo
    
    read -p "Choice [1-4]: " choice
    echo
    
    case "$choice" in
        1)
            # Local model
            if ! list_local_models; then
                print_warning "No local models found"
                read -p "Download a model now? [Y/n]: " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                    download_model
                    list_local_models
                else
                    print_error "Cannot run without a model"
                    exit 1
                fi
            fi
            
            read -p "Select model number or enter path: " model_choice
            
            if [[ "$model_choice" =~ ^[0-9]+$ ]]; then
                # User entered a number
                local models=($(find "$MODELS_DIR" -name "*.gguf" 2>/dev/null))
                local idx=$((model_choice - 1))
                if [ $idx -ge 0 ] && [ $idx -lt ${#models[@]} ]; then
                    MODEL_PATH="${models[$idx]}"
                else
                    print_error "Invalid model number"
                    exit 1
                fi
            else
                # User entered a path
                MODEL_PATH="$model_choice"
            fi
            
            if [ ! -f "$MODEL_PATH" ]; then
                print_error "Model file not found: $MODEL_PATH"
                exit 1
            fi
            
            print_success "Using model: $(basename "$MODEL_PATH")"
            
            # GPU layers
            read -p "Use GPU acceleration? [Y/n]: " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Nn]$ ]]; then
                GPU_LAYERS="-1"  # All layers
                print_info "GPU acceleration enabled (all layers)"
            else
                GPU_LAYERS="0"
                print_info "CPU-only mode"
            fi
            
            # Launch
            print_info "Launching VersaAI CLI..."
            cd "$PROJECT_ROOT"
            python3 -m versaai.cli \
                --provider llama-cpp \
                --model "$MODEL_PATH" \
                --n-gpu-layers "$GPU_LAYERS"
            ;;
            
        2)
            # OpenAI
            if [ -z "$OPENAI_API_KEY" ]; then
                print_warning "OPENAI_API_KEY not set"
                setup_api
            fi
            
            if [ -z "$OPENAI_API_KEY" ]; then
                print_error "Cannot continue without API key"
                exit 1
            fi
            
            echo -e "\n${CYAN}Select OpenAI Model:${NC}\n"
            echo "  1. gpt-4-turbo (Most capable, ~\$0.01/1K tokens)"
            echo "  2. gpt-3.5-turbo (Fast & cheap, ~\$0.0005/1K tokens)"
            echo
            
            read -p "Choice [1-2]: " model_choice
            case "$model_choice" in
                1) MODEL_NAME="gpt-4-turbo" ;;
                2) MODEL_NAME="gpt-3.5-turbo" ;;
                *) MODEL_NAME="gpt-4-turbo" ;;
            esac
            
            print_info "Launching VersaAI CLI with OpenAI ($MODEL_NAME)..."
            cd "$PROJECT_ROOT"
            python3 -m versaai.cli \
                --provider openai \
                --model "$MODEL_NAME"
            ;;
            
        3)
            # Anthropic
            if [ -z "$ANTHROPIC_API_KEY" ]; then
                print_warning "ANTHROPIC_API_KEY not set"
                setup_api
            fi
            
            if [ -z "$ANTHROPIC_API_KEY" ]; then
                print_error "Cannot continue without API key"
                exit 1
            fi
            
            echo -e "\n${CYAN}Select Claude Model:${NC}\n"
            echo "  1. claude-3-opus-20240229 (Highest quality)"
            echo "  2. claude-3-sonnet-20240229 (Balanced)"
            echo "  3. claude-3-haiku-20240307 (Fast & cheap)"
            echo
            
            read -p "Choice [1-3]: " model_choice
            case "$model_choice" in
                1) MODEL_NAME="claude-3-opus-20240229" ;;
                2) MODEL_NAME="claude-3-sonnet-20240229" ;;
                3) MODEL_NAME="claude-3-haiku-20240307" ;;
                *) MODEL_NAME="claude-3-sonnet-20240229" ;;
            esac
            
            print_info "Launching VersaAI CLI with Anthropic ($MODEL_NAME)..."
            cd "$PROJECT_ROOT"
            python3 -m versaai.cli \
                --provider anthropic \
                --model "$MODEL_NAME"
            ;;
            
        4)
            # Placeholder
            print_warning "Running in placeholder mode (no actual LLM)"
            print_info "Use this for testing UI/features only"
            cd "$PROJECT_ROOT"
            python3 -m versaai.cli
            ;;
            
        *)
            print_error "Invalid choice"
            exit 1
            ;;
    esac
}

main() {
    print_header
    
    # Parse arguments
    case "${1:-}" in
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --download          Download a model"
            echo "  --setup-api         Setup API keys"
            echo "  --list              List local models"
            echo "  --help              Show this help"
            echo
            echo "If no options provided, launches interactive menu"
            exit 0
            ;;
        --download)
            download_model
            exit 0
            ;;
        --setup-api)
            setup_api
            exit 0
            ;;
        --list)
            list_local_models
            exit 0
            ;;
    esac
    
    # Interactive mode
    check_dependencies
    
    # Load API keys if available
    if [ -f "$CONFIG_DIR/api_keys.env" ]; then
        source "$CONFIG_DIR/api_keys.env"
    fi
    
    select_model
}

main "$@"
