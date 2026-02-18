"""
Format Converter - Domain Entity
Converts between audio formats using pydub
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .base import ErrorCode


@dataclass
class ConversionResult:
    """Result of format conversion"""
    output_path: Optional[Path] = None
    error_code: Optional[ErrorCode] = None
    error_message: str = ""


class FormatConverter:
    """
    Domain entity for format conversion.
    Supports conversion between various audio formats.
    """
    
    SUPPORTED_FORMATS = {
        '.mp3': 'mp3',
        '.wav': 'wav',
        '.flac': 'flac',
        '.ogg': 'ogg',
        '.m4a': 'm4a',
        '.aac': 'aac'
    }
    
    FORMAT_BITRATES = {
        'mp3': 320,  # kbps
    }
    
    def __init__(self):
        pass
    
    def validate_format(self, format_ext: str) -> bool:
        """Check if format is supported"""
        return format_ext.lower() in self.SUPPORTED_FORMATS
    
    def get_export_params(self, format_ext: str) -> dict:
        """Get export parameters for format"""
        format_ext = format_ext.lower().lstrip('.')
        
        params = {'format': format_ext}
        
        if format_ext == 'mp3':
            params['bitrate'] = f"{self.FORMAT_BITRATES['mp3']}k"
        
        return params
    
    def get_output_extension(self, format_name: str) -> str:
        """Get file extension for format name"""
        return f".{format_name}"
    
    def is_lossless(self, format_ext: str) -> bool:
        """Check if format is lossless"""
        return format_ext.lower() in ['.wav', '.flac']
