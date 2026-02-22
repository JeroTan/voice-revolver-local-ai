"""
ChatterBox TTS Wrapper - Infrastructure Layer
Wraps ChatterBox TTS for text-to-speech generation with dual-engine support
- MTL_TTS: Multi-language support (23+ languages)
- TTSTurbo: English-only, higher quality (optional)
"""

from pathlib import Path
from typing import Optional, Tuple, Dict
import logging
import os
import numpy as np

# Suppress HuggingFace symlinks warning on Windows
os.environ['HF_HUB_DISABLE_SYMLINKS_WARNING'] = '1'

logger = logging.getLogger(__name__)


class ChatterBoxTTSWrapper:
    """
    Infrastructure wrapper for ChatterBox text-to-speech.
    Supports both multi-language (MTL) and English-only turbo modes.
    """
    
    # Language mapping from ChatterBox MTL_TTS
    SUPPORTED_LANGUAGES = {
        "ar": "Arabic",
        "zh": "Chinese",
        "cs": "Czech",
        "da": "Danish",
        "nl": "Dutch",
        "en": "English",
        "fi": "Finnish",
        "fr": "French",
        "de": "German",
        "el": "Greek",
        "hi": "Hindi",
        "hu": "Hungarian",
        "it": "Italian",
        "ja": "Japanese",
        "ko": "Korean",
        "pl": "Polish",
        "pt": "Portuguese",
        "ru": "Russian",
        "es": "Spanish",
        "sv": "Swedish",
        "tr": "Turkish",
        "uk": "Ukrainian",
        "vi": "Vietnamese",
    }
    
    def __init__(self, device: Optional[str] = None):
        self._device = device or self._get_default_device()
        self._mtl_model = None  # Multi-language model
        self._turbo_model = None  # English-only quality model
        self._sample_rate = 24000  # ChatterBox default
    
    def _get_default_device(self) -> str:
        """Get default compute device"""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            elif torch.backends.mps.is_available():
                return "mps"
        except (ImportError, OSError):
            pass
        return "cpu"
    
    @property
    def device(self) -> str:
        return self._device
    
    @property
    def is_loaded(self) -> bool:
        return self._mtl_model is not None or self._turbo_model is not None
    
    @property
    def sample_rate(self) -> int:
        return self._sample_rate
    
    def set_device(self, device: str):
        """
        Update device (will require reloading models).
        
        Args:
            device: Target device (cpu/cuda/mps)
        """
        if device != self._device:
            logger.info(f"Changing device from {self._device} to {device}")
            self._device = device
            # Unload models - will be reloaded on next generate
            self.unload_model()
    
    @staticmethod
    def get_supported_languages() -> Dict[str, str]:
        """Return language code -> display name mapping."""
        return ChatterBoxTTSWrapper.SUPPORTED_LANGUAGES.copy()
    
    def load_model(self, use_turbo: bool = False, hf_token: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Load TTS model (MTL or Turbo).
        
        Args:
            use_turbo: If True, load Turbo model (English only)
            hf_token: HuggingFace token for Turbo model download (required for first-time download)
            
        Returns:
            (success, error_message)
        """
        try:
            if use_turbo:
                # Load Turbo model (English only, supports special tokens like [laugh])
                if self._turbo_model is None:
                    logger.info("Loading ChatterBox Turbo TTS (English with special tokens)...")
                    from chatterbox.tts_turbo import ChatterboxTurboTTS
                    
                    # Set HF_TOKEN environment variable if provided
                    if hf_token:
                        os.environ['HF_TOKEN'] = hf_token
                    
                    logger.info(f"Initializing Turbo TTS on device: {self._device}")
                    self._turbo_model = ChatterboxTurboTTS.from_pretrained(device=self._device)
                    logger.info("ChatterBox Turbo TTS loaded successfully")
            else:
                # Load multi-language model
                if self._mtl_model is None:
                    logger.info("Loading ChatterBox Multi-language TTS...")
                    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
                    
                    logger.info(f"Initializing MTL TTS on device: {self._device}")
                    self._mtl_model = ChatterboxMultilingualTTS.from_pretrained(device=self._device)
                    logger.info("ChatterBox MTL TTS loaded successfully")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to load ChatterBox TTS model: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return False, error_msg
    
    def generate(
        self,
        text: str,
        output_path: Path,
        language: str = "en",
        reference_audio_path: Optional[Path] = None,
        exaggeration: float = 0.7,
        cfg_weight: float = 0.4,
        temperature: float = 0.9,
        use_turbo: bool = False,
        hf_token: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Generate speech from text.
        
        Args:
            text: Input text to synthesize
            output_path: Path to save generated audio
            language: Language code (e.g., "en", "es", "fr")
            reference_audio_path: Optional reference voice audio (must be >5 seconds)
            exaggeration: Energy/emotion (0.0-1.0, MTL only)
            cfg_weight: Classifier-free guidance strength (0.0-1.0, MTL only)
            temperature: Sampling variation (0.1-1.5)
            use_turbo: Use Turbo model for English (higher quality)
            progress_callback: Optional callback(percent, message)
            
        Returns:
            (output_path, error_message)
        """
        try:
            # Validate language
            if language not in self.SUPPORTED_LANGUAGES:
                return None, f"Unsupported language: {language}. Supported: {list(self.SUPPORTED_LANGUAGES.keys())}"
            
            # Force MTL for non-English even if turbo requested
            if use_turbo and language != "en":
                logger.warning(f"Turbo mode only supports English, using MTL for {language}")
                use_turbo = False
            
            # Load appropriate model
            if use_turbo:
                if self._turbo_model is None:
                    success, error = self.load_model(use_turbo=True, hf_token=hf_token)
                    if not success:
                        return None, error
                model = self._turbo_model
                model_name = "Turbo"
            else:
                if self._mtl_model is None:
                    success, error = self.load_model(use_turbo=False, hf_token=hf_token)
                    if not success:
                        return None, error
                model = self._mtl_model
                model_name = "MTL"
            
            if progress_callback:
                progress_callback(10, f"Initializing {model_name} TTS...")
            
            # Validate and normalize reference audio if provided
            if reference_audio_path:
                if not reference_audio_path.exists():
                    return None, f"Reference audio not found: {reference_audio_path}"
                
                # Check duration and normalize audio (ChatterBox requires >5 seconds)
                import librosa
                try:
                    y, sr = librosa.load(str(reference_audio_path), sr=None, duration=6.0)
                    duration = len(y) / sr
                    if duration < 5.0:
                        return None, f"Reference audio must be at least 5 seconds long (got {duration:.1f}s)"
                    
                    # Normalize audio if values are outside [-1, 1] range
                    max_abs = np.abs(y).max()
                    if max_abs > 1.0:
                        logger.warning(f"Audio values outside normalized range: max={max_abs:.4f}, normalizing...")
                        y = y / max_abs
                        # Save normalized version temporarily
                        import soundfile as sf
                        temp_normalized = reference_audio_path.parent / f"normalized_{reference_audio_path.name}"
                        sf.write(str(temp_normalized), y, sr)
                        reference_audio_path = temp_normalized
                        logger.info(f"Reference audio normalized and saved to: {temp_normalized.name}")
                        
                except Exception as e:
                    return None, f"Failed to load reference audio: {e}"
            
            if progress_callback:
                progress_callback(20, f"Generating speech with {model_name}...")
            
            logger.info(f"Generating speech with {model_name} model")
            logger.info(f"Text: {text[:50]}{'...' if len(text) > 50 else ''}")
            logger.info(f"Language: {language} ({self.SUPPORTED_LANGUAGES[language]})")
            if reference_audio_path:
                logger.info(f"Reference voice: {reference_audio_path.name}")
            
            import torch
            
            # Generate speech
            with torch.no_grad():
                if use_turbo:
                    # ChatterboxTurboTTS model (English only, supports special tokens like [laugh])
                    # Note: exaggeration and cfg_weight are not used by Turbo model
                    wav = model.generate(
                        text=text,
                        audio_prompt_path=str(reference_audio_path) if reference_audio_path else None,
                        temperature=temperature,
                        top_p=0.95,
                        repetition_penalty=1.2,
                        norm_loudness=True  # Turbo model supports loudness normalization
                    )
                else:
                    # MTL model (multi-language)
                    wav = model.generate(
                        text=text,
                        language_id=language,
                        audio_prompt_path=str(reference_audio_path) if reference_audio_path else None,
                        exaggeration=exaggeration,
                        cfg_weight=cfg_weight,
                        temperature=temperature,
                        repetition_penalty=2.0,
                        min_p=0.05,
                        top_p=1.0
                    )
            
            if progress_callback:
                progress_callback(80, "Saving audio...")
            
            # Save output
            import torchaudio
            output_path.parent.mkdir(parents=True, exist_ok=True)
            torchaudio.save(str(output_path), wav, self._sample_rate)
            
            if progress_callback:
                progress_callback(100, "Generation complete!")
            
            logger.info(f"TTS generation complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"TTS generation failed: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            return None, error_msg
    
    def unload_model(self):
        """Unload models to free memory"""
        if self._mtl_model is not None:
            del self._mtl_model
            self._mtl_model = None
            logger.info("ChatterBox MTL TTS unloaded")
        
        if self._turbo_model is not None:
            del self._turbo_model
            self._turbo_model = None
            logger.info("ChatterBox Turbo TTS unloaded")
        
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except (ImportError, OSError):
            pass
