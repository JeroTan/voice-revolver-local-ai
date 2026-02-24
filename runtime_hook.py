"""
PyInstaller Runtime Hook for Voice Revolver AI
Executed at application startup when running from .exe

Handles:
- Detection of frozen (PyInstaller) environment
- Extraction of bundled virtual environments on first run
- Setting up environment variables for subprocess wrappers
- Logging setup
"""

import os
import sys
import shutil
from pathlib import Path

def setup_frozen_environment():
    """Configure environment when running from PyInstaller .exe"""
    
    # Only run if frozen (packaged as .exe)
    if not getattr(sys, 'frozen', False):
        return
    
    print("[RUNTIME] Running from packaged executable")
    
    # Get bundle directory (where PyInstaller extracted files)
    bundle_dir = Path(sys._MEIPASS)
    print(f"[RUNTIME] Bundle directory: {bundle_dir}")
    
    # Set up application data directory
    app_data = Path.home() / "AppData" / "Local" / "VoiceRevolverAI"
    app_data.mkdir(parents=True, exist_ok=True)
    print(f"[RUNTIME] App data directory: {app_data}")
    
    # Extract virtual environments on first run
    venvs_dir = app_data / "venvs"
    first_run_marker = venvs_dir / ".extracted"
    
    if not first_run_marker.exists():
        print("[FIRST RUN] Extracting virtual environments...")
        print("This may take a few minutes...")
        
        venvs_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract venv-rvc (required for Voice Cloning & Audio Training)
        _extract_venv(bundle_dir, venvs_dir, "venv-rvc", required=True)
        
        # Extract venv-mdx (optional for MDX separation)
        _extract_venv(bundle_dir, venvs_dir, "venv-mdx", required=False)
        
        # Extract venv-enhance (optional for Resemble Enhance)
        _extract_venv(bundle_dir, venvs_dir, "venv-enhance", required=False)
        
        # Mark as extracted
        first_run_marker.write_text("Virtual environments extracted successfully")
        print("[FIRST RUN] Virtual environments ready!")
    
    # Set environment variable so subprocess wrappers can find virtual environments
    os.environ['VOICE_REVOLVER_VENV_DIR'] = str(venvs_dir)
    os.environ['VOICE_REVOLVER_APP_DATA'] = str(app_data)
    
    print(f"[RUNTIME] Environment configured")
    print(f"[RUNTIME] VOICE_REVOLVER_VENV_DIR={venvs_dir}")


def _extract_venv(bundle_dir, venvs_dir, venv_name, required=True):
    """Extract a single virtual environment from bundle."""
    
    src = bundle_dir / "bundled_venvs" / venv_name
    dst = venvs_dir / venv_name
    
    if not src.exists():
        if required:
            print(f"  ⚠ WARNING: {venv_name} not found in bundle (required!)")
        else:
            print(f"  ℹ {venv_name} not included in build (optional)")
        return False
    
    if dst.exists():
        print(f"  ✓ {venv_name} already extracted")
        return True
    
    try:
        print(f"  → Extracting {venv_name}...")
        shutil.copytree(src, dst, symlinks=True)
        
        # Verify Python executable exists
        python_exe = dst / "Scripts" / "python.exe"
        if python_exe.exists():
            print(f"  ✓ {venv_name} extracted successfully")
            return True
        else:
            print(f"  ✗ {venv_name} extraction failed: python.exe not found")
            return False
            
    except Exception as e:
        print(f"  ✗ Error extracting {venv_name}: {e}")
        return False


# Run setup immediately when this module is imported
setup_frozen_environment()
