"""
Model Download Script
One-time setup to download ChatterBox TTS models from HuggingFace
"""

import os
import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from voice_revolver_core.infrastructure.model_downloader import ModelDownloader


def main():
    print("=" * 70)
    print("ChatterBox TTS Model Downloader")
    print("=" * 70)
    print()
    
    downloader = ModelDownloader()
    
    # Check what's already downloaded
    turbo_cached = downloader.is_turbo_downloaded()
    mtl_cached = downloader.is_mtl_downloaded()
    
    print("Current Status:")
    print(f"  Turbo Model (English, special tokens): {'✓ Cached' if turbo_cached else '✗ Not downloaded'}")
    print(f"  MTL Model (23+ languages):              {'✓ Cached' if mtl_cached else '✗ Not downloaded'}")
    print()
    
    if turbo_cached and mtl_cached:
        print("All models are already downloaded!")
        print(f"Cache location: {downloader.cache_dir}")
        return
    
    print("This script will download the TTS models (one-time setup)")
    print()
    
    # Get HuggingFace token
    token = os.getenv("HF_TOKEN")
    
    if not token:
        print("HuggingFace Token Required")
        print("-" * 70)
        print("To download models, you need a free HuggingFace account token.")
        print()
        print("Steps:")
        print("  1. Go to: https://huggingface.co/settings/tokens")
        print("  2. Click 'New token'")
        print("  3. Give it a name (e.g., 'voice-revolver')")
        print("  4. Select 'Read' access")
        print("  5. Copy the token")
        print()
        print("Then either:")
        print("  - Set environment variable: HF_TOKEN=your_token_here")
        print("  - Or paste it below")
        print()
        
        token = input("Enter your HuggingFace token (or press Enter to skip): ").strip()
        
        if not token:
            print("\nNo token provided. Exiting.")
            print("Set HF_TOKEN environment variable and run this script again.")
            return
    
    print()
    print("Downloading models...")
    print("-" * 70)
    
    # Download Turbo model
    if not turbo_cached:
        print("\n[1/2] Downloading Turbo Model (~350MB)...")
        success, error, path = downloader.download_turbo(token=token)
        
        if success:
            print(f"  ✓ Turbo model downloaded: {path}")
        else:
            print(f"  ✗ Failed: {error}")
            return
    else:
        print("\n[1/2] Turbo model already cached ✓")
    
    # Download MTL model
    if not mtl_cached:
        print("\n[2/2] Downloading MTL Model (~500MB)...")
        success, error, path = downloader.download_mtl(token=token)
        
        if success:
            print(f"  ✓ MTL model downloaded: {path}")
        else:
            print(f"  ✗ Failed: {error}")
            # MTL might not require token, suggest trying without
            if "token" in str(error).lower():
                print("  Note: If you don't need MTL (multilingual), you can skip it.")
    else:
        print("\n[2/2] MTL model already cached ✓")
    
    print()
    print("=" * 70)
    print("Setup Complete!")
    print("=" * 70)
    print(f"Models cached at: {downloader.cache_dir}")
    print()
    print("You can now use Voice Revolver without requiring HuggingFace")
    print("authentication again (models are loaded from local cache).")
    print()


if __name__ == "__main__":
    main()
