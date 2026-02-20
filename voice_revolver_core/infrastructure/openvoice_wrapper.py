"""
OpenVoice Wrapper - Infrastructure Layer
Wraps OpenVoice V2 for voice conversion
"""

import numpy as np
import librosa
from pathlib import Path
from typing import Optional, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class OpenVoiceWrapper:
    """
    Infrastructure wrapper for OpenVoice V2 voice conversion.
    Converts source voice to sound like reference voice.
    Supports accent-based style variations.
    """
    
    # OpenVoice V2 supported styles (accent variants)
    SUPPORTED_STYLES = {
        'default': 'en-default.pth',
        'american': 'en-us.pth',
        'british': 'en-br.pth',
        'australian': 'en-au.pth',
        'indian': 'en-india.pth',
    }
    
    def __init__(self, checkpoints_path: Path, device: Optional[str] = None):
        self._checkpoints_path = checkpoints_path
        self._device = device or self._get_default_device()
        self._converter = None
        self._base_speaker_se = None  # Source speaker embedding
        self._sample_rate = 22050
        self._loaded_style_embeddings = {}  # Cache loaded embeddings
    
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
        return self._converter is not None
    
    def load_model(self) -> Tuple[bool, Optional[str]]:
        """
        Load OpenVoice V2 converter model.
        Returns: (success, error_message)
        """
        try:
            logger.info("OpenVoice load_model: Importing ToneColorConverter...")
            from openvoice.api import ToneColorConverter
            logger.info("OpenVoice load_model: Import successful")
            
            config_path = self._checkpoints_path / "converter" / "config.json"
            checkpoint_path = self._checkpoints_path / "converter" / "checkpoint.pth"
            
            logger.info(f"OpenVoice load_model: Checking paths...")
            logger.info(f"  config_path: {config_path}")
            logger.info(f"  checkpoint_path: {checkpoint_path}")
            
            if not config_path.exists():
                return False, f"Config not found: {config_path}"
            if not checkpoint_path.exists():
                return False, f"Checkpoint not found: {checkpoint_path}"
            
            logger.info(f"OpenVoice load_model: Creating ToneColorConverter on device={self._device}...")
            self._converter = ToneColorConverter(
                str(config_path),
                device=self._device
            )
            logger.info("OpenVoice load_model: ToneColorConverter created, loading checkpoint...")
            self._converter.load_ckpt(str(checkpoint_path))
            
            # Disable watermark for better audio quality
            if hasattr(self._converter, 'watermark_model'):
                self._converter.watermark_model = None
                logger.info("Watermark disabled for better quality")
            
            logger.info(f"OpenVoice V2 loaded on {self._device}")
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to load OpenVoice model: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    def extract_speaker_embedding(
        self, 
        audio_path: Path
    ) -> Tuple[Optional[Any], Optional[str]]:
        """
        Extract speaker embedding from reference audio.
        
        Args:
            audio_path: Path to reference audio file
            
        Returns:
            (speaker_embedding, error_message)
        """
        if not self._converter:
            success, error = self.load_model()
            if not success:
                return None, error
        
        try:
            from openvoice import se_extractor
            
            logger.info(f"Extracting speaker embedding from: {audio_path}")
            
            # Extract speaker embedding
            se, _ = se_extractor.get_se(
                str(audio_path),
                self._converter,
                vad=True
            )
            
            logger.info("Speaker embedding extracted successfully")
            return se, None
            
        except Exception as e:
            error_msg = f"Failed to extract speaker embedding: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def _load_style_embedding(self, style: str) -> Tuple[Optional[Any], Optional[str]]:
        """
        Load source speaker embedding for the specified style.
        
        Args:
            style: Style name from SUPPORTED_STYLES
            
        Returns:
            (embedding, error_message)
        """
        # Check if style is supported
        if style not in self.SUPPORTED_STYLES:
            return None, f"Unsupported style '{style}'. Choose from: {', '.join(self.SUPPORTED_STYLES.keys())}"
        
        # Check cache
        if style in self._loaded_style_embeddings:
            logger.info(f"Using cached embedding for style: {style}")
            return self._loaded_style_embeddings[style], None
        
        # Load embedding file
        embedding_file = self.SUPPORTED_STYLES[style]
        embedding_path = self._checkpoints_path / "base_speakers" / "ses" / embedding_file
        
        if not embedding_path.exists():
            return None, f"Style embedding not found: {embedding_path}"
        
        try:
            logger.info(f"Loading style embedding: {style} from {embedding_file}")
            import torch
            embedding = torch.load(embedding_path).to(self._device)
            
            # Cache for future use
            self._loaded_style_embeddings[style] = embedding
            
            return embedding, None
            
        except Exception as e:
            return None, f"Failed to load style embedding: {str(e)}"
    
    def convert_voice(
        self,
        source_audio_path: Path,
        target_se: Any,
        output_path: Path,
        tau: float = 0.3,
        style: str = 'default',
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Convert source voice to target voice with style control.
        
        Args:
            source_audio_path: Path to source vocal audio
            target_se: Target speaker embedding (from reference)
            output_path: Path to save converted audio
            tau: Voice conversion strength (0-1)
            style: Voice style/accent ('default', 'american', 'british', 'australian', 'indian')
            progress_callback: Optional progress callback
            
        Returns:
            (output_path, error_message)
        """
        if not self._converter:
            success, error = self.load_model()
            if not success:
                return None, error
        
        try:
            import soundfile as sf
            import torch
            
            if progress_callback:
                progress_callback(0.2)
            
            # Load source audio
            logger.info(f"Loading source audio: {source_audio_path}")
            audio, sr = librosa.load(str(source_audio_path), sr=self._sample_rate)
            
            if progress_callback:
                progress_callback(0.4)
            
            # Convert using ToneColorConverter
            logger.info(f"Converting voice with style: {style}")
            
            # Load style-specific source embedding
            src_se, error = self._load_style_embedding(style)
            if error:
                # Fallback to default if style loading fails
                logger.warning(f"Style loading failed: {error}. Using default.")
                src_se, error = self._load_style_embedding('default')
                if error:
                    # Last resort: use target embedding
                    logger.warning("Default embedding also failed. Using target embedding as source.")
                    src_se = target_se
            
            # Convert
            with torch.no_grad():
                audio_tensor = torch.tensor(audio).float().unsqueeze(0).to(self._device)
                
                # The converter expects specific input format
                converted = self._converter.convert(
                    audio_src_path=str(source_audio_path),
                    src_se=src_se,
                    tgt_se=target_se,
                    tau=tau,
                    message="@MyShell"
                )
            
            if progress_callback:
                progress_callback(0.8)
            
            # Save output
            if isinstance(converted, np.ndarray):
                output_audio = converted
            else:
                output_audio = converted.cpu().float().numpy()
            
            # Ensure correct shape
            if output_audio.ndim > 1:
                output_audio = output_audio.squeeze()
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            sf.write(str(output_path), output_audio, self._sample_rate)
            
            if progress_callback:
                progress_callback(1.0)
            
            logger.info(f"Voice conversion complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"Voice conversion failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def convert_voice_simple(
        self,
        source_audio_path: Path,
        reference_audio_path: Path,
        output_path: Path,
        tau: float = 0.3,
        style: str = 'default',
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Simple voice conversion: source + reference -> converted output.
        Convenience method that handles embedding extraction automatically.
        
        Args:
            source_audio_path: Path to source vocal audio
            reference_audio_path: Path to reference voice audio
            output_path: Path to save converted audio
            tau: Voice conversion strength
            style: Voice style/accent to apply
            progress_callback: Optional progress callback
            
        Returns:
            (output_path, error_message)
        """
        # Extract target speaker embedding from reference
        target_se, error = self.extract_speaker_embedding(reference_audio_path)
        if error:
            return None, error
        
        # Convert voice with style
        return self.convert_voice(
            source_audio_path,
            target_se,
            output_path,
            tau,
            style,
            progress_callback
        )
    
    def unload_model(self):
        """Unload model to free memory"""
        if self._converter is not None:
            del self._converter
            self._converter = None
            
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except (ImportError, OSError):
                pass
            
            logger.info("OpenVoice model unloaded")
