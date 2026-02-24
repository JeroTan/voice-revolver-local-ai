"""
Build Windows Installer for Voice Revolver AI
Uses PyInstaller + Inno Setup to create a full installer package
"""

import subprocess
import sys
from pathlib import Path
import shutil

# Colors for console output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}  {text}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ {text}{Colors.END}")

def print_step(text):
    print(f"\n{Colors.BOLD}{text}{Colors.END}")

def check_inno_setup():
    """Check if Inno Setup is installed"""
    print_step("Checking for Inno Setup...")
    
    # Common Inno Setup installation paths
    possible_paths = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 6\ISCC.exe"),
        Path(r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe"),
        Path(r"C:\Program Files\Inno Setup 5\ISCC.exe"),
    ]
    
    for path in possible_paths:
        if path.exists():
            print_success(f"Found Inno Setup: {path}")
            return path
    
    # Try to find in PATH
    try:
        result = subprocess.run(['where', 'ISCC.exe'], 
                              capture_output=True, 
                              text=True, 
                              check=True)
        path = Path(result.stdout.strip().split('\n')[0])
        print_success(f"Found Inno Setup in PATH: {path}")
        return path
    except:
        pass
    
    print_error("Inno Setup not found!")
    print_info("Please install Inno Setup 6 from: https://jrsoftware.org/isdl.php")
    print_info("Direct download: https://jrsoftware.org/download.php/is.exe")
    return None

def build_pyinstaller():
    """Build the PyInstaller folder"""
    print_step("Building PyInstaller folder structure...")
    print_info("This will take 10-15 minutes...")
    
    try:
        result = subprocess.run(
            [sys.executable, 'build_portable.py'],
            check=True,
            capture_output=False
        )
        print_success("PyInstaller build completed!")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"PyInstaller build failed: {e}")
        return False

def build_installer(iscc_path):
    """Build the installer using Inno Setup"""
    print_step("Building installer with Inno Setup...")
    print_info("This will take 15-30 minutes (compressing 19GB)...")
    
    script_path = Path("installer.iss")
    
    if not script_path.exists():
        print_error(f"Installer script not found: {script_path}")
        return False
    
    try:
        # Create installer output directory
        installer_dir = Path("build/installer")
        installer_dir.mkdir(parents=True, exist_ok=True)
        
        # Run Inno Setup compiler
        result = subprocess.run(
            [str(iscc_path), str(script_path)],
            check=True,
            capture_output=True,
            text=True
        )
        
        print_success("Installer created successfully!")
        
        # Find the created installer
        installers = list(installer_dir.glob("VoiceRevolverAI-Setup-*.exe"))
        if installers:
            installer = installers[0]
            size_mb = installer.stat().st_size / (1024 * 1024)
            print_success(f"Installer: {installer.name}")
            print_success(f"Size: {size_mb:.2f} MB")
            print_success(f"Location: {installer.absolute()}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"Installer build failed!")
        print_error(f"Error: {e.stderr}")
        return False

def main():
    print(f"""
{Colors.BOLD}{Colors.HEADER}
╔════════════════════════════════════════════════════════════╗
║   Voice Revolver AI - Windows Installer Builder           ║
╚════════════════════════════════════════════════════════════╝
{Colors.END}
    """)
    
    # Step 1: Check Inno Setup
    print_header("Step 1: Check Prerequisites")
    iscc_path = check_inno_setup()
    if not iscc_path:
        print_error("\nInstallation instructions:")
        print("1. Download Inno Setup: https://jrsoftware.org/download.php/is.exe")
        print("2. Run the installer (default installation path is fine)")
        print("3. Run this script again")
        sys.exit(1)
    
    # Step 2: Build PyInstaller folder
    print_header("Step 2: Build PyInstaller Application")
    if not build_pyinstaller():
        print_error("\nPyInstaller build failed. Please check the errors above.")
        sys.exit(1)
    
    # Step 3: Check if build output exists
    build_dir = Path("build/VoiceRevolverAI")
    if not build_dir.exists():
        print_error(f"Build directory not found: {build_dir}")
        sys.exit(1)
    
    exe_path = build_dir / "VoiceRevolverAI.exe"
    if not exe_path.exists():
        print_error(f"Executable not found: {exe_path}")
        sys.exit(1)
    
    print_success(f"Build folder verified: {build_dir}")
    
    # Step 4: Build installer
    print_header("Step 3: Build Windows Installer")
    if not build_installer(iscc_path):
        print_error("\nInstaller build failed. Please check the errors above.")
        sys.exit(1)
    
    # Success!
    print_header("Build Complete!")
    print(f"""
{Colors.GREEN}
✓ Installer has been created successfully!
  
  Location: build/installer/VoiceRevolverAI-Setup-v1.0.0.exe
  
  You can now:
  1. Test the installer on this machine
  2. Distribute the installer to other Windows 10/11 systems
  
  Installation requirements:
  - Windows 10/11 (64-bit)
  - ~22 GB free disk space
  - Administrator privileges
  
  First-run notes:
  - Installation will take 10-30 minutes
  - First launch will extract venvs to AppData (~2-3 minutes)
  - Console window will show alongside the GUI for logs
{Colors.END}
    """)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\n\n❌ Build cancelled by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
