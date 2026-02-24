"""
Build Portable .exe for Voice Revolver AI

Usage: python build_portable.py

This script:
1. Checks prerequisites (PyInstaller, venvs)
2. Runs PyInstaller with voice_revolver.spec
3. Outputs to ./build/VoiceRevolverAI/
4. Creates README and build documentation
5. Reports build size and next steps
"""

import subprocess
import shutil
import sys
from pathlib import Path
from datetime import datetime


def print_header(text):
    """Print a formatted header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}\n")


def check_prerequisites():
    """Verify build requirements."""
    print_header("Checking Prerequisites")
    
    issues = []
    
    # Check PyInstaller
    try:
        import PyInstaller
        print(f"✓ PyInstaller {PyInstaller.__version__} installed")
    except ImportError:
        print("✗ PyInstaller not found")
        issues.append("Install PyInstaller: pip install pyinstaller")
    
    # Check main virtual environment
    main_venvs = ['.venv-1', '.venv', 'venv']
    main_venv_found = False
    for venv_name in main_venvs:
        venv_path = Path(venv_name)
        if venv_path.exists():
            print(f"✓ Main venv found: {venv_name}")
            main_venv_found = True
            break
    
    if not main_venv_found:
        print("✗ No main virtual environment found")
        issues.append("Create main venv: python -m venv .venv-1")
    
    # Check optional venvs (will be bundled if exist)
    optional_venvs = ['venv-rvc', 'venv-mdx', 'venv-enhance']
    for venv in optional_venvs:
        venv_path = Path(venv)
        if venv_path.exists():
            # Check size to estimate bundle impact
            size_mb = sum(f.stat().st_size for f in venv_path.rglob('*') if f.is_file()) / 1024 / 1024
            print(f"✓ {venv} found ({size_mb:.0f} MB) - will be bundled")
        else:
            print(f"ℹ {venv} not found (optional, skipping)")
    
    # Check RVC module
    rvc_path = Path('rvc')
    if rvc_path.exists():
        print(f"✓ RVC module found")
    else:
        print(f"⚠ RVC module not found (required for Audio Training)")
        issues.append("RVC module missing - some features may not work")
    
    # Check assets
    assets_path = Path('assets')
    if assets_path.exists():
        print(f"✓ Assets folder found")
    else:
        print(f"⚠ Assets folder not found")
        issues.append("Assets folder missing - create it or some features may fail")
    
    # Check icon
    icon_path = Path('icon.ico')
    if icon_path.exists():
        print(f"✓ Icon file found")
    else:
        print(f"ℹ Icon file not found (will use default)")
    
    # Check spec file
    spec_path = Path('voice_revolver.spec')
    if spec_path.exists():
        print(f"✓ Spec file found")
    else:
        print(f"✗ voice_revolver.spec not found")
        issues.append("Spec file missing - cannot build without it")
    
    if issues:
        print(f"\n❌ Build cannot proceed. Issues found:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    else:
        print(f"\n✅ All prerequisites met!")
        return True


def clean_build_dirs():
    """Clean previous build artifacts."""
    print_header("Cleaning Previous Builds")
    
    # Remove PyInstaller work directories
    work_dir = Path('build/pyinstaller_work')
    if work_dir.exists():
        print(f"Removing {work_dir}...")
        shutil.rmtree(work_dir)
    
    # Remove old dist directory
    dist_dir = Path('dist')
    if dist_dir.exists():
        print(f"Removing {dist_dir}...")
        shutil.rmtree(dist_dir)
    
    print("✓ Clean complete")


def build_exe():
    """Run PyInstaller build."""
    print_header("Building Executable")
    
    print("This will take 5-15 minutes depending on your system...")
    print("Building...\n")
    
    cmd = [
        sys.executable,  # Use current Python interpreter
        "-m", "PyInstaller",
        "--clean",  # Clean cache
        "--distpath", "build",  # Output to build/ instead of dist/
        "--workpath", "build/pyinstaller_work",  # Temp files in build/
        "voice_revolver.spec"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=False)
        
        if result.returncode == 0:
            print("\n✓ Build successful!")
            return True
        else:
            print(f"\n✗ Build failed with code {result.returncode}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n✗ Build failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return False


def create_readme():
    """Create README for distribution."""
    print_header("Creating Documentation")
    
    build_dir = Path("build/VoiceRevolverAI")
    
    readme_content = f"""
╔══════════════════════════════════════════════════════════════╗
║           Voice Revolver AI - Portable Edition               ║
║                                                              ║
║  AI-Powered Audio Workstation for Voice Cloning,            ║
║  Vocal Replacement, Stem Separation & Audio Training        ║
╚══════════════════════════════════════════════════════════════╝

BUILD DATE: {datetime.now().strftime('%Y-%m-%d %H:%M')}
VERSION: 1.0 (All 7 workspaces included)

