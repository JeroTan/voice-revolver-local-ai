"""
Audio Mixer - Infrastructure Layer
Combines converted vocals with instrumental stems using pydub
"""

from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class AudioMixer:
    """
    Infrastructure component for audio mixing.
    Combines converted vocals with instrumental stems.
    """
    
    def __init__(self, ffmpeg_dir: Optional[Path] = None):
        """
        Initialize audio mixer.
        
        Args:
            ffmpeg_dir: Optional path to FFmpeg binary directory
        """
        self._ffmpeg_dir = ffmpeg_dir
        self._vocals_volume = 1.0
        self._instrumental_volume = 1.0
        self._normalize = True
    
    def set_volumes(self, vocals: float = 1.0, instrumental: float = 1.0):
        """Set mixing volumes"""
        self._vocals_volume = max(0.0, min(2.0, vocals))
        self._instrumental_volume = max(0.0, min(2.0, instrumental))
    
    def set_normalize(self, normalize: bool):
        """Enable/disable loudness normalization"""
        self._normalize = normalize
    
    def mix(
        self,
        vocals_path: Path,
        instrumental_paths: dict,
        output_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Mix vocals with instrumental stems.
        
        Args:
            vocals_path: Path to vocals audio file
            instrumental_paths: Dict of {stem_name: path} e.g., {'drums': Path, 'bass': Path, 'other': Path}
            output_path: Path to save mixed output
            progress_callback: Optional progress callback
            
        Returns:
            (output_path, error_message)
        """
        try:
            from pydub import AudioSegment
            from pydub.effects import normalize
            
            # Configure FFmpeg path if provided
            if self._ffmpeg_dir:
                import os
                ffmpeg_path = str(self._ffmpeg_dir / "ffmpeg")
                ffmpeg_probe_path = str(self._ffmpeg_dir / "ffprobe")
                
                AudioSegment.converter = ffmpeg_path
                # pydub uses ffprobe internally
                os.environ['FFMPEG_BINARY'] = ffmpeg_path
                os.environ['FFPROBE_BINARY'] = ffmpeg_probe_path
            
            if progress_callback:
                progress_callback(0.1)
            
            # Load vocals
            logger.info(f"Loading vocals: {vocals_path}")
            vocals = AudioSegment.from_file(str(vocals_path))
            vocals = vocals.apply_gain_volume(self._vocals_volume)
            
            if progress_callback:
                progress_callback(0.3)
            
            # Load and mix instrumental stems
            instrumental = None
            total_stems = len(instrumental_paths)
            
            for i, (stem_name, stem_path) in enumerate(instrumental_paths.items()):
                if stem_path and stem_path.exists():
                    logger.info(f"Loading {stem_name}: {stem_path}")
                    stem_audio = AudioSegment.from_file(str(stem_path))
                    stem_audio = stem_audio.apply_gain_volume(self._instrumental_volume)
                    
                    # Match length to vocals if needed
                    if len(stem_audio) < len(vocals):
                        stem_audio = stem_audio + AudioSegment.silent(duration=len(vocals) - len(stem_audio))
                    elif len(stem_audio) > len(vocals):
                        stem_audio = stem_audio[:len(vocals)]
                    
                    if instrumental is None:
                        instrumental = stem_audio
                    else:
                        # Overlay stems
                        instrumental = instrumental.overlay(stem_audio)
                    
                    if progress_callback:
                        progress_callback(0.3 + (0.3 * (i + 1) / total_stems))
            
            if instrumental is None:
                return None, "No instrumental stems provided"
            
            # Normalize if enabled
            if self._normalize:
                logger.info("Normalizing audio...")
                instrumental = normalize(instrumental)
            
            # Mix vocals with instrumental
            logger.info("Mixing vocals with instrumental...")
            final_mix = instrumental.overlay(vocals)
            
            if progress_callback:
                progress_callback(0.8)
            
            # Export
            logger.info(f"Exporting mixed audio: {output_path}")
            final_mix.export(
                str(output_path),
                format=output_path.suffix[1:],  # Remove leading dot
                bitrate="320k"
            )
            
            if progress_callback:
                progress_callback(1.0)
            
            logger.info(f"Audio mixing complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"Audio mixing failed: {str(e)}"
            logger.error(error_msg)
            return None, error_msg
    
    def mix_simple(
        self,
        vocals_path: Path,
        drums_path: Optional[Path],
        bass_path: Optional[Path],
        other_path: Optional[Path],
        output_path: Path,
        progress_callback: Optional[callable] = None
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Simple mix with individual stem paths.
        
        Args:
            vocals_path: Path to vocals
            drums_path: Path to drums (optional)
            bass_path: Path to bass (optional)
            other_path: Path to other (optional)
            output_path: Path to save output
            progress_callback: Optional progress callback
            
        Returns:
            (output_path, error_message)
        """
        instrumental_paths = {}
        
        if drums_path and drums_path.exists():
            instrumental_paths['drums'] = drums_path
        if bass_path and bass_path.exists():
            instrumental_paths['bass'] = bass_path
        if other_path and other_path.exists():
            instrumental_paths['other'] = other_path
        
        return self.mix(vocals_path, instrumental_paths, output_path, progress_callback)
