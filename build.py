#!/usr/bin/env python3
"""
Build script for Voice Revolver AI
Run this to build the portable executable
"""

import os
import sys
import subprocess


def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    
    required = ['pyinstaller']
    missing = []
    
    for dep in required:
        try:
            __import__(dep)
        except ImportError:
            missing.append(dep)
    
    if missing:
        print(f"Missing dependencies: {', '.join(missing)}")
        print("Install with: pip install pyinstaller")
        return False
    
    return True


def build_windows():
    """Build Windows executable"""
    print("Building Windows executable...")
    
    spec_file = os.path.join(os.path.dirname(__file__), 'voice_revolver.spec')
    
    cmd = [
        'pyinstaller',
        spec_file,
        '--distpath', 'dist/windows',
        '--workpath', 'build/windows/temp',
    ]
    
    subprocess.run(cmd, check=True)
    print("Build complete! Executable in dist/windows/")


def build_macos():
    """Build macOS app (requires running on macOS)"""
    if sys.platform != 'darwin':
        print("macOS build requires running on macOS")
        return
    
    print("Building macOS app...")
    
    # Similar to Windows but outputs .app
    spec_file = os.path.join(os.path.dirname(__file__), 'voice_revolver.spec')
    
    cmd = [
        'pyinstaller',
        spec_file,
        '--distpath', 'dist/mac',
        '--workpath', 'build/mac/temp',
    ]
    
    subprocess.run(cmd, check=True)
    print("Build complete! App in dist/mac/")


def main():
    if not check_dependencies():
        sys.exit(1)
    
    if len(sys.argv) < 2:
        print("Usage: python build.py [windows|mac]")
        sys.exit(1)
    
    platform = sys.argv[1].lower()
    
    if platform == 'windows':
        build_windows()
    elif platform == 'mac':
        build_macos()
    else:
        print(f"Unknown platform: {platform}")


if __name__ == '__main__':
    main()
