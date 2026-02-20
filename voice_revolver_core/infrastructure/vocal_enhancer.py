"""
Vocal Enhancer - Infrastructure Layer
Cleans and enhances vocal audio quality while preserving original loudness
"""

import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class VocalEnhancer:
    """
    Enhances vocal audio quality with noise reduction,
    compression, EQ, and normalization while preserving original loudness.
    """
    
    def __init__(self, sample_rate: int = 22050):
        self._sample_rate = sample_rate
        self._nr = None
        self._pb = None
        self._pyln = None
        self._dependencies_loaded = False
    
    def _load_dependencies(self):
        """Lazy load dependencies"""
        if self._dependencies_loaded:
            return True
            
        try:
            import noisereduce
            import pedalboard
            import pyloudnorm
            self._nr = noisereduce
            self._pb = pedalboard
            self._pyln = pyloudnorm
            self._dependencies_loaded = True
            logger.info("Vocal enhancement dependencies loaded")
            return True
        except ImportError as e:
            logger.warning(f"Vocal enhancement dependencies not available: {e}")
            return False
    
    def enhance_vocal(
        self, 
        input_path: Path, 
        output_path: Path,
        noise_reduction: float = 0.8,
        remove_reverb: bool = True
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Enhance vocal audio quality while preserving original loudness.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save enhanced audio
            noise_reduction: Noise reduction strength (0-1)
            remove_reverb: Apply reverb removal (drying effect)
            
        Returns:
            (output_path, error_message)
        """
        if not self._load_dependencies():
            # Fallback: just copy the file if dependencies not available
            import shutil
            shutil.copy(input_path, output_path)
            logger.warning("Enhancement skipped (dependencies missing), using original audio")
            return output_path, None
        
        try:
            logger.info(f"Enhancing vocal: {input_path}")
            
            # 1. Load audio
            audio, sr = librosa.load(str(input_path), sr=self._sample_rate, mono=True)
            
            # 2. Measure ORIGINAL loudness (to preserve it later)
            meter = self._pyln.Meter(sr)
            original_loudness = meter.integrated_loudness(audio)
            logger.info(f"Original loudness: {original_loudness:.2f} LUFS")
            
            # 3. Noise reduction (remove Demucs artifacts)
            logger.info("Applying noise reduction...")
            cleaned = self._nr.reduce_noise(
                y=audio, 
                sr=sr, 
                stationary=True,
                prop_decrease=noise_reduction
            )
            
            # 3.5. Reverb removal (dry the vocal)
            if remove_reverb:
                logger.info("Applying reverb removal (drying vocal)...")
                # Spectral gating approach: removes reverb tails
                # Use non-stationary reduction to target reverb (time-varying)
                cleaned = self._nr.reduce_noise(
                    y=cleaned,
                    sr=sr,
                    stationary=False,  # Better for reverb (time-varying)
                    prop_decrease=0.6,  # Moderate reduction
                    freq_mask_smooth_hz=500,  # Smooth frequency transitions
                    time_mask_smooth_ms=50    # Smooth time transitions (catches reverb tails)
                )
                logger.info("Reverb reduction complete")
            
            # 4. Apply professional audio effects
            logger.info("Applying audio effects...")
            
            # Build effects chain
            effects = [
                # Remove low-frequency rumble
                self._pb.HighpassFilter(cutoff_frequency_hz=80),
            ]
            
            # Add gate for reverb removal (cuts off quiet reverb tails)
            if remove_reverb:
                effects.append(
                    self._pb.NoiseGate(
                        threshold_db=-40,   # Cut signals below -40dB (reverb tails)
                        ratio=10,           # Aggressive gating
                        attack_ms=1.0,      # Fast attack
                        release_ms=100.0    # Moderate release (avoid choppy sound)
                    )
                )
            
            # Add remaining effects
            effects.extend([
                # Gentle dynamics control
                self._pb.Compressor(
                    threshold_db=-25, 
                    ratio=2.5,
                    attack_ms=10.0,
                    release_ms=100.0
                ),
                
                # Subtle clarity enhancement
                self._pb.LowShelfFilter(
                    cutoff_frequency_hz=200, 
                    gain_db=-1.5
                ),
                
                # Gentle presence boost
                self._pb.HighShelfFilter(
                    cutoff_frequency_hz=5000,
                    gain_db=1
                ),
                
                # Prevent clipping
                self._pb.Limiter(threshold_db=-1.0)
            ])
            
            board = self._pb.Pedalboard(effects)
            processed = board(cleaned, sr)
            
            # 5. Normalize back to ORIGINAL loudness (preserve mix balance)
            logger.info("Normalizing to original loudness...")
            processed_loudness = meter.integrated_loudness(processed)
            normalized = self._pyln.normalize.loudness(
                processed, 
                processed_loudness, 
                original_loudness  # Match original, not fixed target
            )
            
            logger.info(f"Final loudness: {original_loudness:.2f} LUFS (preserved)")
            
            # 6. Save enhanced audio
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), normalized, sr, subtype='PCM_16')
            
            logger.info(f"Vocal enhancement complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"Vocal enhancement failed: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            
            # Fallback: copy original
            import shutil
            shutil.copy(input_path, output_path)
            logger.warning("Using original audio due to enhancement error")
            return output_path, None  # Don't fail the whole pipeline
    
    def denoise_only(
        self, 
        input_path: Path, 
        output_path: Path,
        noise_reduction: float = 0.5
    ) -> Tuple[Optional[Path], Optional[str]]:
        """
        Apply ONLY noise reduction - no compression, no EQ.
        Perfect for reference voices to preserve character while cleaning background noise.
        
        Args:
            input_path: Path to input audio file
            output_path: Path to save denoised audio
            noise_reduction: Noise reduction strength (0-1), default 0.5 for subtle cleaning
            
        Returns:
            (output_path, error_message)
        """
        if not self._load_dependencies():
            # Fallback: just copy the file if dependencies not available
            import shutil
            shutil.copy(input_path, output_path)
            logger.warning("Denoising skipped (dependencies missing), using original audio")
            return output_path, None
        
        try:
            logger.info(f"Denoising audio (subtle): {input_path}")
            
            # 1. Load audio
            audio, sr = librosa.load(str(input_path), sr=self._sample_rate, mono=True)
            
            # 2. Noise reduction ONLY (no compression, no EQ)
            logger.info("Applying gentle noise reduction...")
            cleaned = self._nr.reduce_noise(
                y=audio, 
                sr=sr, 
                stationary=True,
                prop_decrease=noise_reduction  # Default 0.5 = subtle cleaning
            )
            
            # 3. Save denoised audio (preserve original characteristics)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), cleaned, sr, subtype='PCM_16')
            
            logger.info(f"Noise reduction complete: {output_path}")
            return output_path, None
            
        except Exception as e:
            error_msg = f"Denoising failed: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback.print_exc()
            
            # Fallback: copy original
            import shutil
            shutil.copy(input_path, output_path)
            logger.warning("Using original audio due to denoising error")
            return output_path, None
