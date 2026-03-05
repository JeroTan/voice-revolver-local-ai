"""
Resemble Enhance Wrapper - AI-powered speech denoising and enhancement

This module wraps the Resemble Enhance library for high-quality vocal enhancement.
Uses RK4 solver with 100 steps for maximum quality.

IMPORTANT: Resemble Enhance runs in a separate virtual environment (venv-enhance)
due to dependency conflicts (scipy, numpy, deepspeed). This wrapper calls it via
subprocess, similar to how MDX separation works.

Reference: https://github.com/resemble-ai/resemble-enhance
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional, Callable

from .venv_utils import get_venv_python as get_venv_python_util

logger = logging.getLogger(__name__)


def get_venv_python() -> Optional[Path]:
    """
    Get the Python executable path for venv-enhance.
    Wrapper around venv_utils for backwards compatibility.
    
    Returns:
        Path to Python executable in venv-enhance, or None if not found
    """
    try:
        return get_venv_python_util('venv-enhance')
    except (FileNotFoundError, RuntimeError):
        return None


def enhance_vocals(
    input_path: Path,
    output_path: Path,
    solver: str = "rk4",
    nfe: int = 100,
    temperature: float = 0.33,
    denoise_first: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Enhance vocals using Resemble Enhance with high-quality settings.
    
    This applies AI-powered denoising and enhancement to improve speech quality.
    The model performs:
    1. Denoising: Separates speech from background noise
    2. Enhancement: Restores audio distortions and extends bandwidth
    
    NOTE: Runs in separate venv-enhance environment via subprocess.
    
    Args:
        input_path: Path to input vocal audio file
        output_path: Path where enhanced audio will be saved
        solver: Numerical solver ('euler', 'midpoint', 'rk4')
                Default: 'rk4' (highest quality, slower)
        nfe: Number of function evaluations (1-128)
             Higher = better quality but slower
             Default: 100 (high quality)
        temperature: Prior temperature (0.01-1.0)
                    Higher can improve quality but may reduce stability
                    Default: 0.33 (recommended)
        denoise_first: Whether to apply denoising before enhancement
                      Default: False (vocals already separated)
        progress_callback: Optional callback function for progress updates
    
    Returns:
        bool: True if enhancement succeeded, False otherwise
    
    Example:
        >>> success = enhance_vocals(
        ...     Path("vocals.wav"),
        ...     Path("vocals_enhanced.wav")
        ... )
    """
    try:
        # Check if venv-enhance exists
        venv_python = get_venv_python()
        if not venv_python:
            logger.error("venv-enhance not found. Please create it:")
            logger.error("  python -m venv venv-enhance")
            logger.error("  .\\venv-enhance\\Scripts\\Activate.ps1")
            logger.error("  pip install resemble-enhance --upgrade")
            if progress_callback:
                progress_callback(0, "❌ venv-enhance not installed")
            return False
        
        if progress_callback:
            progress_callback(0, f"Starting vocal enhancement (RK4, {nfe} steps)...")
        
        logger.info(f"Enhancing vocals: {input_path}")
        logger.info(f"Settings: solver={solver}, nfe={nfe}, temperature={temperature}")
        logger.info(f"Using venv: {venv_python}")        
        
        # Convert paths to Path objects if they're strings
        input_path = Path(input_path) if isinstance(input_path, str) else input_path
        output_path = Path(output_path) if isinstance(output_path, str) else output_path
        
        # Convert paths to absolute strings
        input_str = str(input_path.resolve())
        output_str = str(output_path.resolve())
        
        # Path to our helper script
        script_path = Path(__file__).parent / "enhance_single_file.py"
        
        # Build command to run our helper script in venv-enhance
        # This script uses the Python API directly instead of the broken CLI
        def _build_cmd(device: str):
            c = [
                str(venv_python),
                str(script_path),
                input_str,
                output_str,
                "--solver", solver,
                "--nfe", str(nfe),
                "--tau", str(temperature),  # Note: API uses 'tau' not 'temp'
                "--device", device
            ]
            if denoise_first:
                c.append("--denoise")
            return c
        
        cmd = _build_cmd("cuda")
        
        logger.info(f"Running command: {' '.join(cmd)}")
        
        if progress_callback:
            progress_callback(10, "Enhancement running on GPU (this may take a few minutes)...")
        
        # Run enhancement in subprocess
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600  # 10 minute timeout
        )
        
        # Check for CUDA/GPU errors - return special status to let UI ask user
        if process.returncode != 0:
            stderr_text = process.stderr or ""
            cuda_error_keywords = [
                "GET was unable to find an engine",
                "CUDA error",
                "CUDA out of memory",
                "cudnn",
                "cuDNN",
                "CUBLAS_STATUS",
            ]
            is_cuda_error = any(kw.lower() in stderr_text.lower() for kw in cuda_error_keywords)
            
            if is_cuda_error:
                logger.warning(f"CUDA enhancement failed: {stderr_text[-200:]}")
                if progress_callback:
                    progress_callback(0, "⚠ GPU enhancement failed")
                return "cuda_failed"  # Special return value for CUDA failure
            else:
                # Non-CUDA error, don't offer retry
                logger.error(f"Enhancement failed with return code {process.returncode}")
                logger.error(f"STDOUT: {process.stdout}")
                logger.error(f"STDERR: {process.stderr}")
                if progress_callback:
                    progress_callback(100, f"❌ Enhancement failed: {stderr_text[:100]}")
                return False
        
        # Log output
        if process.stdout:
            logger.info(f"Enhancement output: {process.stdout}")
        
        # Verify output was created
        if not output_path.exists():
            logger.error(f"Enhancement failed: output file not created at {output_path}")
            if progress_callback:
                progress_callback(100, "❌ Enhancement failed: no output file")
            return False
        
        # Check if output has audio data
        if output_path.stat().st_size == 0:
            logger.error(f"Enhancement failed: output file is empty at {output_path}")
            if progress_callback:
                progress_callback(100, "❌ Enhancement failed: empty output")
            return False
        
        logger.info(f"Enhancement complete: {output_path}")
        if progress_callback:
            progress_callback(100, "✓ Vocal enhancement complete")
        
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("Enhancement timed out after 10 minutes")
        if progress_callback:
            progress_callback(100, "❌ Enhancement timed out")
        return False
        
    except Exception as e:
        logger.error(f"Enhancement failed with error: {e}", exc_info=True)
        if progress_callback:
            progress_callback(100, f"❌ Enhancement failed: {e}")
        return False


