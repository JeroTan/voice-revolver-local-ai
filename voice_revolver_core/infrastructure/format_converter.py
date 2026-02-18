"""
Format Converter - Infrastructure Layer
Converts between audio formats using pydub
"""

from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FormatConverter:
    """
    Infrastructure component for audio format conversion.
    Supports: WAV, MP3, FLAC, OGG, AAC
    """
    
    SUPPORTED_FORMATS = {
        'wav': 'wav',
        'mp3': 'mp3',
        'flac': 'flac',
        'ogg': 'ogg',
        'aac': 'aac',
        'm4a': 'aac',
    }
    
    # Bitrate settings
    BITRATE_MAP = {
        'mp3': '320k',
        'aac': '256k',
        'ogg': '192k',
    }
    
    def __init__(self, ffmpeg_dir: Optional[Path] = None):
        """
        Initialize format converter.
        
        Args:
            ffmpeg_dir: Optional path to FFmpeg binary directory
        """
        self._ffmpeg_dir = ffmpeg_dir
    
    def is_format_supported(self, format_ext: str) -> bool:
        """Check if format is supported"""
        return format_ext.lower() in self.SUPPORTED_FORMATS
    
    async def convert(
        self,
        input_path: Path,
        output_path: Path,
        format_ext: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Convert audio file to different format.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save converted audio
            format_ext: Target format extension (mp3, wav, flac, etc.)
            progress_callback: Optional progress callback
                
        Returns:
            (output_path, error_message)
        """
        try:
            from pydub import AudioSegment
            
            # Configure FFmpeg path if provided
            if self._ffmpeg_dir:
                import os
                ffmpeg_path = str(self._ffmpeg_dir / "ffmpeg")
                AudioSegment.converter = ffmpeg_path
                os.environ['FFMPEG_BINARY'] = ffmpeg_path
            
            # Determine format
            target_format = format_ext.lower() if format_ext else output_path.suffix[1:].lower()
            if not target_format:
                target_format = 'wav'
            
            if not self.is_format_supported(target_format):
                return None, f"Unsupported format: {target_format}"
            
            if progress_callback:
                progress_callback(0.1)
            
            # Load audio
            logger.info(f"Loading audio: {input_path}")
            audio = AudioSegment.from_file(str(input_path))
            
            if progress_callback:
                progress_callback(0.3)
            
            # Determine bitrate
            bitrate = self.BITRATE_MAP.get(target_format, None)
            
            # Export
            logger.info(f"Converting to {target_format}: {output_path}")
            
            export_kwargs = {
                'format': self.SUPPORTED_FORMATS[target_format],
            }
            
            if bitrate:
                export_kwargs['bitrate'] = bitrate
            
            # Special handling for WAV
            if target_format == 'wav':
                export_kwargs['codec'] = 'pcm_s16le'
            
            audio.export(str(output_path), **export_kwargs)
            
            if progress_callback:
                progress_callback(1.0)
            
            logger.info(f"Format conversion complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"Format conversion failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    async def convert_to_format(
        self,
        input_path: Path,
        output_dir: Path,
        format_ext: str,
        filename: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Convert audio file to specified format.
        
        Args:
            input_path: Path to input audio file
            output_dir: Directory to save converted file
            format_ext: Target format (mp3, wav, flac, etc.)
            filename: Optional output filename (without extension)
            progress_callback: Optional progress callback
                
        Returns:
            (output_path, error_message)
        """
        # Generate filename if not provided
        if filename is None:
            base_name = input_path.stem
        else:
            base_name = filename
        
        output_path = output_dir / f"{base_name}.{format_ext.lower()}"
        
        return await self.convert(input_path, output_path, format_ext, progress_callback)
    
    async def convert_to_mp3(
        self,
        input_path: Path,
        output_path: Path,
        bitrate: str = '320k',
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Convert to MP3 format"""
        try:
            from pydub import AudioSegment
            
            if self._ffmpeg_dir:
                import os
                ffmpeg_path = str(self._ffmpeg_dir / "ffmpeg")
                AudioSegment.converter = ffmpeg_path
                os.environ['FFMPEG_BINARY'] = ffmpeg_path
            
            audio = AudioSegment.from_file(str(input_path))
            audio.export(str(output_path), format='mp3', bitrate=bitrate)
            
            return output_path, None
            
        except Exception as e:
            return None, str(e)
    
    async def convert_to_wav(
        self,
        input_path: Path,
        output_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """Convert to WAV format"""
        try:
            from pydub import AudioSegment
            
            if self._ffmpeg_dir:
                import os
                ffmpeg_path = str(self._ffmpeg_dir / "ffmpeg")
                AudioSegment.converter = ffmpeg_path
                os.environ['FFMPEG_BINARY'] = ffmpeg_path
            
            audio = AudioSegment.from_file(str(input_path))
            audio.export(str(output_path), format='wav', codec='pcm_s16le')
            
            return output_path, None
            
        except Exception as e:
            return None, str(e)
