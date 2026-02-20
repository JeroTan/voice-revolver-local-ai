"""
Voice Revolver Core - Domain Layer
Pure business logic with no external dependencies
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional, Any
from pathlib import Path
import uuid
from datetime import datetime
import random
import string


class ProcessingStage(Enum):
    """Processing stages for progress tracking"""
    IDLE = "idle"
    LOADING_MODELS = "loading_models"
    STEM_SEPARATION = "stem_separation"
    VOICE_CONVERSION = "voice_conversion"
    MIXING = "mixing"
    COMPLETE = "complete"
    FAILED = "failed"


class ErrorCode(Enum):
    """Global error codes"""
    STEM_LOAD_FAILED = "STEM_LOAD_FAILED"
    STEM_SEPARATION_FAILED = "STEM_SEPARATION_FAILED"
    VOICE_CONVERT_FAILED = "VOICE_CONVERT_FAILED"
    REFERENCE_TOO_SHORT = "REFERENCE_TOO_SHORT"
    MIX_FAILED = "MIX_FAILED"
    CONVERT_FAILED = "CONVERT_FAILED"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    FILE_WRITE_FAILED = "FILE_WRITE_FAILED"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    GPU_NOT_AVAILABLE = "GPU_NOT_AVAILABLE"
    CANCELLED = "CANCELLED"
    MODEL_DOWNLOAD_FAILED = "MODEL_DOWNLOAD_FAILED"


@dataclass
class AudioStems:
    """Container for separated audio stems"""
    vocals: Optional[Path] = None
    drums: Optional[Path] = None
    bass: Optional[Path] = None
    other: Optional[Path] = None
    
    def get_instrumental(self) -> Dict[str, Path]:
        """Get all non-vocal stems"""
        result = {}
        if self.drums:
            result['drums'] = self.drums
        if self.bass:
            result['bass'] = self.bass
        if self.other:
            result['other'] = self.other
        return result


@dataclass
class VoiceConversionParams:
    """Parameters for voice conversion/transformation"""
    pitch: int = 0  # -12 to +12 semitones
    style: str = "default"  # Voice style: default, american, british, australian, indian
    style_strength: float = 1.0
    tau: float = 0.3  # Voice conversion strength (0.0-1.0): lower=original, higher=reference
    
    # Gender-aware pitch adaptation
    auto_detect_gender: bool = False  # Enable gender alignment (auto-detect for audio, manual for RVC)
    detected_original_gender: Optional[str] = None  # Detected original voice gender (audio mode only)
    detected_reference_gender: Optional[str] = None  # Detected reference voice gender (audio mode only)
    original_gender: Optional[str] = None  # Manual original gender selection for RVC model mode
    model_gender: Optional[str] = None  # Manual model gender selection for RVC model mode
    
    # Adaptive pitch shift thresholds (Hz) - controls shift aggressiveness
    threshold_low: float = 180.0  # Low threshold - aggressive shift below this F0
    threshold_mid: float = 230.0  # Mid threshold - moderate shift
    threshold_high: float = 280.0  # High threshold - conservative shift above this F0


@dataclass
class ProjectData:
    """Project data for .vra files"""
    original_file: Optional[str] = None
    reference_file: Optional[str] = None
    voice_params: VoiceConversionParams = field(default_factory=VoiceConversionParams)
    output_format: str = "mp3"
    processing_state: str = "not_started"
    export_history: list = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class ProgressInfo:
    """Progress information for a task"""
    task_key: str
    stage: ProcessingStage = ProcessingStage.IDLE
    percentage: int = 0
    message: str = ""
    status: str = "pending"  # pending, running, complete, failed, cancelled


def generate_auto_filename(extension: str) -> str:
    """Generate auto filename: date_time_random.extension"""
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H%M%S")
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{date_str}_{time_str}_{random_str}.{extension}"


def generate_task_key() -> str:
    """Generate unique task key for progress tracking"""
    return uuid.uuid4().hex[:12]
