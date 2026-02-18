"""
Voice Revolver Core - Domain Layer
Pure business logic with no external dependencies
"""

from .base import (
    ProcessingStage,
    ErrorCode,
    AudioStems,
    VoiceConversionParams,
    ProjectData,
    ProgressInfo,
    generate_auto_filename,
    generate_task_key,
)

from .stem_separator import StemSeparator, StemSeparationResult
from .voice_converter import VoiceConverter, VoiceConversionResult
from .audio_mixer import AudioMixer, MixingResult
from .format_converter import FormatConverter, ConversionResult
from .voice_transformer import VoiceTransformer, TransformResult
from .file_manager import FileManager, FileOperationResult
from .progress_tracker import ProgressTracker

__all__ = [
    # Base
    'ProcessingStage',
    'ErrorCode',
    'AudioStems',
    'VoiceConversionParams',
    'ProjectData',
    'ProgressInfo',
    'generate_auto_filename',
    'generate_task_key',
    
    # Entities
    'StemSeparator',
    'StemSeparationResult',
    'VoiceConverter',
    'VoiceConversionResult',
    'AudioMixer',
    'MixingResult',
    'FormatConverter',
    'ConversionResult',
    'VoiceTransformer',
    'TransformResult',
    'FileManager',
    'FileOperationResult',
    'ProgressTracker',
]
