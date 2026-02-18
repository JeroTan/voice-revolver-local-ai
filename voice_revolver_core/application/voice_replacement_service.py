"""
Voice Replacement Service - Application Layer
Orchestrates the full vocal replacement workflow
"""

from pathlib import Path
from typing import Optional, Callable
import asyncio
import logging

from ..domain import (
    ProgressTracker,
    ProgressInfo,
    ProcessingStage,
    ErrorCode,
    AudioStems,
    VoiceConversionParams,
    generate_task_key,
)

logger = logging.getLogger(__name__)


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
        self._progress_callback: Optional[Callable] = None
    
    def process(
        self,
        original_audio_path: Path,
        reference_voice_path: Path,
        voice_params: VoiceConversionParams,
        output_format: str = "mp3",
        output_dir: Optional[Path] = None,
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> tuple[Optional[Path], Optional[ErrorCode], str]:
        """
        Execute full vocal replacement pipeline.
        
        Args:
            original_audio_path: Path to original song
            reference_voice_path: Path to reference voice audio
            voice_params: Voice conversion parameters
            output_format: Output format (mp3, wav, flac)
            output_dir: Output directory (defaults to temp)
            progress_callback: Progress callback
            
        Returns:
            (output_path, error_code, error_message)
        """
        logger.info(f"process() called with original={original_audio_path}, reference={reference_voice_path}")
        
        if output_dir is None:
            output_dir = self._file_manager.temp_dir
        
        logger.info(f"Output directory: {output_dir}")
        
        # Ensure temp directory exists
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Store progress callback
        self._progress_callback = progress_callback
        
        # Start progress tracking
        self._active_task_key = self._progress_tracker.start_task("voice_replacement")
        
        try:
            # Stage 1: Load models (5%)
            logger.info("Stage 1: Loading models...")
            self._update_progress(
                ProcessingStage.LOADING_MODELS, 
                5, 
                "Loading AI models..."
            )
            self._load_models()
            logger.info("Models loaded successfully")
            
            # Stage 2: Stem separation (5-30%)
            logger.info("Stage 2: Starting stem separation...")
            self._update_progress(
                ProcessingStage.STEM_SEPARATION,
                10,
                "Separating audio stems..."
            )
            stems, err = self._separate_stems(original_audio_path, output_dir)
            logger.info(f"Stem separation result: stems={stems is not None}, err={err}")
            
            if err:
                logger.error(f"Stem separation failed with error: {err}")
                return None, err, "Stem separation failed"
            
            logger.info("Stem separation complete, moving to voice conversion...")
            
            # Stage 3: Voice conversion (30-70%)
            self._update_progress(
                ProcessingStage.VOICE_CONVERSION,
                35,
                "Converting voice..."
            )
            converted_vocals, err = self._convert_voice(
                stems.vocals, 
                reference_voice_path,
                output_dir,
                voice_params
            )
            if err:
                return None, err, "Voice conversion failed"
            
            # Stage 4: Audio mixing (70-95%)
            self._update_progress(
                ProcessingStage.MIXING,
                75,
                "Mixing audio..."
            )
            final_output, err = self._mix_audio(converted_vocals, stems, output_dir)
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
            logger.error(f"Voice replacement failed: {e}")
            if self._active_task_key:
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
        
        # Invoke UI callback
        if self._progress_callback:
            self._progress_callback(percentage, message)
    
    def _load_models(self):
        """Load AI models"""
        # Load Demucs model
        logger.info("Loading Demucs model...")
        if hasattr(self._stem_separator, 'load_model'):
            self._stem_separator.load_model()
            logger.info("Demucs model load complete")
        else:
            logger.info("Stem separator does not have load_model method")
        
        # Load OpenVoice model
        logger.info("Loading OpenVoice model...")
        if hasattr(self._voice_converter, 'load_model'):
            logger.info("Calling voice_converter.load_model()...")
            try:
                self._voice_converter.load_model()
                logger.info("OpenVoice model load complete")
            except Exception as e:
                logger.error(f"OpenVoice load_model failed: {e}")
                import traceback
                traceback.print_exc()
                raise
        else:
            logger.info("Voice converter does not have load_model method")
        
        logger.info("All models loaded successfully")
    
    def _separate_stems(
        self, 
        audio_path: Path,
        output_dir: Path
    ) -> tuple[Optional[AudioStems], Optional[ErrorCode]]:
        """Separate audio into stems using Demucs"""
        logger.info(f"_separate_stems called: audio_path={audio_path}")
        try:
            # Use Demucs wrapper
            logger.info("Calling demucs_wrapper.separate()...")
            stems_dict, error = self._stem_separator.separate(
                audio_path,
                output_dir,
                progress_callback=None
            )
            
            logger.info(f"Separation returned: stems_dict={stems_dict is not None}, error={error}")
            
            if error:
                return None, ErrorCode.STEM_SEPARATION_FAILED
            
            # Convert dict to AudioStems
            stems = AudioStems(
                vocals=stems_dict.get('vocals'),
                drums=stems_dict.get('drums'),
                bass=stems_dict.get('bass'),
                other=stems_dict.get('other'),
            )
            
            logger.info("AudioStems created successfully")
            return stems, None
            
        except Exception as e:
            logger.error(f"Exception in _separate_stems: {e}")
            import traceback
            traceback.print_exc()
            return None, ErrorCode.STEM_SEPARATION_FAILED
    
    def _convert_voice(
        self, 
        vocal_path: Path, 
        reference_path: Path,
        output_dir: Path,
        params: VoiceConversionParams
    ) -> tuple[Optional[Path], Optional[ErrorCode]]:
        """Convert voice using OpenVoice"""
        try:
            # Generate output filename
            output_path = output_dir / "converted_vocals.wav"
            
            # Use OpenVoice wrapper
            result_path, error = self._voice_converter.convert_voice_simple(
                source_audio_path=vocal_path,
                reference_audio_path=reference_path,
                output_path=output_path,
                tau=0.3,  # Voice conversion strength
                progress_callback=None
            )
            
            if error:
                logger.error(f"Voice conversion error: {error}")
                return None, ErrorCode.VOICE_CONVERT_FAILED
            
            return result_path, None
            
        except Exception as e:
            logger.error(f"Voice conversion error: {e}")
            return None, ErrorCode.VOICE_CONVERT_FAILED
    
    def _mix_audio(
        self, 
        converted_vocals: Path, 
        stems: AudioStems,
        output_dir: Path
    ) -> tuple[Optional[Path], Optional[ErrorCode]]:
        """Mix audio using AudioMixer"""
        try:
            # Generate output filename
            output_path = output_dir / "mixed_output.wav"
            
            # Use AudioMixer
            result_path, error = self._audio_mixer.mix_simple(
                vocals_path=converted_vocals,
                drums_path=stems.drums,
                bass_path=stems.bass,
                other_path=stems.other,
                output_path=output_path,
                progress_callback=None
            )
            
            if error:
                logger.error(f"Audio mixing error: {error}")
                return None, ErrorCode.MIX_FAILED
            
            return result_path, None
            
        except Exception as e:
            logger.error(f"Audio mixing error: {e}")
            return None, ErrorCode.MIX_FAILED
