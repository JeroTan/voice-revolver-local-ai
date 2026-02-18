"""
Voice Replacement Service - Application Layer
Orchestrates the full vocal replacement workflow
"""

from pathlib import Path
from typing import Optional, Callable
import asyncio

from ..domain import (
    ProgressTracker,
    ProgressInfo,
    ProcessingStage,
    ErrorCode,
    AudioStems,
    VoiceConversionParams,
    generate_task_key,
)


class VoiceReplacementService:
    """
    Application service that orchestrates the full vocal replacement pipeline.
    Coordinates: StemSeparator → VoiceConverter → VoiceTransformer → AudioMixer
    """
    
    def __init__(
        self,
        stem_separator,      # Infrastructure: Demucs wrapper
        voice_converter,     # Infrastructure: OpenVoice wrapper
        voice_transformer,   # Infrastructure: Pitch/Emotion wrapper
        audio_mixer,        # Infrastructure: Audio mixing wrapper
        file_manager,        # Domain: File management
        progress_tracker: ProgressTracker,
    ):
        self._stem_separator = stem_separator
        self._voice_converter = voice_converter
        self._voice_transformer = voice_transformer
        self._audio_mixer = audio_mixer
        self._file_manager = file_manager
        self._progress_tracker = progress_tracker
        
        self._active_task_key: Optional[str] = None
    
    async def process(
        self,
        original_audio_path: Path,
        reference_voice_path: Path,
        voice_params: VoiceConversionParams,
        output_format: str = "mp3",
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> tuple[Optional[Path], Optional[ErrorCode], str]:
        """
        Execute full vocal replacement pipeline.
        
        Returns: (output_path, error_code, error_message)
        """
        # Start progress tracking
        self._active_task_key = self._progress_tracker.start_task("voice_replacement")
        
        try:
            # Stage 1: Load models
            self._update_progress(
                ProcessingStage.LOADING_MODELS, 
                5, 
                "Loading AI models..."
            )
            await self._load_models()
            
            # Stage 2: Stem separation
            self._update_progress(
                ProcessingStage.STEM_SEPARATION,
                15,
                "Separating audio stems..."
            )
            stems, err = await self._separate_stems(original_audio_path)
            if err:
                return None, err, "Stem separation failed"
            
            # Stage 3: Voice conversion
            self._update_progress(
                ProcessingStage.VOICE_CONVERSION,
                40,
                "Converting voice..."
            )
            converted_vocals, err = await self._convert_voice(
                stems.vocals, 
                reference_voice_path,
                voice_params
            )
            if err:
                return None, err, "Voice conversion failed"
            
            # Stage 4: Audio mixing
            self._update_progress(
                ProcessingStage.MIXING,
                75,
                "Mixing audio..."
            )
            final_output, err = await self._mix_audio(converted_vocals, stems)
            if err:
                return None, err, "Audio mixing failed"
            
            # Complete
            self._update_progress(
                ProcessingStage.COMPLETE,
                100,
                "Processing complete!"
            )
            self._progress_tracker.complete_task(self._active_task_key, True)
            
            return final_output, None, "Success"
            
        except Exception as e:
            self._progress_tracker.complete_task(self._active_task_key, False)
            return None, ErrorCode.VOICE_CONVERT_FAILED, str(e)
        
        finally:
            self._active_task_key = None
    
    def cancel(self):
        """Cancel current processing"""
        if self._active_task_key:
            self._progress_tracker.cancel_task(self._active_task_key)
    
    def _update_progress(self, stage: ProcessingStage, percentage: int, message: str):
        """Update progress and notify callback"""
        if self._active_task_key:
            self._progress_tracker.update_progress(
                self._active_task_key,
                stage,
                percentage,
                message
            )
    
    async def _load_models(self):
        """Load AI models"""
        # Infrastructure handles actual model loading
        await asyncio.sleep(0.5)  # Simulated - actual impl would call infrastructure
    
    async def _separate_stems(self, audio_path: Path) -> tuple[Optional[AudioStems], Optional[ErrorCode]]:
        """Separate audio into stems"""
        # Infrastructure handles actual separation
        return None, None  # Placeholder
    
    async def _convert_voice(
        self, 
        vocal_path: Path, 
        reference_path: Path,
        params: VoiceConversionParams
    ) -> tuple[Optional[Path], Optional[ErrorCode]]:
        """Convert voice"""
        # Infrastructure handles actual conversion
        return None, None  # Placeholder
    
    async def _mix_audio(
        self, 
        converted_vocals: Path, 
        stems: AudioStems
    ) -> tuple[Optional[Path], Optional[ErrorCode]]:
        """Mix audio"""
        # Infrastructure handles actual mixing
        return None, None  # Placeholder
