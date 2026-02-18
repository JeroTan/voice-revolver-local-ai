"""
Voice Transformer - Domain Entity
Applies pitch and emotion transformations
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .base import ErrorCode, VoiceConversionParams


@dataclass
class TransformResult:
    """Result of voice transformation"""
    output_path: Optional[Path] = None
    error_code: Optional[ErrorCode] = None
    error_message: str = ""


class VoiceTransformer:
    """
    Domain entity for voice transformation.
    Applies pitch shift and emotion/style control.
    """
    
    PITCH_MIN = -12  # semitones
    PITCH_MAX = 12   # semitones
    
    STYLE_STRENGTH_MIN = 0.0
    STYLE_STRENGTH_MAX = 2.0
    
    def __init__(self):
        self._enabled = True
    
    @property
    def is_enabled(self) -> bool:
        """Check if transformation is enabled"""
        return self._enabled
    
    def validate_params(self, params: VoiceConversionParams) -> tuple[bool, Optional[ErrorCode]]:
        """Validate transformation parameters"""
        if params.pitch < self.PITCH_MIN or params.pitch > self.PITCH_MAX:
            return False, ErrorCode.CONVERT_FAILED
        
        if params.style_strength < self.STYLE_STRENGTH_MIN or params.style_strength > self.STYLE_STRENGTH_MAX:
            return False, ErrorCode.CONVERT_FAILED
        
        return True, None
    
    def is_transformation_needed(self, params: VoiceConversionParams) -> bool:
        """Check if any transformation is actually needed"""
        return params.pitch != 0 or params.emotion != "neutral" or params.style_strength != 1.0
    
    def set_enabled(self, enabled: bool):
        """Enable or disable transformation"""
        self._enabled = enabled
