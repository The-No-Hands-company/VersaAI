#!/usr/bin/env python3
"""
Download and Setup Code Models for VersaAI

Downloads pre-trained code models in GGUF format (optimized for CPU/GPU inference)
"""

import os
import sys
import argparse
import subprocess
from pathlib import Path
from typing import List


# Model download URLs and specs
MODELS = {
    "phi2": {
        "name": "Phi-2 (2.7B)",
        "url": "https://huggingface.co/TheBloke/phi-2-GGUF/resolve/main/phi-2.Q4_K_M.gguf",
        "file": "phi-2.Q4_K_M.gguf",
        "size": "1.6GB",
        "ram": "4GB"
    },
    "deepseek": {
        "name": "DeepSeek-Coder-6.7B",
        "url": "https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "file": "deepseek-coder-6.7b-instruct.Q4_K_M.gguf",
        "size": "4.0GB",
        "ram": "8GB"
    },
    "starcoder2": {
        "name": "StarCoder2-7B",
        "url": "https://huggingface.co/TheBloke/starcoder2-7b-GGUF/resolve/main/starcoder2-7b.Q4_K_M.gguf",
        "file": "starcoder2-7b.Q4_K_M.gguf",
        "size": "4.5GB",
        "ram": "8GB"
    },
    "codellama": {
        "name": "CodeLlama-13B",
        "url": "https://huggingface.co/TheBloke/CodeLlama-13B-Instruct-GGUF/resolve/main/codellama-13b-instruct.Q4_K_M.gguf",
        "file": "codellama-13b-instruct.Q4_K_M.gguf",
        "size": "7.5GB",
        "ram": "16GB"
    },
    "wizardcoder": {
        "name": "WizardCoder-15B",
        "url": "https://huggingface.co/TheBloke/WizardCoder-15B-V1.0-GGUF/resolve/main/wizardcoder-15b-v1.0.Q4_K_M.gguf",
        "file": "wizardcoder-15b-v1.0.Q4_K_M.gguf",
        "size": "9.0GB",
        "ram": "16GB"
    }
}


def get_models_dir() -> Path:
    """Get or create models directory"""
    models_dir = Path.home() / ".versaai" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    return models_dir


def download_model(model_id: str, force: bool = False) -> bool:
    """
    Download a specific model
    
    Args:
        model_id: Model identifier (e.g., 'deepseek')
        force: Re-download even if file exists
        
    Returns:
        True if successful
    """
    if model_id not in MODELS:
        print(f"❌ Unknown model: {model_id}")
        print(f"Available: {', '.join(MODELS.keys())}")
        return False
    
    model_info = MODELS[model_id]
    models_dir = get_models_dir()
    model_path = models_dir / model_info["file"]
    
    # Check if already exists
    if model_path.exists() and not force:
        print(f"✅ {model_info['name']} already downloaded")
        print(f"   Path: {model_path}")
        return True
    
    print(f"📥 Downloading {model_info['name']}...")
    print(f"   Size: {model_info['size']}")
    print(f"   RAM Required: {model_info['ram']}")
    print(f"   URL: {model_info['url']}")
    print()
    
    try:
        # Use wget or curl for download with progress
        if subprocess.run(["which", "wget"], capture_output=True).returncode == 0:
            cmd = ["wget", "-c", "-O", str(model_path), model_info["url"]]
        elif subprocess.run(["which", "curl"], capture_output=True).returncode == 0:
            cmd = ["curl", "-L", "-C", "-", "-o", str(model_path), model_info["url"]]
        else:
            print("❌ Neither wget nor curl found. Please install one.")
            return False
        
        result = subprocess.run(cmd)
        
        if result.returncode == 0:
            print(f"\n✅ Downloaded: {model_info['name']}")
            print(f"   Path: {model_path}")
            return True
        else:
            print(f"\n❌ Download failed for {model_info['name']}")
            if model_path.exists():
                model_path.unlink()  # Remove partial download
            return False
            
    except Exception as e:
        print(f"❌ Error downloading {model_info['name']}: {e}")
        return False