════════════════════════════════════════════════════════════════
 HOW TO RUN
════════════════════════════════════════════════════════════════

1. Double-click: VoiceRevolverAI.exe

2. TWO WINDOWS WILL APPEAR:
   ┌─────────────────────────────────────┐
   │ CONSOLE WINDOW (Terminal)           │  ← Shows logs & debugging info
   │ - Keep this open while using app    │
   │ - Real-time processing updates      │
   │ - Error messages appear here        │
   └─────────────────────────────────────┘
   
   ┌─────────────────────────────────────┐
   │ MAIN APPLICATION WINDOW             │  ← Your workspace
   │ - 7 workspaces for audio tasks      │
   │ - Tkinter GUI interface             │
   └─────────────────────────────────────┘

3. FIRST RUN (5-10 minutes):
   - Extracts virtual environments
   - Downloads AI models (requires internet)
   - Creates AppData folder

4. SELECT DEVICE:
   - GPU (CUDA): For NVIDIA graphics cards (10-20x faster)
   - CPU: For any computer (works but slower)

════════════════════════════════════════════════════════════════
 SYSTEM REQUIREMENTS
════════════════════════════════════════════════════════════════

MINIMUM (CPU Mode):
  • OS: Windows 10/11 (64-bit)
  • CPU: Intel Core i5 / AMD Ryzen 5 (4+ cores)
  • RAM: 8 GB
  • Storage: 10 GB free space
  • Internet: Required for first run only

RECOMMENDED (GPU Mode):
  • OS: Windows 10/11 (64-bit)
  • CPU: Intel Core i7 / AMD Ryzen 7
  • GPU: NVIDIA RTX 3060 / RTX 4050 or better (6GB+ VRAM)
  • RAM: 16 GB
  • Storage: 15 GB free space
  • CUDA: Toolkit 11.8 (for GPU acceleration)

════════════════════════════════════════════════════════════════
 7 WORKSPACES INCLUDED
════════════════════════════════════════════════════════════════

1. VOCAL CHANGER - Replace vocals in songs
2. AUDIO SEPARATION - Extract stems (vocals, drums, bass, other)
3. TEXT TO SPEECH - Generate speech with voice cloning
4. VOICE CLONING - Clone voices from audio or RVC models
5. VOICE ENHANCEMENT - AI denoising and audio effects
6. TRACK MERGER - Combine multiple audio files
7. AUDIO TRAINING - Train custom RVC voice models

════════════════════════════════════════════════════════════════
 FILE LOCATIONS
════════════════════════════════════════════════════════════════

Application Data:
  C:\\Users\\YOUR_NAME\\AppData\\Local\\VoiceRevolverAI\\

├── models/          AI model checkpoints (auto-downloaded)
├── temp/           Temporary processing files
├── logs/           Application logs
│   └── app.log     Main log file (check for errors)
└── venvs/          Extracted virtual environments
    ├── venv-rvc/   RVC training/cloning
    ├── venv-mdx/   MDX separation (optional)
    └── venv-enhance/ Resemble Enhance (optional)

════════════════════════════════════════════════════════════════
 TROUBLESHOOTING
════════════════════════════════════════════════════════════════

ISSUE: Console window closes immediately
  → Check logs: C:\\Users\\YOUR_NAME\\AppData\\Local\\VoiceRevolverAI\\logs\\app.log
  → Run from Command Prompt to see error: VoiceRevolverAI.exe

ISSUE: "GPU not detected" but you have NVIDIA GPU
  → Install CUDA Toolkit 11.8:
    https://developer.nvidia.com/cuda-11-8-0-download-archive
  → Update NVIDIA drivers
  → Restart computer

ISSUE: "DLL load failed" or "module not found"
  → Install Visual C++ Redistributable (x64):
    https://aka.ms/vs/17/release/vc_redist.x64.exe
  → Restart computer

ISSUE: Slow processing even with GPU
  → GPU may not be enabled - check console for CUDA messages
  → Try CPU mode first to verify app works

ISSUE: Models not downloading
  → Check internet connection
  → Temporarily disable antivirus/firewall
  → Check AppData permissions

ISSUE: "Out of memory" errors
  → Close other applications
  → Use CPU mode instead of GPU
  → Reduce batch size in RVC training

════════════════════════════════════════════════════════════════
 IN-APP HELP
════════════════════════════════════════════════════════════════

• Press F12: Show/hide in-app log window
• Workspace Menu: Switch between 7 workspaces
• Each workspace has tooltips and help text

════════════════════════════════════════════════════════════════
 SUPPORT & DOCUMENTATION
════════════════════════════════════════════════════════════════

GitHub: https://github.com/JeroTan/voice-revolver-local-ai
Issues: https://github.com/JeroTan/voice-revolver-local-ai/issues
Docs:   https://github.com/JeroTan/voice-revolver-local-ai/tree/main/docs

