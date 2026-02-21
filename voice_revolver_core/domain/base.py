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
    
    # Stem separation model selection
    separation_model: str = "demucs"  # "demucs" or "mdx" - MDX has better vocal isolation
    
    # Phase 2: Spectrum editor curves (optional)
    editing_curves: Optional[Dict[str, Any]] = None  # Contains pitch, reverb, volume curves


@dataclass
class PitchControlPoint:
    """Single control point for pitch automation"""
    time: float  # Seconds into audio
    shift_semitones: float  # Pitch adjustment at this point (-12 to +12)


@dataclass
class PitchCurve:
    """Pitch automation curve for spectrum editor"""
    control_points: list = field(default_factory=list)  # List of PitchControlPoint
    interpolation: str = "cubic"  # "linear", "cubic", or "step"
    
    def has_edits(self) -> bool:
        """Check if curve has any user edits"""
        return len(self.control_points) > 0
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for project save"""
        return {
            "control_points": [
                {"time": pt.time, "shift": pt.shift_semitones}
                for pt in self.control_points
            ],
            "interpolation": self.interpolation
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'PitchCurve':
        """Deserialize from dictionary"""
        curve = PitchCurve(interpolation=data.get("interpolation", "cubic"))
        for pt_data in data.get("control_points", []):
            curve.control_points.append(
                PitchControlPoint(time=pt_data["time"], shift_semitones=pt_data["shift"])
            )
        return curve


@dataclass
class ReverbControlPoint:
    """Single control point for reverb automation"""
    time: float  # Seconds into audio
    wet_percent: float  # Reverb wet mix (0-100%)


@dataclass
class ReverbCurve:
    """Reverb automation curve for spectrum editor"""
    control_points: list = field(default_factory=list)  # List of ReverbControlPoint
    interpolation: str = "linear"
    
    def has_edits(self) -> bool:
        """Check if curve has any user edits"""
        return len(self.control_points) > 0 and any(pt.wet_percent > 0 for pt in self.control_points)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for project save"""
        return {
            "control_points": [
                {"time": pt.time, "wet_percent": pt.wet_percent}
                for pt in self.control_points
            ],
            "interpolation": self.interpolation
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'ReverbCurve':
        """Deserialize from dictionary"""
        curve = ReverbCurve(interpolation=data.get("interpolation", "linear"))
        for pt_data in data.get("control_points", []):
            curve.control_points.append(
                ReverbControlPoint(time=pt_data["time"], wet_percent=pt_data["wet_percent"])
            )
        return curve


@dataclass
class VolumeControlPoint:
    """Single control point for volume automation"""
    time: float  # Seconds into audio
    gain_db: float  # Volume adjustment in dB (-20 to +6)


@dataclass
class VolumeCurve:
    """Volume automation curve for spectrum editor"""
    control_points: list = field(default_factory=list)  # List of VolumeControlPoint
    interpolation: str = "cubic"
    
    def has_edits(self) -> bool:
        """Check if curve has any user edits"""
        return len(self.control_points) > 0 and any(abs(pt.gain_db) > 0.1 for pt in self.control_points)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for project save"""
        return {
            "control_points": [
                {"time": pt.time, "gain_db": pt.gain_db}
                for pt in self.control_points
            ],
            "interpolation": self.interpolation
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'VolumeCurve':
        """Deserialize from dictionary"""
        curve = VolumeCurve(interpolation=data.get("interpolation", "cubic"))
        for pt_data in data.get("control_points", []):
            curve.control_points.append(
                VolumeControlPoint(time=pt_data["time"], gain_db=pt_data["gain_db"])
            )
        return curve


@dataclass
class NoiseControlPoint:
    """Single control point for noise reduction automation"""
    time: float  # Seconds into audio
    reduction_percent: float  # Noise reduction strength (0-100%)


@dataclass
class NoiseCurve:
    """Noise reduction automation curve for spectrum editor"""
    control_points: list = field(default_factory=list)  # List of NoiseControlPoint
    interpolation: str = "linear"
    
    def has_edits(self) -> bool:
        """Check if curve has any user edits"""
        return len(self.control_points) > 0 and any(pt.reduction_percent > 0 for pt in self.control_points)
    
    def to_dict(self) -> dict:
        """Serialize to dictionary for project save"""
        return {
            "control_points": [
                {"time": pt.time, "reduction_percent": pt.reduction_percent}
                for pt in self.control_points
            ],
            "interpolation": self.interpolation
        }
    
    @staticmethod
    def from_dict(data: dict) -> 'NoiseCurve':
        """Deserialize from dictionary"""
        curve = NoiseCurve(interpolation=data.get("interpolation", "linear"))
        for pt_data in data.get("control_points", []):
            curve.control_points.append(
                NoiseControlPoint(time=pt_data["time"], reduction_percent=pt_data["reduction_percent"])
            )
        return curve


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
