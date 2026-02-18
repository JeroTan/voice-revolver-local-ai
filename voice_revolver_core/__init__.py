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

from .infrastructure import (
    ComputeController,
    ModelManager,
    FFmpegChecker,
)

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
    
    # Infrastructure
    'ComputeController',
    'ModelManager',
    'FFmpegChecker',
    
    # Version
    '__version__',
]