════════════════════════════════════════════════════════════════
 LICENSE
════════════════════════════════════════════════════════════════

MIT License - Free to use, modify, and distribute
See LICENSE file or repository for full terms

Voice Revolver AI uses these open-source projects:
• PyTorch (BSD) • Demucs (MIT) • ChatterBox (MIT)
• RVC/Applio (MIT) • Resemble Enhance (Apache 2.0)

════════════════════════════════════════════════════════════════

Made with ❤️ by the Voice Revolver AI Team
100% Local • 100% Open Source

Documentation written by AI (Claude Sonnet 4.6)
"Automation with Human Touch"

════════════════════════════════════════════════════════════════
"""
    
    readme_path = build_dir / "README.txt"
    readme_path.write_text(readme_content, encoding='utf-8')
    print(f"✓ README created: {readme_path}")
    
    return True


def generate_build_report():
    """Generate build report with size and details."""
    print_header("Build Report")
    
    build_dir = Path("build/VoiceRevolverAI")
    
    if not build_dir.exists():
        print("✗ Build directory not found")
        return False
    
    # Calculate total size
    total_size = sum(f.stat().st_size for f in build_dir.rglob('*') if f.is_file())
    total_size_mb = total_size / 1024 / 1024
    total_size_gb = total_size / 1024 / 1024 / 1024
    
    # Count files
    file_count = sum(1 for f in build_dir.rglob('*') if f.is_file())
    
    # Check for exe
    exe_path = build_dir / "VoiceRevolverAI.exe"
    exe_exists = exe_path.exists()
    
    print(f"Build Directory: {build_dir.absolute()}")
    print(f"Total Size: {total_size_mb:.1f} MB ({total_size_gb:.2f} GB)")
    print(f"File Count: {file_count:,} files")
    print(f"Executable: {'✓ Found' if exe_exists else '✗ Not found'}")
    
    # Size breakdown
    print(f"\nSize Breakdown (approximate):")
    
    # Check major components
    components = {
        'Python Libraries': '_internal',
        'RVC Module': 'rvc',
        'Assets': 'assets',
        'Bundled Venvs': 'bundled_venvs',
    }
    
    for name, folder in components.items():
        folder_path = build_dir / folder
        if folder_path.exists():
            folder_size = sum(f.stat().st_size for f in folder_path.rglob('*') if f.is_file())
            folder_size_mb = folder_size / 1024 / 1024
            print(f"  - {name}: {folder_size_mb:.1f} MB")
    
    return exe_exists


def print_next_steps():
    """Print next steps for user."""
    print_header("Next Steps")
    
    build_dir = Path("build/VoiceRevolverAI")
    exe_path = build_dir / "VoiceRevolverAI.exe"
    
    print("BUILD COMPLETE! 🎉\n")
    print("To test the portable app:")
    print(f"  1. Navigate to: {build_dir.absolute()}")
    print(f"  2. Double-click: VoiceRevolverAI.exe")
    print(f"  3. Console window + Main app window will appear")
    print(f"  4. Wait for first-run setup (extracts venvs)")
    print(f"  5. Test all 7 workspaces\n")
    
    print("To distribute:")
    print(f"  Option 1: ZIP the folder")
    print(f"    - Compress-Archive -Path '{build_dir}' -DestinationPath 'VoiceRevolverAI-v1.0-Windows.zip'")
    print(f"  Option 2: Use Inno Setup to create installer.exe")
    print(f"  Option 3: Share the folder directly\n")
    
    print("Testing on clean system:")
    print(f"  - Copy entire folder to test machine")
    print(f"  - No Python installation needed")
    print(f"  - May need Visual C++ Redistributable")
    print(f"  - CUDA Toolkit needed for GPU mode\n")


def main():
    """Main build process."""
    print("")
    print("╔════════════════════════════════════════════════════════════╗")
    print("║   Voice Revolver AI - Portable .exe Build Script          ║")
    print("╚════════════════════════════════════════════════════════════╝")
    
    # Step 1: Check prerequisites
    if not check_prerequisites():
        print("\n❌ Build aborted due to missing prerequisites")
        sys.exit(1)
    
    # Step 2: Clean previous builds
    clean_build_dirs()
    
    # Step 3: Build executable
    if not build_exe():
        print("\n❌ Build failed")
        sys.exit(1)
    
    # Step 4: Create documentation
    create_readme()
    
    # Step 5: Generate report
    if not generate_build_report():
        print("\n⚠ Build succeeded but verification failed")
    
    # Step 6: Print next steps
    print_next_steps()
    
    print("╔════════════════════════════════════════════════════════════╗")
    print("║                   BUILD SUCCESSFUL!                        ║")
    print("╚════════════════════════════════════════════════════════════╝\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
