"""
Voice Converter - Domain Entity
Uses OpenVoice for voice conversion
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .base import ErrorCode, VoiceConversionParams


@dataclass
class VoiceConversionResult:
    """Result of voice conversion operation"""
    output_path: Optional[Path] = None
    error_code: Optional[ErrorCode] = None
    error_message: str = ""


class VoiceConverter:
    """
    Domain entity for voice conversion.
    Uses reference voice to convert source vocals.
    """
    
    SUPPORTED_INPUT_FORMATS = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
    
    # OpenVoice supported emotions/styles
    SUPPORTED_EMOTIONS = ['neutral', 'sad', 'happy', 'angry', 'surprised', 'fearful']
    
    # Supported languages for OpenVoice V2
    SUPPORTED_LANGUAGES = ['en', 'es', 'fr', 'zh', 'ja', 'kr']
    
    def __init__(self):
        self._model_loaded = False
    
    @property
    def is_ready(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded
    
    def validate_reference(self, reference_path: Path) -> tuple[bool, Optional[ErrorCode]]:
        """Validate reference voice file"""
        if not reference_path.exists():
            return False, ErrorCode.FILE_NOT_FOUND
        
        if reference_path.suffix.lower() not in self.SUPPORTED_INPUT_FORMATS:
            return False, ErrorCode.UNSUPPORTED_FORMAT
        
        return True, None
    
    def validate_voice_params(self, params: VoiceConversionParams) -> tuple[bool, str]:
        """Validate voice transformation parameters"""
        if params.pitch < -12 or params.pitch > 12:
            return False, "Pitch must be between -12 and +12 semitones"
        
        if params.emotion not in self.SUPPORTED_EMOTIONS:
            return False, f"Emotion must be one of: {', '.join(self.SUPPORTED_EMOTIONS)}"
        
        if params.style_strength < 0 or params.style_strength > 2.0:
            return False, "Style strength must be between 0 and 2.0"
        
        return True, ""
    
    def set_model_loaded(self, loaded: bool = True):
        """Mark model as loaded (called by infrastructure)"""
        self._model_loaded = loaded
