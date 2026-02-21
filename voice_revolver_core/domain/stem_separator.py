"""
Stem Separator - Domain Entity
Uses Demucs for audio stem separation
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .base import AudioStems, ErrorCode


@dataclass
class StemSeparationResult:
    """Result of stem separation operation"""
    stems: Optional[AudioStems] = None
    error_code: Optional[ErrorCode] = None
    error_message: str = ""


class StemSeparator:
    """
    Domain entity for stem separation.
    Pure business logic - actual implementation in infrastructure.
    """
    
    SUPPORTED_INPUT_FORMATS = ['.mp3', '.wav', '.flac', '.ogg', '.m4a']
    OUTPUT_STEMS = ['vocals', 'drums', 'bass', 'other']
    
    def __init__(self):
        self._model_loaded = False
    
    @property
    def is_ready(self) -> bool:
        """Check if model is loaded"""
        return self._model_loaded
    
    def validate_input(self, audio_path: Path) -> tuple[bool, Optional[ErrorCode]]:
        """Validate input file"""
        if not audio_path.exists():
            return False, ErrorCode.FILE_NOT_FOUND
        
        if audio_path.suffix.lower() not in self.SUPPORTED_INPUT_FORMATS:
            return False, ErrorCode.UNSUPPORTED_FORMAT
        
        return True, None
    
    def get_required_output_names(self, base_name: str) -> dict:
        """Get expected output file names (using generic names)"""
        return {
            'vocals': "vocals.wav",
            'drums': "drums.wav",
            'bass': "bass.wav",
            'other': "other.wav"
        }
    
    def set_model_loaded(self, loaded: bool = True):
        """Mark model as loaded (called by infrastructure)"""
        self._model_loaded = loaded
