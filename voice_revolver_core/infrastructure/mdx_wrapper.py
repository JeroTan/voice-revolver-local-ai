"""
MDX Wrapper - Infrastructure Layer  
High-quality vocal separation using MDX23C model from audio-separator
Runs in isolated venv-mdx environment via subprocess to avoid dependency conflicts
"""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional, Tuple, Dict, Callable
import shutil

from .venv_utils import get_venv_python

logger = logging.getLogger(__name__)


class MDXWrapper:
    """
    Infrastructure wrapper for MDX stem separation.
    Uses subprocess to call mdx_standalone.py in venv-mdx environment.
    Separates audio into: vocals, drums, bass, other
    """
    
    MODEL_NAME = "MDX23C-8KFFT-InstVoc_HQ.ckpt"  # Best vocal isolation
    
    def __init__(self, device: Optional[str] = None):
        self._device = device or "cpu"
        self._model_loaded = False
    
    @property
    def device(self) -> str:
        return self._device
    
    @property
    def is_loaded(self) -> bool:
        return self._model_loaded
    
    def load_model(self) -> Tuple[bool, Optional[str]]:
        """
        Check if MDX environment is available.
        Returns: (success, error_message)
        """
        try:
            # Find venv-mdx Python executable
            try:
                mdx_python = get_venv_python('venv-mdx')
            except (FileNotFoundError, RuntimeError) as e:
                error_msg = str(e) + "\n\nOr select 'demucs' for stem separation."
                logger.warning(error_msg)
                return False, error_msg
            
            logger.info(f"MDX environment found: {mdx_python}")
            
            # Warn about CPU performance
            if self._device.lower() == "cpu":
                logger.warning("MDX on CPU is VERY slow (20-30+ minutes per song). Consider using Demucs or GPU acceleration.")
            
            self._model_loaded = True
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to check MDX environment: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def separate(
        self, 
        audio_path: Path, 
        output_dir: Path,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Tuple[Optional[Dict[str, Path]], Optional[str]]:
        """
        Separate audio into stems using MDX model via subprocess.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save separated stems
            progress_callback: Optional callback(percentage, message)
        
        Returns:
            (stem_dict, error_message) where stem_dict contains paths to separated files
        """
        # Auto-load model if not loaded (same as DemucsWrapper)
        if not self._model_loaded:
            success, error = self.load_model()
            if not success:
                return None, error
        
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            if progress_callback:
                progress_callback(5, "Calling MDX subprocess...")
            
            # Find MDX Python executable and standalone script
            mdx_python = get_venv_python('venv-mdx')
            mdx_script = Path(__file__).parent / "mdx_standalone.py"
            
            # Run MDX subprocess
            logger.info(f"Running MDX subprocess: {mdx_python} {mdx_script}")
            
            command = [
                str(mdx_python),
                str(mdx_script),
                str(audio_path),
                str(output_dir),
                self.MODEL_NAME,
                self._device  # Pass device (cuda/cpu) to subprocess
            ]
            
            if progress_callback:
                progress_callback(10, "Separating with MDX...")
            
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=1800  # 30 minutes max (MDX is slow on CPU)
            )
            
            # Log subprocess output
            stderr_text = result.stderr or ""
            if stderr_text:
                for line in stderr_text.strip().split('\n'):
                    if line:
                        logger.info(f"MDX: {line}")
            
            if result.returncode != 0:
                error_msg = f"MDX subprocess failed with code {result.returncode}"
                if stderr_text:
                    error_msg += f"\n{stderr_text}"
                logger.error(error_msg)
                return None, error_msg
            
            # Handle timeout
            if "timed out" in stderr_text.lower():
                logger.error("MDX processing is very slow on CPU. Consider using Demucs or GPU acceleration.")
            
            # Parse JSON result
            result_data = json.loads(result.stdout.strip())
            
            if not result_data.get("success"):
                error_msg = result_data.get("error", "Unknown error")
                logger.error(f"MDX separation failed: {error_msg}")
                return None, error_msg
            
            if progress_callback:
                progress_callback(70, "Processing stems...")
            
            # Get vocals and instrumental paths from JSON result
            vocals_path = Path(result_data["vocals_path"])
            instrumental_path = Path(result_data.get("instrumental_path", ""))
            
            # Check if paths are absolute, if not, assume they're in output_dir
            if not vocals_path.is_absolute():
                vocals_path = output_dir / vocals_path.name
            if instrumental_path and not instrumental_path.is_absolute():
                instrumental_path = output_dir / instrumental_path.name
            
            logger.info(f"MDX returned vocals path: {vocals_path}")
            logger.info(f"MDX returned instrumental path: {instrumental_path}")
            
            # If exact paths don't exist, search for MDX output files by pattern
            if not vocals_path.exists():
                logger.warning(f"Vocals path from JSON doesn't exist: {vocals_path}")
                logger.info("Searching for vocals file by pattern...")
                vocals_files = list(output_dir.glob("*_(Vocals)_*.wav"))
                if vocals_files:
                    vocals_path = vocals_files[0]
                    logger.info(f"Found vocals file: {vocals_path}")
                else:
                    error_msg = f"No vocals file found in {output_dir}"
                    logger.error(error_msg)
                    return None, error_msg
            
            if instrumental_path and not instrumental_path.exists():
                logger.warning(f"Instrumental path from JSON doesn't exist: {instrumental_path}")
                logger.info("Searching for instrumental file by pattern...")
                instrumental_files = list(output_dir.glob("*_(Instrumental)_*.wav"))
                if instrumental_files:
                    instrumental_path = instrumental_files[0]
                    logger.info(f"Found instrumental file: {instrumental_path}")
            
            # Rename to standard format (using generic names)
            final_vocals = output_dir / "vocals.wav"
            final_other = output_dir / "other.wav"
            
            # Delete existing files to avoid conflicts
            if final_vocals.exists():
                try:
                    final_vocals.unlink()
                    logger.info(f"Deleted existing vocals.wav")
                except Exception as e:
                    logger.warning(f"Could not delete existing vocals.wav: {e}")
            
            if final_other.exists():
                try:
                    final_other.unlink()
                    logger.info(f"Deleted existing other.wav")
                except Exception as e:
                    logger.warning(f"Could not delete existing other.wav: {e}")
            
            if vocals_path.exists():
                shutil.move(str(vocals_path), str(final_vocals))
                logger.info(f"Saved vocals: {final_vocals}")
            else:
                error_msg = f"Vocals file not found: {vocals_path}"
                logger.error(error_msg)
                return None, error_msg
            
            if instrumental_path and instrumental_path.exists():
                shutil.move(str(instrumental_path), str(final_other))
                logger.info(f"Saved instrumental as 'other': {final_other}")
            
            if progress_callback:
                progress_callback(100, "MDX separation complete!")
            
            # MDX produces only 2 stems (vocals + instrumental)
            # Don't create fake silent stems - return only what was actually separated
            logger.info("MDX produced 2 stems: vocals + instrumental (as 'other')")
            
            return {
                'vocals': final_vocals,
                'other': final_other  # Instrumental labeled as 'other'
                # drums and bass are None - UI will render only vocals + other
            }, None
            
        except subprocess.TimeoutExpired:
            error_msg = "MDX subprocess timed out (>30 minutes). MDX is very slow on CPU - consider using Demucs instead or enable GPU acceleration."
            logger.error(error_msg)
            return None, error_msg
        except Exception as e:
            error_msg = f"MDX separation failed: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return None, error_msg
    
    def unload_model(self):
        """Unload model to free memory"""
        self._model_loaded = False
        logger.info("MDX model unloaded")
