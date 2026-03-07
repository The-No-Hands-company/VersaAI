#!/usr/bin/env python3
"""
Download and setup pre-trained code models for VersaAI

Supports:
1. Local GGUF models (DeepSeek-Coder, StarCoder2, CodeLlama)
2. HuggingFace models (auto-download)
3. API configuration (OpenAI, Anthropic)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional

# Recommended code models (sorted by size)
RECOMMENDED_MODELS = {
    "deepseek-coder-1.3b": {
        "url": "https://huggingface.co/TheBloke/deepseek-coder-1.3b-instruct-GGUF/resolve/main/deepseek-coder-1.3b-instruct.Q4_K_M.gguf",
        "size": "0.9GB",
        "context": 16384,
        "description": "Smallest DeepSeek model - great for testing (1.3B params)"
    },
    "deepseek-coder-6.7b": {
        "url": "https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "size": "4.1GB",
        "context": 16384,
        "description": "Best balance of quality/performance (6.7B params) ⭐ RECOMMENDED"
    },
    "starcoder2-7b": {
        "url": "https://huggingface.co/second-state/StarCoder2-7B-GGUF/resolve/main/starcoder2-7b-Q5_K_M.gguf",
        "size": "5.0GB",
        "context": 16384,
        "description": "StarCoder2 7B - excellent for general coding (7B params)"
    },
    "codellama-7b": {
        "url": "https://huggingface.co/TheBloke/CodeLlama-7B-Instruct-GGUF/resolve/main/codellama-7b-instruct.Q4_K_M.gguf",
        "size": "4.1GB",
        "context": 16384,
        "description": "Meta's CodeLlama 7B - good all-rounder (7B params)"
    },
    "deepseek-coder-33b": {
        "url": "https://huggingface.co/TheBloke/deepseek-coder-33B-instruct-GGUF/resolve/main/deepseek-coder-33b-instruct.Q4_K_M.gguf",
        "size": "20GB",
        "context": 16384,
        "description": "Large DeepSeek model - highest quality (33B params) [Requires 24GB+ RAM]"
    }
}


def download_model(model_name: str, models_dir: Path) -> Optional[Path]:
    """Download a GGUF model from HuggingFace"""
    if model_name not in RECOMMENDED_MODELS:
        print(f"❌ Unknown model: {model_name}")
        print(f"Available models: {', '.join(RECOMMENDED_MODELS.keys())}")
        return None
    
    model_info = RECOMMENDED_MODELS[model_name]
    url = model_info["url"]
    filename = url.split("/")[-1]
    output_path = models_dir / filename
    
    if output_path.exists():
        print(f"✅ Model already exists: {output_path}")
        return output_path
    
    print(f"\n📥 Downloading {model_name}...")
    print(f"   Size: {model_info['size']}")
    print(f"   Description: {model_info['description']}")
    print(f"   URL: {url}")
    print(f"   Output: {output_path}\n")
    
    try:
        # Use wget or curl for download with progress
        if subprocess.run(["which", "wget"], capture_output=True).returncode == 0:
            subprocess.run([
                "wget",
                "--show-progress",
                "--progress=bar:force",
                "-O", str(output_path),
                url
            ], check=True)
        elif subprocess.run(["which", "curl"], capture_output=True).returncode == 0:
            subprocess.run([
                "curl",
                "-L",
                "-#",
                "-o", str(output_path),
                url
            ], check=True)
        else:
            print("❌ Neither wget nor curl found. Please install one.")
            print("   Ubuntu/Debian: sudo apt install wget")
            print("   macOS: brew install wget")
            return None
        
        print(f"\n✅ Downloaded successfully: {output_path}")
        return output_path
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Download failed: {e}")
        if output_path.exists():
            output_path.unlink()  # Clean up partial download
        return None
    except KeyboardInterrupt:
        print(f"\n⚠️  Download cancelled")
        if output_path.exists():
            output_path.unlink()
        return None


def list_models():
    """List all available models"""
    print("\n" + "="*70)
    print("  Available Code Models")
    print("="*70 + "\n")
    
    for i, (name, info) in enumerate(RECOMMENDED_MODELS.items(), 1):
        marker = "⭐" if "RECOMMENDED" in info["description"] else " "
        print(f"{marker} {i}. {name}")
        print(f"   Size: {info['size']}")
        print(f"   Context: {info['context']} tokens")
        print(f"   {info['description']}")
        print()


def setup_api_config(models_dir: Path):
    """Interactive API configuration setup"""
    config_path = models_dir.parent / "config" / "api_keys.env"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "="*70)
    print("  API Configuration Setup")
    print("="*70 + "\n")
    
    print("Configure API keys for cloud providers (optional):\n")
    
    # OpenAI
    print("1. OpenAI API (GPT-4, GPT-3.5)")
    openai_key = input("   Enter OpenAI API key (or press Enter to skip): ").strip()
    
    # Anthropic
    print("\n2. Anthropic API (Claude)")
    anthropic_key = input("   Enter Anthropic API key (or press Enter to skip): ").strip()
    
    # Together.ai
    print("\n3. Together.ai API (Various open models)")
    together_key = input("   Enter Together.ai API key (or press Enter to skip): ").strip()
    
    # Write config
    config_lines = [
        "# VersaAI API Configuration",
        "# Generated by download_code_models.py\n",
    ]
    
    if openai_key:
        config_lines.append(f"OPENAI_API_KEY={openai_key}")
    if anthropic_key:
        config_lines.append(f"ANTHROPIC_API_KEY={anthropic_key}")
    if together_key:
        config_lines.append(f"TOGETHER_API_KEY={together_key}")
    
    if len(config_lines) > 2:
        with open(config_path, 'w') as f:
            f.write('\n'.join(config_lines))
        print(f"\n✅ API configuration saved to: {config_path}")
        print(f"   Load with: source {config_path}")
    else:
        print("\n⚠️  No API keys provided. Skipping config file creation.")


def install_dependencies():
    """Install required Python packages"""
    print("\n" + "="*70)
    print("  Installing Dependencies")
    print("="*70 + "\n")
    
    packages = [
        "llama-cpp-python",  # For local GGUF models
        "transformers",      # For HuggingFace models
        "torch",            # PyTorch backend
        "openai",           # OpenAI API
        "anthropic",        # Anthropic API
    ]
    
    print("Required packages:")
    for pkg in packages:
        print(f"  - {pkg}")
    
    response = input("\nInstall dependencies? [y/N]: ").strip().lower()
    if response == 'y':
        print("\nInstalling packages...")
        for pkg in packages:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", pkg], check=True)
                print(f"✅ {pkg}")
            except subprocess.CalledProcessError:
                print(f"❌ Failed to install {pkg}")


def main():
    parser = argparse.ArgumentParser(
        description="Download and setup code models for VersaAI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List available models
  python download_code_models.py --list
  
  # Download recommended model
  python download_code_models.py --model deepseek-coder-6.7b
  
  # Download and setup everything
  python download_code_models.py --model deepseek-coder-6.7b --setup-api --install-deps
  
  # Download multiple models
  python download_code_models.py --model deepseek-coder-1.3b --model starcoder2-7b
        """
    )
    
    parser.add_argument(
        "--model",
        action="append",
        choices=list(RECOMMENDED_MODELS.keys()),
        help="Model to download (can be specified multiple times)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available models"
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path.home() / ".versaai" / "models",
        help="Directory to store models (default: ~/.versaai/models)"
    )
    parser.add_argument(
        "--setup-api",
        action="store_true",
        help="Configure API keys for cloud providers"
    )
    parser.add_argument(
        "--install-deps",
        action="store_true",
        help="Install required Python dependencies"
    )
    
    args = parser.parse_args()
    
    # List models
    if args.list:
        list_models()
        return
    
    # Create models directory
    args.models_dir.mkdir(parents=True, exist_ok=True)
    print(f"📁 Models directory: {args.models_dir}")
    
    # Install dependencies
    if args.install_deps:
        install_dependencies()
    
    # Download models
    if args.model:
        print(f"\n📥 Downloading {len(args.model)} model(s)...")
        for model_name in args.model:
            download_model(model_name, args.models_dir)
    
    # Setup API
    if args.setup_api:
        setup_api_config(args.models_dir)
    
    # Show usage instructions
    if args.model:
        print("\n" + "="*70)
        print("  Usage Instructions")
        print("="*70 + "\n")
        
        print("Start VersaAI CLI with local model:")
        first_model = args.model[0]
        model_file = RECOMMENDED_MODELS[first_model]["url"].split("/")[-1]
        print(f"  python versaai_cli.py --provider llama-cpp \\")
        print(f"    --model {args.models_dir}/{model_file}\n")
        
        print("Start VersaAI CLI with API:")
        print("  python versaai_cli.py --provider openai --model gpt-4-turbo")
        print("  python versaai_cli.py --provider anthropic --model claude-3-sonnet\n")
    
    if not args.model and not args.list and not args.install_deps and not args.setup_api:
        parser.print_help()


if __name__ == "__main__":
    main()
