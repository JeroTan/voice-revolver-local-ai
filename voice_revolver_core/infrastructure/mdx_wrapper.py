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
            project_root = Path(__file__).parent.parent.parent
            mdx_python = project_root / "venv-mdx" / "Scripts" / "python.exe"
            
            if not mdx_python.exists():
                error_msg = (
                    "venv-mdx environment not found. To use MDX:\n"
                    "  python -m venv venv-mdx\n"
                    "  .\\venv-mdx\\Scripts\\Activate.ps1\n"
                    "  pip install audio-separator[cpu]\n"
                    "\nOr select 'demucs' for stem separation."
                )
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
            project_root = Path(__file__).parent.parent.parent
            mdx_python = project_root / "venv-mdx" / "Scripts" / "python.exe"
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
                timeout=1800  # 30 minutes max (MDX is slow on CPU)
            )
            
            # Log subprocess output
            if result.stderr:
                for line in result.stderr.strip().split('\n'):
                    if line:
                        logger.info(f"MDX: {line}")
            
            if result.returncode != 0:
                error_msg = f"MDX subprocess failed with code {result.returncode}"
                if result.stderr:
                    error_msg += f"\n{result.stderr}"
                logger.error(error_msg)
                return None, error_msg
            
            # Handle timeout
            if "timed out" in result.stderr.lower():
                logger.error("MDX processing is very slow on CPU. Consider using Demucs or GPU acceleration.")
            
            # Parse JSON result
            result_data = json.loads(result.stdout.strip())
            
            if not result_data.get("success"):
                error_msg = result_data.get("error", "Unknown error")
                logger.error(f"MDX separation failed: {error_msg}")
                return None, error_msg
            
            if progress_callback:
                progress_callback(70, "Processing stems...")
            
            # Get vocals and instrumental paths
            vocals_path = Path(result_data["vocals_path"])
            instrumental_path = Path(result_data.get("instrumental_path", ""))
            
            # Rename to standard format (using generic names)
            final_vocals = output_dir / "vocals.wav"
            final_other = output_dir / "other.wav"
            
            if vocals_path.exists():
                shutil.move(str(vocals_path), str(final_vocals))
                logger.info(f"Saved vocals: {final_vocals}")
            
            if instrumental_path.exists():
                shutil.move(str(instrumental_path), str(final_other))
                logger.info(f"Saved instrumental as 'other': {final_other}")
            
            if progress_callback:
                progress_callback(85, "Creating placeholder stems...")
            
            # Create silent placeholders for drums/bass (MDX only does vocals/instrumental)
            import soundfile as sf
            import numpy as np
            
            # Load vocals to get duration and sample rate
            vocals_audio, sr = sf.read(str(final_vocals))
            silence = np.zeros_like(vocals_audio)
            
            final_drums = output_dir / "drums.wav"
            final_bass = output_dir / "bass.wav"
            
            sf.write(str(final_drums), silence, sr)
            sf.write(str(final_bass), silence, sr)
            
            logger.info("Created placeholder drums and bass (silent)")
            
            if progress_callback:
                progress_callback(100, "MDX separation complete!")
            
            return {
                'vocals': final_vocals,
                'drums': final_drums,
                'bass': final_bass,
                'other': final_other
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
