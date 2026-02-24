"""
Virtual Environment Path Utilities

Handles venv path resolution for both development and .exe (frozen) modes.
Allows Voice Revolver AI to run as portable .exe with venvs extracted to AppData.
"""

import sys
import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def is_frozen() -> bool:
    """
    Check if running from PyInstaller .exe bundle.
    
    Returns:
        True if frozen, False if running from source
    """
    return getattr(sys, 'frozen', False)


def get_venv_python(venv_name: str) -> Path:
    """
    Get venv Python executable path (works in both dev and .exe modes).
    
    In .exe mode: Uses VOICE_REVOLVER_VENV_DIR from runtime_hook.py
    In dev mode: Uses project_root/venv_name
    
    Args:
        venv_name: Name of venv ('venv-rvc', 'venv-mdx', 'venv-enhance')
    
    Returns:
        Path to Python executable
    
    Raises:
        FileNotFoundError: If venv not found
        RuntimeError: If VOICE_REVOLVER_VENV_DIR not set in frozen mode
    """
    if is_frozen():
        # Running from .exe - use extracted venvs in AppData
        venv_dir = os.environ.get('VOICE_REVOLVER_VENV_DIR')
        if not venv_dir:
            raise RuntimeError(
                "VOICE_REVOLVER_VENV_DIR environment variable not set.\n"
                "This should be set by runtime_hook.py during .exe startup."
            )
        
        venv_path = Path(venv_dir) / venv_name
        python_exe = venv_path / "Scripts" / "python.exe"
        
        if not python_exe.exists():
            raise FileNotFoundError(
                f"Virtual environment not found: {venv_name}\n"
                f"Expected location: {python_exe}\n\n"
                f"This venv should have been extracted during first run.\n"
                f"Try deleting: {Path(venv_dir).parent} and restarting the application."
            )
        
        logger.info(f"Using venv (frozen mode): {python_exe}")
        return python_exe
    
    else:
        # Development mode - use project venvs
        project_root = Path(__file__).parent.parent.parent
        venv_path = project_root / venv_name
        python_exe = venv_path / "Scripts" / "python.exe"
        
        if not python_exe.exists():
            # Try Linux/Mac path
            python_exe_unix = venv_path / "bin" / "python"
            if python_exe_unix.exists():
                logger.info(f"Using venv (dev mode): {python_exe_unix}")
                return python_exe_unix
            
            raise FileNotFoundError(
                f"Virtual environment not found: {venv_name}\n"
                f"Expected location: {python_exe}\n\n"
                f"To create this environment, run:\n"
                f"  python -m venv {venv_name}\n"
                f"  .\\{venv_name}\\Scripts\\Activate.ps1\n"
                f"  pip install -r requirements-{venv_name.replace('venv-', '')}.txt"
            )
        
        logger.info(f"Using venv (dev mode): {python_exe}")
        return python_exe


def get_project_root() -> Path:
    """
    Get project root directory.
    
    In .exe mode: Returns _MEIPASS (PyInstaller temp directory)
    In dev mode: Returns actual project root
    
    Returns:
        Path to project root
    """
    if is_frozen():
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return Path(sys._MEIPASS)
    else:
        # Development mode - go up from infrastructure/
        return Path(__file__).parent.parent.parent