def list_models():
    """List all available models and their status"""
    models_dir = get_models_dir()
    
    print("\n🤖 Available Code Models:\n")
    print(f"{'ID':<15} {'Name':<25} {'Size':<8} {'RAM':<6} {'Status'}")
    print("=" * 75)
    
    for model_id, info in MODELS.items():
        model_path = models_dir / info["file"]
        status = "✅ Downloaded" if model_path.exists() else "⬇️  Available"
        
        print(f"{model_id:<15} {info['name']:<25} {info['size']:<8} {info['ram']:<6} {status}")
    
    print()
    print(f"Models directory: {models_dir}")
    
    # Calculate totals
    total_size = sum(
        float(info['size'].replace('GB', '')) for info in MODELS.values()
    )
    print(f"Total size if all downloaded: {total_size:.1f}GB")
    print()


def download_all(skip_existing: bool = True) -> List[str]:
    """Download all models"""
    success = []
    failed = []
    
    for model_id in MODELS.keys():
        if download_model(model_id, force=not skip_existing):
            success.append(model_id)
        else:
            failed.append(model_id)
    
    print("\n" + "=" * 75)
    print(f"✅ Successfully downloaded: {len(success)} models")
    if success:
        print(f"   {', '.join(success)}")
    
    if failed:
        print(f"❌ Failed: {len(failed)} models")
        print(f"   {', '.join(failed)}")
    
    return success


def check_system_requirements():
    """Check if system meets requirements"""
    print("\n🔍 Checking System Requirements:\n")
    
    # Check RAM
    try:
        import psutil
        total_ram_gb = psutil.virtual_memory().total / (1024**3)
        available_ram_gb = psutil.virtual_memory().available / (1024**3)
        
        print(f"RAM: {total_ram_gb:.1f}GB total, {available_ram_gb:.1f}GB available")
        
        if total_ram_gb < 4:
            print("⚠️  Warning: Less than 4GB RAM. Only Phi-2 will work.")
        elif total_ram_gb < 8:
            print("✅ 4-8GB RAM: Phi-2 models will work well.")
        elif total_ram_gb < 16:
            print("✅ 8-16GB RAM: Can run Phi-2, DeepSeek, StarCoder2.")
        else:
            print("✅ 16GB+ RAM: Can run all models!")
    except ImportError:
        print("⚠️  Install psutil to check RAM: pip install psutil")
    
    # Check disk space
    try:
        import shutil
        models_dir = get_models_dir()
        total, used, free = shutil.disk_usage(models_dir)
        free_gb = free / (1024**3)
        
        print(f"Disk Space: {free_gb:.1f}GB available at {models_dir}")
        
        if free_gb < 10:
            print("⚠️  Warning: Less than 10GB free. May not fit all models.")
        else:
            print("✅ Sufficient disk space.")
    except:
        pass
    
    # Check llama-cpp-python
    try:
        import llama_cpp
        print(f"✅ llama-cpp-python installed (version {llama_cpp.__version__})")
    except ImportError:
        print("⚠️  llama-cpp-python not installed.")
        print("   Install: pip install llama-cpp-python")
    
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Download and manage VersaAI code models"
    )
    parser.add_argument(
        "action",
        choices=["list", "download", "download-all", "check"],
        help="Action to perform"
    )
    parser.add_argument(
        "model",
        nargs="?",
        choices=list(MODELS.keys()),
        help="Model to download (required for 'download' action)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-download even if file exists"
    )
    
    args = parser.parse_args()
    
    if args.action == "list":
        list_models()
    
    elif args.action == "check":
        check_system_requirements()
    
    elif args.action == "download":
        if not args.model:
            print("❌ Error: Model name required for download")
            print(f"Available: {', '.join(MODELS.keys())}")
            sys.exit(1)
        
        success = download_model(args.model, force=args.force)
        sys.exit(0 if success else 1)
    
    elif args.action == "download-all":
        print("📥 Downloading all models (this may take a while)...")
        print(f"Total size: ~26GB\n")
        
        response = input("Continue? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            sys.exit(0)
        
        download_all(skip_existing=not args.force)


if __name__ == "__main__":
    main()
