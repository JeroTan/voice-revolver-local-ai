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

# Infrastructure imports are done lazily to avoid PyTorch DLL issues
# Import directly from specific modules when needed:
# from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
# from voice_revolver_core.infrastructure.openvoice_wrapper import OpenVoiceWrapper
# from voice_revolver_core.infrastructure.compute_controller import ComputeController
# from voice_revolver_core.infrastructure.model_manager import ModelManager
# from voice_revolver_core.infrastructure.ffmpeg_checker import FFmpegChecker

__version__ = "1.0.0"


def __getattr__(name):
    """Lazy application exports avoid loading optional audio DLLs at package import."""
    if name == "VoiceReplacementService":
        from .application.voice_replacement_service import VoiceReplacementService
        return VoiceReplacementService
    if name == "ProjectService":
        from .application.project_service import ProjectService
        return ProjectService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

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
