"""
Voice Replacement Service - Application Layer
Orchestrates the full vocal replacement workflow
"""

from pathlib import Path
from typing import Optional, Callable
import asyncio
import logging
import numpy as np

from ..domain import (
    ProgressTracker,
    ProgressInfo,
    ProcessingStage,
    ErrorCode,
    AudioStems,
    VoiceConversionParams,
    generate_task_key,
)
from ..infrastructure.vocal_enhancer import VocalEnhancer
from ..infrastructure.rvc_wrapper import RVCWrapper
from ..infrastructure.gender_detector import GenderDetector
from ..infrastructure.audio_processor import AudioProcessor

logger = logging.getLogger(__name__)


class VoiceReplacementService:
    """
    Application service that orchestrates the full vocal replacement pipeline.
    Coordinates: StemSeparator → VoiceConverter → VoiceTransformer → AudioMixer
    """
    
    def __init__(
        self,
        stem_separator,      # Infrastructure: Demucs wrapper
        voice_converter,     # Infrastructure: ChatterBox wrapper (or OpenVoice if using legacy)
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
        self._vocal_enhancer = VocalEnhancer(sample_rate=22050)
        self._rvc_wrapper: Optional[RVCWrapper] = None  # Lazy-loaded for RVC mode
        self._gender_detector = GenderDetector()  # Gender-aware pitch adaptation
        self._audio_processor = AudioProcessor()  # Pitch shifting pre-processor
        
        self._active_task_key: Optional[str] = None
        self._progress_callback: Optional[Callable] = None
    
    def process(
        self,
        original_audio_path: Path,
        reference_voice_path: Path,
        voice_params: VoiceConversionParams,
        output_format: str = "mp3",
        output_dir: Optional[Path] = None,
        vocal_only: bool = False,
        reference_mode: str = "audio",
        progress_callback: Optional[Callable[[ProgressInfo], None]] = None,
    ) -> tuple[Optional[Path], Optional[ErrorCode], str]:
        """
        Execute full vocal replacement pipeline.
        
        Args:
            original_audio_path: Path to original song
            reference_voice_path: Path to reference voice audio or RVC model zip
            voice_params: Voice conversion parameters
            output_format: Output format (mp3, wav, flac)
            output_dir: Output directory (defaults to temp)
            vocal_only: If True, output only converted vocals without mixing
            reference_mode: 'audio' for audio file, 'model' for RVC zip
            progress_callback: Progress callback
            
        Returns:
            (output_path, error_code, error_message)
        """
        logger.info(f"process() called with original={original_audio_path}, reference={reference_voice_path}, mode={reference_mode}")
        
        if output_dir is None:
            output_dir = self._file_manager.temp_dir
        
        logger.info(f"Output directory: {output_dir}")
        
        # Ensure temp directory exists and clean up ALL preview files from previous runs
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clean up all preview files to prevent loading stale cached files
        preview_files = [
            "mixed_output.wav",
            "converted_vocals.wav",
            "original_vocals.wav",
            "original_drums.wav",
            "original_bass.wav",
            "original_other.wav",
            "instrumental_only.wav",
            "vocals_enhanced.wav"
        ]
        
        for filename in preview_files:
            file_path = output_dir / filename
            if file_path.exists():
                try:
                    file_path.unlink()
                    logger.info(f"Cleaned up previous file: {filename}")
                except Exception as e:
                    logger.warning(f"Could not clean up {filename}: {e}")
        
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
            
            # Copy stems to standardized names for UI preview
            import shutil
            stem_mappings = {
                'vocals': 'original_vocals.wav',
                'drums': 'original_drums.wav',
                'bass': 'original_bass.wav',
                'other': 'original_other.wav'
            }
            
            for stem_name, standard_name in stem_mappings.items():
                stem_path = getattr(stems, stem_name, None)
                if stem_path and stem_path.exists():
                    dest_path = output_dir / standard_name
                    # Skip copy if source and destination are the same file
                    if stem_path.resolve() != dest_path.resolve():
                        shutil.copy(stem_path, dest_path)
                        logger.info(f"Copied {stem_name} to {standard_name} for preview")
                    else:
                        logger.info(f"Skipped copying {stem_name} (already at {standard_name})")
            
            logger.info("Stem separation complete, enhancing vocals...")
            
            # Stage 2.5: Enhance separated vocals
            self._update_progress(
                ProcessingStage.VOICE_CONVERSION,
                32,
                "Enhancing separated vocals..."
            )
            enhanced_vocals_path = output_dir / "vocals_enhanced.wav"
            enhanced_vocals_result, enhance_err = self._vocal_enhancer.enhance_vocal(
                stems.vocals,
                enhanced_vocals_path,
                noise_reduction=0.3
            )
            
            # Use enhanced vocals for conversion (fallback to original if enhancement fails)
            vocals_to_convert = enhanced_vocals_result if enhanced_vocals_result else stems.vocals
            logger.info(f"Using vocals for conversion: {vocals_to_convert}")
            
            # Stage 2.6: Denoise reference voice (ONLY if using audio mode, skip for RVC model)
            if reference_mode == "audio":
                self._update_progress(
                    ProcessingStage.VOICE_CONVERSION,
                    33,
                    "Cleaning reference voice..."
                )
                denoised_reference_path = output_dir / "reference_denoised.wav"
                denoised_reference, denoise_err = self._vocal_enhancer.denoise_only(
                    reference_voice_path,
                    denoised_reference_path,
                    noise_reduction=0.5  # Subtle cleaning to preserve voice character
                )
                
                # Use denoised reference for conversion (fallback to original if denoising fails)
                reference_to_use = denoised_reference if denoised_reference else reference_voice_path
                logger.info(f"Using denoised reference audio: {reference_to_use}")
            else:
                # Model mode - use zip path directly (will be handled by RVC wrapper)
                reference_to_use = reference_voice_path
                logger.info(f"Using RVC model: {reference_to_use}")
            
            # Stage 3: Voice conversion (30-70%)
            self._update_progress(
                ProcessingStage.VOICE_CONVERSION,
                35,
                "Converting voice..." + (" (RVC)" if reference_mode == "model" else " (ChatterBox)")
            )
            converted_vocals, err = self._convert_voice(
                vocals_to_convert, 
                reference_to_use,
                output_dir,
                voice_params,
                reference_mode
            )
            if err:
                return None, err, "Voice conversion failed"
            
            # Stage 4: Audio mixing (70-95%) - ALWAYS create full mix for preview
            self._update_progress(
                ProcessingStage.MIXING,
                75,
                "Mixing audio..."
            )
            final_mix, err = self._mix_audio(converted_vocals, stems, output_dir)
            if err:
                return None, err, "Audio mixing failed"
            
            # Stage 5: Choose output based on vocal_only setting
            if vocal_only:
                logger.info("Vocal-only mode: returning vocals only as final output")
                final_output = converted_vocals
            else:
                logger.info("Full mix mode: returning mixed audio as final output")
                final_output = final_mix
            
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
        # Load stem separation model (Demucs or MDX)
        logger.info("Loading stem separation model...")
        if hasattr(self._stem_separator, 'load_model'):
            success, error = self._stem_separator.load_model()
            if not success:
                error_msg = f"Failed to load stem separation model: {error}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            logger.info("Stem separation model load complete")
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
        params: VoiceConversionParams,
        reference_mode: str = "audio"
    ) -> tuple[Optional[Path], Optional[ErrorCode]]:
        """Convert voice using ChatterBox VC (audio mode) or RVC (model mode)"""
        try:
            # Generate output filename
            output_path = output_dir / "converted_vocals.wav"
            
            # Gender-aware pitch adaptation (only for audio mode, skip for model mode)
            pitch_shift = params.pitch  # Default to manual pitch setting
            original_gender = None  # Will be set for RVC manual mode
            model_gender = None  # Will be set for RVC manual mode
            
            if reference_mode == "audio" and params.auto_detect_gender:
                logger.info("Performing automatic gender detection for pitch adaptation")
                try:
                    # Detect gender and calculate pitch shift
                    calculated_shift, explanation = self._gender_detector.calculate_pitch_shift(
                        original_audio=vocal_path,
                        reference_audio=reference_path
                    )
                    
                    # Store detected genders in params for UI display
                    params.detected_original_gender = self._gender_detector.detect_gender(vocal_path)
                    params.detected_reference_gender = self._gender_detector.detect_gender(reference_path)
                    
                    # Use calculated pitch shift if detection succeeded
                    if calculated_shift != 0:  # Gender mismatch detected
                        pitch_shift = calculated_shift
                        logger.info(f"Gender detection: {explanation}")
                    else:
                        logger.info(f"Gender detection: {explanation}")
                        
                except Exception as e:
                    logger.warning(f"Gender detection failed: {e}, using manual pitch setting")
            
            elif reference_mode == "model" and params.auto_detect_gender and params.original_gender and params.model_gender:
                # Model mode with manual gender selection (TRUST USER INPUT - no auto-detection override)
                logger.info(f"Using manual gender selection: Original={params.original_gender}, Model={params.model_gender}")
                
                original_gender = params.original_gender
                model_gender = params.model_gender
                
                # Use FIXED shifts based on user's manual selection
                # Do NOT override with F0 detection - if user says it's male, treat it as male!
                if original_gender == model_gender:
                    pitch_shift = 0
                    explanation = f"Same gender ({original_gender}): no pitch shift"
                elif original_gender == "male" and model_gender == "female":
                    pitch_shift = 12
                    explanation = f"Male -> Female model: +{pitch_shift} semitones (manual selection)"
                elif original_gender == "female" and model_gender == "male":
                    pitch_shift = -12
                    explanation = f"Female -> Male model: {pitch_shift} semitones (manual selection)"
                else:
                    pitch_shift = 0
                    explanation = "No pitch shift"
                
                logger.info(f"Manual gender alignment: {explanation}")
            
            logger.info(f"Final pitch shift: {pitch_shift:+d} semitones")
            
            # Pre-process vocal with Parselmouth adaptive pitch shifting if needed
            vocal_to_convert = vocal_path  # Default to original vocal
            
            if pitch_shift != 0 and reference_mode == "model":
                logger.info(f"Pre-shifting vocal using ADAPTIVE pitch shift (gender-aware)")
                logger.info(f"Thresholds: Low={params.threshold_low:.0f}Hz, Mid={params.threshold_mid:.0f}Hz, High={params.threshold_high:.0f}Hz")
                
                # Create temp file for pitch-shifted vocal
                shifted_vocal_path = output_dir / f"vocal_adaptive_pitch_shifted.wav"
                
                # Apply ADAPTIVE gender-aware pitch shifting with user-defined thresholds
                # This analyzes pitch moment-by-moment and shifts only what's needed
                # Lower thresholds = more aggressive shifting (better for subtle voices)
                shift_success = self._audio_processor.pitch_shift_adaptive(
                    audio_path=vocal_path,
                    output_path=shifted_vocal_path,
                    source_gender=original_gender,
                    target_gender=model_gender,
                    target_male_f0=130.0,
                    target_female_f0=210.0,
                    max_shift_semitones=12.0,
                    smoothing_window=5,
                    threshold_low=params.threshold_low,
                    threshold_mid=params.threshold_mid,
                    threshold_high=params.threshold_high
                )
                
                if shift_success:
                    logger.info(f"Adaptive pitch shift successful, using shifted vocal for RVC")
                    vocal_to_convert = shifted_vocal_path
                    # Set pitch shift to 0 for RVC since we've already done it
                    rvc_pitch_shift = 0
                else:
                    logger.warning(f"Adaptive pitch shifting failed, RVC will handle pitch shift instead")
                    vocal_to_convert = vocal_path
                    rvc_pitch_shift = pitch_shift
            elif pitch_shift != 0 and reference_mode == "audio":
                # For audio mode, still use fixed shift (adaptive only for RVC mode)
                logger.info(f"Pre-shifting vocal pitch by {pitch_shift:+d} semitones (fixed shift for audio mode)")
                
                shifted_vocal_path = output_dir / f"vocal_pitch_shifted_{abs(pitch_shift)}st.wav"
                
                shift_success = self._audio_processor.pitch_shift_gender(
                    audio_path=vocal_path,
                    output_path=shifted_vocal_path,
                    semitones=float(pitch_shift)
                )
                
                if shift_success:
                    logger.info(f"Vocal pitch shifted successfully, using shifted vocal")
                    vocal_to_convert = shifted_vocal_path
                    rvc_pitch_shift = 0
                else:
                    logger.warning(f"Pitch shifting failed")
                    vocal_to_convert = vocal_path
                    rvc_pitch_shift = pitch_shift
            else:
                logger.info("No pitch shift needed, using original vocal")
                rvc_pitch_shift = 0
            
            if reference_mode == "audio":
                # Audio mode - Use ChatterBox wrapper (simple API)
                logger.info("Using ChatterBox VC for audio reference conversion")
                result_path, error = self._voice_converter.convert_voice(
                    source_audio_path=vocal_to_convert,  # Use pitch-shifted vocal if available
                    target_voice_path=reference_path,
                    output_path=output_path,
                    progress_callback=None
                )
                
            elif reference_mode == "model":
                # Model mode - Use RVC wrapper with pre-trained model
                logger.info(f"Using RVC for model reference conversion: {reference_path}")
                
                # Lazy-load RVC wrapper (use CUDA if available)
                if self._rvc_wrapper is None:
                    logger.info("Initializing RVC wrapper")
                    try:
                        import torch
                        device = "cuda" if torch.cuda.is_available() else "cpu"
                        logger.info(f"RVC device: {device}")
                    except ImportError:
                        device = "cpu"
                        logger.warning("PyTorch not found, using CPU for RVC")
                    self._rvc_wrapper = RVCWrapper(device=device)
                
                # Load model from zip
                logger.info("Loading RVC model from zip")
                load_success, load_error = self._rvc_wrapper.load_model_from_zip(reference_path)
                if load_error:
                    logger.error(f"RVC model load error: {load_error}")
                    return None, ErrorCode.VOICE_CONVERT_FAILED
                
                # Convert voice using RVC
                logger.info("Converting voice with RVC")
                result_path, error = self._rvc_wrapper.convert_voice(
                    source_audio_path=vocal_to_convert,  # Use pitch-shifted vocal if available
                    output_path=output_path,
                    f0_method="rmvpe",  # Best quality pitch detection
                    f0_up_key=rvc_pitch_shift,  # 0 if already shifted, otherwise apply shift
                    index_rate=0.75,  # Retrieval index influence
                    filter_radius=3,  # Pitch smoothing
                    resample_sr=0,  # Keep original sample rate
                    rms_mix_rate=0.25,  # Envelope mixing
                    protect=0.33  # Consonant protection
                )
                
                # Unload model after conversion to free resources
                logger.info("Unloading RVC model")
                self._rvc_wrapper.unload_model()
                
            else:
                logger.error(f"Invalid reference_mode: {reference_mode}")
                return None, ErrorCode.VOICE_CONVERT_FAILED
            
            # NOTE: If using OpenVoice wrapper instead of ChatterBox, use:
            # result_path, error = self._voice_converter.convert_voice_simple(
            #     source_audio_path=vocal_path,
            #     reference_audio_path=reference_path,
            #     output_path=output_path,
            #     tau=params.tau,  # Voice conversion strength from UI
            #     style=params.style,  # Apply voice style
            #     progress_callback=None
            # )
            
            if error:
                logger.error(f"Voice conversion error: {error}")
                return None, ErrorCode.VOICE_CONVERT_FAILED
            
            return result_path, None
            
        except Exception as e:
            logger.error(f"Voice conversion error: {e}")
            import traceback
            traceback.print_exc()
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