def enhance_vocals_cpu(
    input_path: Path,
    output_path: Path,
    solver: str = "rk4",
    nfe: int = 100,
    temperature: float = 0.33,
    denoise_first: bool = False,
    progress_callback: Optional[Callable[[str], None]] = None
) -> bool:
    """
    Run vocal enhancement on CPU. Called as fallback when GPU fails and user agrees.
    
    Returns:
        bool: True if enhancement succeeded, False otherwise
    """
    try:
        venv_python = get_venv_python()
        if not venv_python:
            return False
        
        input_path = Path(input_path) if isinstance(input_path, str) else input_path
        output_path = Path(output_path) if isinstance(output_path, str) else output_path
        
        input_str = str(input_path.resolve())
        output_str = str(output_path.resolve())
        script_path = Path(__file__).parent / "enhance_single_file.py"
        
        cmd = [
            str(venv_python),
            str(script_path),
            input_str,
            output_str,
            "--solver", solver,
            "--nfe", str(nfe),
            "--tau", str(temperature),
            "--device", "cpu"
        ]
        if denoise_first:
            cmd.append("--denoise")
        
        logger.info(f"Running CPU enhancement: {' '.join(cmd)}")
        
        if progress_callback:
            progress_callback(10, "Enhancement running on CPU (this will be slower)...")
        
        process = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800  # 30 minute timeout for CPU
        )
        
        if process.returncode != 0:
            logger.error(f"CPU enhancement failed: {process.stderr}")
            if progress_callback:
                progress_callback(100, "❌ Enhancement failed on CPU")
            return False
        
        if not output_path.exists() or output_path.stat().st_size == 0:
            logger.error(f"CPU enhancement produced no output")
            if progress_callback:
                progress_callback(100, "❌ Enhancement failed: no output")
            return False
        
        logger.info(f"CPU enhancement complete: {output_path}")
        if progress_callback:
            progress_callback(100, "✓ Vocal enhancement complete (CPU)")
        return True
        
    except subprocess.TimeoutExpired:
        logger.error("CPU enhancement timed out after 30 minutes")
        if progress_callback:
            progress_callback(100, "❌ Enhancement timed out on CPU")
        return False
    except Exception as e:
        logger.error(f"CPU enhancement error: {e}", exc_info=True)
        if progress_callback:
            progress_callback(100, f"❌ Enhancement failed: {e}")
        return False


def is_resemble_enhance_available() -> bool:
    """
    Check if Resemble Enhance is installed in venv-enhance.
    
    Returns:
        bool: True if venv-enhance exists and has resemble-enhance installed
    """
    venv_python = get_venv_python()
    if not venv_python:
        return False
    
    # Try importing resemble_enhance in the venv
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import resemble_enhance"],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def get_estimated_time(audio_duration_seconds: float, device: str = "gpu") -> float:
    """
    Estimate enhancement processing time based on audio duration.
    
    These are rough estimates based on RK4 solver with 100 steps.
    
    Args:
        audio_duration_seconds: Duration of input audio in seconds
        device: 'gpu' or 'cpu'
    
    Returns:
        float: Estimated processing time in seconds
    
    Example:
        >>> # 180 second (3 minute) song
        >>> estimate = get_estimated_time(180, "gpu")
        >>> print(f"Estimated: {estimate:.0f} seconds")
        Estimated: 90 seconds
    """
    if device.lower() == "gpu":
        # RK4 with 100 steps: ~0.5x realtime on modern GPU
        # 3 minute song = ~90 seconds
        return audio_duration_seconds * 0.5
    else:
        # CPU is much slower: ~3-5x realtime
        # 3 minute song = ~9-15 minutes
        return audio_duration_seconds * 4.0
