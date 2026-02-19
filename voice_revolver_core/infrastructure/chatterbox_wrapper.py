"""
ChatterBox Wrapper - Infrastructure Layer
Wraps ChatterBox VC for voice conversion
"""

import torch
import torchaudio
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class ChatterBoxWrapper:
    """
    Infrastructure wrapper for ChatterBox voice conversion.
    Converts source vocals to match target voice characteristics.
    """
    
    def __init__(self, device: Optional[str] = None):
        self._device = device or self._get_default_device()
        self._model = None
        self._sample_rate = 24000  # ChatterBox default sample rate
    
    def _get_default_device(self) -> str:
        """Get default compute device"""
        if torch.cuda.is_available():
            return "cuda"
        elif torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    
    @property
    def device(self) -> str:
        return self._device
    
    @property
    def is_loaded(self) -> bool:
        return self._model is not None
    
    @property
    def sample_rate(self) -> int:
        return self._sample_rate
    
    def load_model(self) -> Tuple[bool, Optional[str]]:
        """
        Load ChatterBox VC model.
        Returns: (success, error_message)
        """
        try:
            logger.info("Loading ChatterBox VC model...")
            from chatterbox.vc import ChatterboxVC
            
            logger.info(f"Initializing ChatterBox on device: {self._device}")
            self._model = ChatterboxVC.from_pretrained(device=self._device)
            
            logger.info(f"ChatterBox VC loaded successfully on {self._device}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to load ChatterBox model: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    def convert_voice(
        self,
        source_audio_path: Path,
        target_voice_path: Path,
        output_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Convert source voice to target voice.
        
        Args:
            source_audio_path: Path to source vocal audio
            target_voice_path: Path to reference voice audio
            output_path: Path to save converted audio
            progress_callback: Optional progress callback
            
        Returns:
            (output_path, error_message)
        """
        if not self._model:
            success, error = self.load_model()
            if not success:
                return None, error
        
        try:
            if progress_callback:
                progress_callback(0.2)
            
            logger.info(f"Converting voice: {source_audio_path}")
            logger.info(f"Target voice: {target_voice_path}")
            
            # Convert using ChatterBox VC
            with torch.no_grad():
                wav = self._model.generate(
                    audio=str(source_audio_path),
                    target_voice_path=str(target_voice_path)
                )
            
            if progress_callback:
                progress_callback(0.8)
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(str(output_path), wav, self._sample_rate)
            
            if progress_callback:
                progress_callback(1.0)
            
            logger.info(f"Voice conversion complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"Voice conversion failed: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return None, error_msg
    
    def unload_model(self):
        """Unload model to free memory"""
        if self._model is not None:
            del self._model
            self._model = None
            
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            logger.info("ChatterBox model unloaded")
