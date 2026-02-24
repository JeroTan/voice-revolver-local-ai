"""
RVC Wrapper - Infrastructure Layer
Wraps RVC-Project v2 for voice conversion using pre-trained models
"""

import librosa
import soundfile as sf
from pathlib import Path
from typing import Optional, Tuple
import logging
import zipfile
import tempfile
import shutil
import subprocess
import sys

from .venv_utils import get_venv_python

logger = logging.getLogger(__name__)


class RVCWrapper:
    """
    Infrastructure wrapper for RVC (Retrieval-based Voice Conversion).
    Uses pre-trained .pth model and .index file for voice conversion.
    """
    
    def __init__(self, device: Optional[str] = None):
        self._device = device or self._get_default_device()
        self._vc = None
        self._model_path = None
        self._index_path = None
        self._sample_rate = 40000  # RVC default sample rate
        self._f0_method = "rmvpe"  # Pitch extraction method (rmvpe, crepe, harvest, dio)
        self._temp_dir = None
    
    def _get_default_device(self) -> str:
        """Get default compute device"""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except (ImportError, OSError):
            pass  # torch not available or CUDA toolkit missing
        return "cpu"
    
    @property
    def device(self) -> str:
        return self._device
    
    @property
    def is_loaded(self) -> bool:
        return self._model_path is not None
    
    @property
    def sample_rate(self) -> int:
        return self._sample_rate
    
    def load_model_from_zip(self, zip_path: Path) -> Tuple[bool, Optional[str]]:
        """
        Extract and load RVC model from zip file.
        Expected contents: .pth file and .index file
        
        Args:
            zip_path: Path to zip file containing model files
            
        Returns:
            (success, error_message)
        """
        try:
            logger.info(f"Loading RVC model from zip: {zip_path}")
            
            # Create temporary directory for extraction
            self._temp_dir = Path(tempfile.mkdtemp(prefix="rvc_model_"))
            
            # Extract zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self._temp_dir)
            
            # Find .pth and .index files
            pth_files = list(self._temp_dir.glob("*.pth"))
            index_files = list(self._temp_dir.glob("*.index"))
            
            if not pth_files:
                return False, "No .pth model file found in zip"
            
            self._model_path = pth_files[0]
            self._index_path = index_files[0] if index_files else None
            
            logger.info(f"Model ready: {self._model_path.name}")
            if self._index_path:
                logger.info(f"Index ready: {self._index_path.name}")
            else:
                logger.warning("No index file found (optional)")
            
            return True, None
            
        except zipfile.BadZipFile:
            return False, "Invalid zip file format"
        except Exception as e:
            logger.error(f"Error loading RVC model: {e}")
            return False, f"Failed to load model: {str(e)}"
    
    def _load_rvc_model(self) -> Tuple[bool, Optional[str]]:
        """
        Initialize RVC inference module.
        NOTE: Due to fairseq/hydra dataclass bugs with Python 3.11, we use subprocess approach.
        Returns: (success, error_message)
        """
        try:
            # Check if standalone RVC is available (user must install separately)
            # Expected: Standalone RVC-WebUI installation
            import subprocess
            import os
            
            # Check for standalone RVC in common locations
            rvc_paths = [
                r"C:\Program Files\RVC\infer-cli.py",
                r"C:\RVC\infer-cli.py",
                os.path.expanduser(r"~\RVC\infer-cli.py"),
                os.path.expanduser(r"~\Documents\RVC\infer-cli.py"),
            ]
            
            rvc_found = None
            for path in rvc_paths:
                if os.path.exists(path):
                    rvc_found = path
                    break
            
            if not rvc_found:
                error_msg = """RVC not available - Standalone installation required.

Due to Python dependency conflicts (fairseq/hydra bugs with Python 3.11), 
RVC must be installed separately.

To use RVC Model mode:
1. Download RVC-WebUI from: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI
2. Install to C:\\RVC\\ or ~/RVC/
3. Ensure infer-cli.py is accessible

For now, please use Audio File mode with ChatterBox VC - it works great!"""
                return False, error_msg
            
            self._rvc_cli_path = rvc_found
            logger.info(f"RVC CLI found at: {rvc_found}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error initializing RVC: {e}")
            return False, f"Failed to initialize RVC: {str(e)}"
    
    def convert_voice(
        self,
        source_audio_path: Path,
        output_path: Path,
        f0_method: Optional[str] = None,
        f0_up_key: int = 0,
        index_rate: float = 0.75,        # Index influence (0.0-1.0, higher = more accurate timbre)
        filter_radius: int = 3,          # Pitch smoothing (0-7, higher = smoother)
        resample_sr: int = 0,            # Output sample rate (0=auto from model)
        rms_mix_rate: float = 0.25,      # Volume envelope mixing (0.0-1.0)
        protect: float = 0.33,           # Protect voiceless consonants (0.0-0.5)
        progress_callback=None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Convert voice using loaded RVC model via subprocess (avoids fairseq bugs).
        
        Args:
            source_audio_path: Path to source audio (vocals to convert)
            output_path: Path to save converted audio
            f0_method: Pitch extraction method (rmvpe, crepe, harvest, dio)
            f0_up_key: Pitch shift in semitones
            index_rate: Feature retrieval strength (0.0-1.0, default 0.75)
                       Higher = more index influence = better timbre match
            filter_radius: Median filtering for pitch curve (0-7, default 3)
                          Higher = smoother pitch, less vibrato
            resample_sr: Output sample rate in Hz (0=auto, e.g. 40000, 48000)
            rms_mix_rate: Volume envelope mixing (0.0-1.0, default 0.25)
                         0.0=converted only, 1.0=source only, 0.25=75%/25% mix
            protect: Protect voiceless consonants (0.0-0.5, default 0.33)
                    Prevents over-smoothing of "s", "t", "k" sounds
            
        Returns:
            (output_path, error_message)
        """
        if not self.is_loaded:
            return None, "Model not loaded. Call load_model_from_zip() first."
        
        try:
            logger.info(f"Converting voice with RVC (subprocess): {source_audio_path}")
            logger.info(f"Advanced params: index_rate={index_rate}, filter_radius={filter_radius}, "
                       f"resample_sr={resample_sr}, rms_mix_rate={rms_mix_rate}, protect={protect}")
            
            # Use provided f0_method or default
            f0_method = f0_method or self._f0_method
            
            # Path to standalone RVC script
            standalone_script = Path(__file__).parent / "rvc_standalone.py"
            
            # Path to RVC Python executable (dedicated venv-rvc environment)
            # This environment has RVC dependencies with numpy 1.23.5, isolated from main app
            try:
                rvc_python = get_venv_python('venv-rvc')
            except (FileNotFoundError, RuntimeError) as e:
                logger.error(str(e))
                return None, str(e)
            
            # Call RVC via subprocess using dedicated venv-rvc Python with ALL parameters
            import subprocess
            cmd = [
                str(rvc_python),
                str(standalone_script),
                str(self._model_path),
                str(self._index_path) if self._index_path else "",
                str(source_audio_path),
                str(output_path),
                f0_method,
                str(f0_up_key),
                str(index_rate),      # Advanced param 1
                str(filter_radius),   # Advanced param 2
                str(resample_sr),     # Advanced param 3
                str(rms_mix_rate),    # Advanced param 4
                str(protect)          # Advanced param 5
            ]
            
            logger.info(f"Running RVC subprocess: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = f"RVC subprocess failed:\n{result.stderr}"
                logger.error(error_msg)
                return None, error_msg
            
            logger.info(f"RVC subprocess output:\n{result.stdout}")
            
            if not output_path.exists():
                return None, "RVC conversion succeeded but output file not created"
            
            logger.info(f"[SUCCESS] Voice converted successfully: {output_path}")
            return output_path, None
            
        except subprocess.TimeoutExpired:
            return None, "RVC conversion timed out (>5 minutes)"
        except Exception as e:
            logger.error(f"Voice conversion error: {e}")
            import traceback
            traceback.print_exc()
            return None, f"Voice conversion failed: {str(e)}"
    
    def unload_model(self):
        """Unload model and free resources"""
        try:
            self._model_path = None
            self._index_path = None
            
            # Clean up temporary directory
            if self._temp_dir and self._temp_dir.exists():
                shutil.rmtree(self._temp_dir, ignore_errors=True)
                self._temp_dir = None
            
            # Clear CUDA cache if using GPU
            if self._device == "cuda":
                try:
                    import torch
                    torch.cuda.empty_cache()
                except (ImportError, OSError):
                    pass
            
            logger.info("RVC model unloaded")
        except Exception as e:
            logger.warning(f"Error unloading RVC model: {e}")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.unload_model()
