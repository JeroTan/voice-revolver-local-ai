"""
Voice Revolver Core
DDD-based voice replacement engine
"""

from .domain import (
    ProcessingStage,
    ErrorCode,
    AudioStems,
    VoiceConversionParams,
    ProjectData,
    ProgressInfo,
    generate_auto_filename,
    generate_task_key,
    StemSeparator,
    VoiceConverter,
    AudioMixer,
    FormatConverter,
    VoiceTransformer,
    FileManager,
    ProgressTracker,
)

from .application import (
    VoiceReplacementService,
    ProjectService,
)

# Infrastructure imports are done lazily to avoid PyTorch DLL issues
# Import directly from specific modules when needed:
# from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
# from voice_revolver_core.infrastructure.openvoice_wrapper import OpenVoiceWrapper
# from voice_revolver_core.infrastructure.compute_controller import ComputeController
# from voice_revolver_core.infrastructure.model_manager import ModelManager
# from voice_revolver_core.infrastructure.ffmpeg_checker import FFmpegChecker

__version__ = "1.0.0"

__all__ = [
    # Domain
    'ProcessingStage',
    'ErrorCode',
    'AudioStems',
    'VoiceConversionParams',
    'ProjectData',
    'ProgressInfo',
    'generate_auto_filename',
    'generate_task_key',
    'StemSeparator',
    'VoiceConverter',
    'AudioMixer',
    'FormatConverter',
    'VoiceTransformer',
    'FileManager',
    'ProgressTracker',
    
    # Application
    'VoiceReplacementService',
    'ProjectService',
    
    # Version
    '__version__',
]
