#!/usr/bin/env python3
"""
Helper script to download a localized GGUF model for VersaAI.
"""
import os
import requests
import sys
from tqdm import tqdm

# Recommended model: DeepSeek Coder 6.7B Instruct (GGUF Quantized)
# This is a good balance of performance and size (~4GB)
MODEL_URL = "https://huggingface.co/TheBloke/deepseek-coder-6.7B-instruct-GGUF/resolve/main/deepseek-coder-6.7b-instruct.Q4_K_M.gguf"
MODEL_DIR = os.path.expanduser("~/.versaai/models")
MODEL_PATH = os.path.join(MODEL_DIR, "default.gguf")

def download_model():
    if os.path.exists(MODEL_PATH):
        print(f"✅ Model already exists at: {MODEL_PATH}")
        return

    print(f"⬇️  Downloading DeepSeek Coder 6.7B to {MODEL_PATH}...")
    print("   (This is ~4GB, please wait...)")
    
    os.makedirs(MODEL_DIR, exist_ok=True)
    
    try:
        response = requests.get(MODEL_URL, stream=True)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        block_size = 1024 # 1 Kibibyte
        
        with open(MODEL_PATH, "wb") as f, tqdm(
            desc="Progress",
            total=total_size,
            unit='iB',
            unit_scale=True,
            unit_divisor=1024,
        ) as bar:
            for data in response.iter_content(block_size):
                size = f.write(data)
                bar.update(size)
                
        print("\n✅ Download complete!")
        print(f"   Model saved to: {MODEL_PATH}")
        print("\n🚀 You can now run 'python3 test_coding_agent_cli.py' to use the specific model!")
        
    except Exception as e:
        print(f"\n❌ Download failed: {e}")
        if os.path.exists(MODEL_PATH):
            os.remove(MODEL_PATH)
        sys.exit(1)

if __name__ == "__main__":
    download_model()
