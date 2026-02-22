"""
Demucs Wrapper - Infrastructure Layer
Wraps Demucs for audio stem separation
"""

from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class DemucsWrapper:
    """
    Infrastructure wrapper for Demucs stem separation.
    Separates audio into: vocals, drums, bass, other
    """
    
    MODEL_NAME = "htdemucs_ft"  # Best quality
    
    def __init__(self, device: Optional[str] = None):
        self._device = device or self._get_default_device()
        self._model = None
        self._sample_rate = 44100
    
    def _get_default_device(self) -> str:
        """Get default compute device"""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except (ImportError, OSError):
            pass
        return "cpu"
    
    @property
    def device(self) -> str:
        return self._device
    
    @property
    def is_loaded(self) -> bool:
        return self._model is not None
    
    def load_model(self) -> Tuple[bool, Optional[str]]:
        """
        Load Demucs model.
        Returns: (success, error_message)
        """
        try:
            from demucs.pretrained import get_model
            
            logger.info(f"Loading Demucs model: {self.MODEL_NAME}")
            self._model = get_model(self.MODEL_NAME)
            self._model.to(self._device)
            self._model.eval()
            
            logger.info(f"Demucs model loaded on {self._device}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to load Demucs model: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def separate(
        self, 
        audio_path: Path,
        output_dir: Path,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[dict], Optional[str]]:
        """
        Separate audio into stems.
        
        Args:
            audio_path: Path to input audio file
            output_dir: Directory to save separated stems
            progress_callback: Optional callback for progress updates
            
        Returns:
            (stems_dict, error_message)
            stems_dict: {vocals: Path, drums: Path, bass: Path, other: Path}
        """
        if not self._model:
            success, error = self.load_model()
            if not success:
                return None, error
        
        try:
            from demucs.apply import apply_model
            import torch
            import torchaudio
            
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Load audio
            logger.info(f"Loading audio: {audio_path}")
            try:
                waveform, sr = torchaudio.load(str(audio_path))
                logger.info(f"Audio loaded: shape={waveform.shape}, sr={sr}")
            except Exception as e:
                logger.error(f"Failed to load audio: {e}")
                raise
            
            # Convert to expected sample rate if needed
            if sr != self._sample_rate:
                logger.info(f"Resampling from {sr} to {self._sample_rate}")
                waveform = torchaudio.functional.resample(waveform, sr, self._sample_rate)
            
            # Convert mono to stereo if needed
            if waveform.shape[0] == 1:
                logger.info("Converting mono to stereo")
                waveform = torch.cat([waveform, waveform], dim=0)
            
            # Move to device
            logger.info(f"Moving waveform to device: {self._device}")
            waveform = waveform.to(self._device)
            
            if progress_callback:
                progress_callback(0.3)
            
            # Apply model
            logger.info("Running stem separation (this may take several minutes)...")
            logger.info(f"Input shape: {waveform.shape}, device: {self._device}")
            
            try:
                with torch.no_grad():
                    logger.info("Calling apply_model...")
                    sources = apply_model(
                        self._model, 
                        waveform.unsqueeze(0),
                        device=self._device,
                        split=True  # Split into chunks for memory efficiency
                    )[0]
                    logger.info(f"Separation complete! Output shape: {sources.shape}")
            except Exception as e:
                logger.error(f"apply_model failed: {e}")
                import traceback
                traceback.print_exc()
                raise
            
            if progress_callback:
                progress_callback(0.7)
            
            # sources order: [drums, bass, other, vocals]
            # Save each stem
            stems = {}
            stem_names = ['drums', 'bass', 'other', 'vocals']
            
            for i, stem_name in enumerate(stem_names):
                stem_wav = sources[i].cpu()
                stem_path = output_dir / f"{stem_name}.wav"
                
                # Delete existing file to avoid conflicts
                if stem_path.exists():
                    try:
                        stem_path.unlink()
                        logger.info(f"Deleted existing {stem_name}.wav")
                    except Exception as e:
                        logger.warning(f"Could not delete existing {stem_name}.wav: {e}")
                
                torchaudio.save(str(stem_path), stem_wav, self._sample_rate)
                stems[stem_name] = stem_path
                logger.info(f"Saved {stem_name}: {stem_path}")
            
            if progress_callback:
                progress_callback(1.0)
            
            logger.info("Stem separation complete")
            return stems, None
            
        except Exception as e:
            error_msg = f"Stem separation failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def unload_model(self):
        """Unload model to free memory"""
        if self._model is not None:
            del self._model
            self._model = None
            
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except (ImportError, OSError):
                pass
            
            logger.info("Demucs model unloaded")
