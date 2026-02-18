"""
Audio Mixer - Domain Entity
Combines converted vocals with instrumental stems
"""

from pathlib import Path
from typing import Optional, Dict
from dataclasses import dataclass

from .base import AudioStems, ErrorCode


@dataclass
class MixingResult:
    """Result of audio mixing operation"""
    output_path: Optional[Path] = None
    error_code: Optional[ErrorCode] = None
    error_message: str = ""


class AudioMixer:
    """
    Domain entity for audio mixing.
    Combines vocals with instrumental stems.
    """
    
    def __init__(self):
        self._default_volume_vocals = 1.0
        self._default_volume_instrumental = 1.0
    
    def validate_stems(self, stems: AudioStems) -> tuple[bool, Optional[ErrorCode]]:
        """Validate that we have required stems"""
        if not stems.vocals:
            return False, ErrorCode.FILE_NOT_FOUND
        
        # Need at least one instrumental stem
        if not (stems.drums or stems.bass or stems.other):
            return False, ErrorCode.MIX_FAILED
        
        return True, None
    
    def get_mixing_config(self) -> dict:
        """Get default mixing configuration"""
        return {
            'vocals_volume': self._default_volume_vocals,
            'instrumental_volume': self._default_volume_instrumental,
            'normalize': True,
            'fade_in': 0.0,
            'fade_out': 0.0
        }
    
    def set_mixing_config(self, vocals_volume: float = 1.0, instrumental_volume: float = 1.0):
        """Set custom mixing configuration"""
        self._default_volume_vocals = vocals_volume
        self._default_volume_instrumental = instrumental_volume
