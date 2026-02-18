"""
Voice Revolver Core - Infrastructure Layer
External integrations and implementations
"""

from .compute_controller import ComputeController
from .model_manager import ModelManager
from .ffmpeg_checker import FFmpegChecker

__all__ = [
    'ComputeController',
    'ModelManager',
    'FFmpegChecker',
]
