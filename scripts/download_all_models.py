#!/usr/bin/env python3
"""
Download ALL recommended code models for VersaAI Multi-Model Router

This script downloads all 5 recommended models to enable automatic
model selection based on task complexity and requirements.
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict

# Import from download_code_models
sys.path.insert(0, str(Path(__file__).parent))
from download_code_models import RECOMMENDED_MODELS, download_model


def get_available_space_gb(path: Path) -> float:
    """Get available disk space in GB"""
    stat = os.statvfs(path)
    available_bytes = stat.f_bavail * stat.f_frsize
    return available_bytes / (1024**3)


def parse_size(size_str: str) -> float:
    """Parse size string like '4.1GB' to float"""
    return float(size_str.replace('GB', '').strip())


def calculate_total_size(models: List[str]) -> float:
    """Calculate total download size in GB"""
    total = 0.0
    for model in models:
        if model in RECOMMENDED_MODELS:
            total += parse_size(RECOMMENDED_MODELS[model]['size'])
    return total


def check_system_requirements() -> Dict:
    """Check system RAM and disk space"""
    # Get RAM
    try:
        with open('/proc/meminfo', 'r') as f:
            mem_total = int([line for line in f if 'MemTotal' in line][0].split()[1])
            ram_gb = mem_total / (1024**2)
    except:
        ram_gb = 16  # Default assumption
    
    return {
        'ram_gb': ram_gb,
        'can_run_33b': ram_gb >= 24
    }


def display_download_plan(models: List[str], models_dir: Path):
    """Display what will be downloaded"""
    print("\n" + "="*80)
    print("  📦 VersaAI Multi-Model Download Plan")
    print("="*80 + "\n")
    
    total_size = 0.0
    existing_size = 0.0
    
    print("Models to download:\n")
    for i, model_name in enumerate(models, 1):
        info = RECOMMENDED_MODELS[model_name]
        size_gb = parse_size(info['size'])
        total_size += size_gb
        
        filename = info['url'].split('/')[-1]
        exists = (models_dir / filename).exists()
        status = "✅ EXISTS" if exists else "📥 DOWNLOAD"
        
        if exists:
            existing_size += size_gb
        
        print(f"  {i}. {model_name}")
        print(f"     Size: {info['size']}")
        print(f"     RAM:  {info.get('ram_required', '8GB')}")
        print(f"     {info['description']}")
        print(f"     Status: {status}\n")
    
    print("-" * 80)
    print(f"  Total size: {total_size:.1f}GB")
    print(f"  Already downloaded: {existing_size:.1f}GB")
    print(f"  Need to download: {total_size - existing_size:.1f}GB")
    
    # Check disk space
    available = get_available_space_gb(models_dir)
    print(f"  Available space: {available:.1f}GB")
    
    if available < (total_size - existing_size + 5):  # +5GB buffer
        print(f"\n  ⚠️  WARNING: Low disk space! Need {total_size - existing_size + 5:.1f}GB")
        return False
    
    print("\n" + "="*80 + "\n")
    return True


def main():
    models_dir = Path.home() / ".versaai" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    
    print("\n" + "╔" + "="*78 + "╗")
    print("║" + " "*20 + "VersaAI Multi-Model Downloader" + " "*28 + "║")
    print("╚" + "="*78 + "╝\n")
    
    # Check system requirements
    sys_info = check_system_requirements()
    print(f"🖥️  System RAM: {sys_info['ram_gb']:.1f}GB")
    
    # Recommended models based on RAM
    if sys_info['can_run_33b']:
        print("✅ Can run ALL models (including 33B)\n")
        recommended = list(RECOMMENDED_MODELS.keys())
    else:
        print(f"⚠️  Cannot run 33B model (need 24GB+ RAM, have {sys_info['ram_gb']:.1f}GB)")
        print("   Will download only models that fit in your RAM\n")
        recommended = [k for k in RECOMMENDED_MODELS.keys() if k != 'deepseek-coder-33b']
    
    # Display download options
    print("Download options:\n")
    print("  1. Download ALL recommended models (auto-selected for your system)")
    print("  2. Download ESSENTIAL models only (1.3B + 6.7B)")
    print("  3. Download BALANCED set (1.3B + 6.7B + 7B)")
    print("  4. Custom selection")
    print("  5. Exit\n")
    
    choice = input("Your choice [1-5]: ").strip()
    
    models_to_download = []
    
    if choice == "1":
        models_to_download = recommended
    elif choice == "2":
        models_to_download = ["deepseek-coder-1.3b", "deepseek-coder-6.7b"]
    elif choice == "3":
        models_to_download = ["deepseek-coder-1.3b", "deepseek-coder-6.7b", "starcoder2-7b"]
    elif choice == "4":
        print("\nAvailable models:")
        for i, name in enumerate(recommended, 1):
            info = RECOMMENDED_MODELS[name]
            print(f"  {i}. {name} ({info['size']})")
        
        selections = input("\nEnter model numbers separated by spaces (e.g., 1 2 3): ").strip().split()
        try:
            models_to_download = [recommended[int(s)-1] for s in selections]
        except (ValueError, IndexError):
            print("❌ Invalid selection")
            return
    else:
        print("Exiting...")
        return
    
    # Display plan
    if not display_download_plan(models_to_download, models_dir):
        response = input("\n⚠️  Continue anyway? [y/N]: ").strip().lower()
        if response != 'y':
            print("Download cancelled.")
            return
    
    # Confirm
    response = input("Start download? [y/N]: ").strip().lower()
    if response != 'y':
        print("Download cancelled.")
        return
    
    # Download each model
    print("\n" + "="*80)
    print("  Starting downloads...")
    print("="*80 + "\n")
    
    successful = []
    failed = []
    
    for i, model_name in enumerate(models_to_download, 1):
        print(f"\n[{i}/{len(models_to_download)}] Processing {model_name}...")
        result = download_model(model_name, models_dir)
        
        if result:
            successful.append(model_name)
        else:
            failed.append(model_name)
    
    # Summary
    print("\n" + "="*80)
    print("  Download Summary")
    print("="*80 + "\n")
    
    if successful:
        print(f"✅ Successfully downloaded {len(successful)} model(s):")
        for name in successful:
            print(f"   - {name}")
        print()
    
    if failed:
        print(f"❌ Failed to download {len(failed)} model(s):")
        for name in failed:
            print(f"   - {name}")
        print()
    
    # Next steps
    if successful:
        print("="*80)
        print("  🎉 Setup Complete!")
        print("="*80 + "\n")
        
        print("Next steps:\n")
        print("1. Start VersaAI with multi-model router:")
        print("   python versaai_cli.py --multi-model\n")
        
        print("2. Or use a specific model:")
        first_model = successful[0]
        filename = RECOMMENDED_MODELS[first_model]['url'].split('/')[-1]
        print(f"   python versaai_cli.py --provider llama-cpp --model {models_dir}/{filename}\n")
        
        print("3. Check model router documentation:")
        print("   cat docs/MODEL_ROUTER.md\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Download cancelled by user")
        sys.exit(1)
