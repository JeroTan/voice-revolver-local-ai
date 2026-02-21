"""Audio processing utilities for pitch shifting and manipulation.

This module provides low-level audio processing functions including:
- Pitch shifting (semitone-based)
- Gender-aware pitch shifting using Praat/Parselmouth
- Adaptive pitch shifting with SMOOTH INTERPOLATION
- Sample rate conversion
- Audio format normalization

Pitch Shifting Methods:
1. pitch_shift(): Uses librosa's phase vocoder (good for music, simple)
2. pitch_shift_gender(): Uses Praat's Change Gender (better for voice, preserves formants)
3. pitch_shift_adaptive(): SMART adaptive with cubic spline interpolation (best for natural transitions)

Adaptive Pitch Shifting:
- Analyzes pitch moment-by-moment throughout the song
- Applies variable shift based on actual F0 at each time point
- Uses median filtering to remove outliers and sudden jumps
- Cubic spline interpolation creates smooth, natural transitions (not linear!)
- Preserves melody while matching target gender range

Example use case (Maroon 5 "Daylight"):
- Low verses (140Hz): Shift +5 semitones
- High chorus (200Hz): Shift +1 semitone
- Smooth transition between: Cubic interpolation prevents robotic steps
"""

import logging
from pathlib import Path
import librosa
import soundfile as sf
import numpy as np
import parselmouth
from parselmouth.praat import call
from scipy.ndimage import median_filter
from scipy.interpolate import interp1d

logger = logging.getLogger(__name__)


class AudioProcessor:
    """Handles audio processing operations like pitch shifting and resampling."""
    
    def __init__(self, target_sr: int = 40000):
        """
        Initialize audio processor.
        
        Args:
            target_sr: Target sample rate for processed audio (default: 40kHz for RVC)
        """
        self.target_sr = target_sr
    
    def pitch_shift(
        self,
        audio_path: Path,
        output_path: Path,
        semitones: float
    ) -> bool:
        """
        Shift the pitch of an audio file by a specified number of semitones.
        
        Uses librosa's high-quality phase vocoder pitch shifting algorithm.
        Preserves audio duration while changing pitch.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            semitones: Number of semitones to shift (positive = up, negative = down)
                      +12 = one octave up, -12 = one octave down
        
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> processor = AudioProcessor()
            >>> processor.pitch_shift(input_wav, output_wav, 12)  # Shift up one octave
        """
        try:
            logger.info(f"Pitch shifting {audio_path.name} by {semitones:+.1f} semitones")
            
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=None, mono=True)
            
            # Apply pitch shift
            audio_shifted = librosa.effects.pitch_shift(
                audio,
                sr=sr,
                n_steps=semitones
            )
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio_shifted, sr)
            
            logger.info(f"Pitch-shifted audio saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Pitch shift failed for {audio_path}: {e}")
            return False
    
    def pitch_shift_adaptive(
        self,
        audio_path: Path,
        output_path: Path,
        source_gender: str,
        target_gender: str,
        target_male_f0: float = 130.0,
        target_female_f0: float = 210.0,
        max_shift_semitones: float = 12.0,
        smoothing_window: int = 5,
        threshold_low: float = 150.0,
        threshold_mid: float = 190.0,
        threshold_high: float = 230.0
    ) -> bool:
        """
        Dynamically shift pitch with SMOOTH INTERPOLATION and THRESHOLD-BASED SENSITIVITY.
        
        Analyzes the pitch contour and applies variable shift with:
        - Threshold-based shift calculation (lower threshold = more aggressive)
        - Median filtering to remove outliers/sudden jumps
        - Cubic spline interpolation for smooth transitions (not linear!)
        - Natural pitch curves that follow melody
        
        Threshold zones (male to female example):
        - Below threshold_low (e.g., <150Hz): Full shift (up to max_shift_semitones)
        - Between low-mid (150-190Hz): Gradual reduction in shift
        - Between mid-high (190-230Hz): Further reduction
        - Above threshold_high (>230Hz): Minimal shift
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            source_gender: Original voice gender ("male" or "female")
            target_gender: Target voice gender ("male" or "female")
            target_male_f0: Target pitch for male voice (Hz)
            target_female_f0: Target pitch for female voice (Hz)
            max_shift_semitones: Maximum shift to apply (prevents over-shifting)
            smoothing_window: Window size for median smoothing (removes jumps)
            threshold_low: Low F0 threshold - aggressive shift below this (Hz)
            threshold_mid: Mid F0 threshold - moderate shift (Hz)
            threshold_high: High F0 threshold - conservative shift above this (Hz)
        
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> processor = AudioProcessor()
            >>> processor.pitch_shift_adaptive(vocal_wav, output_wav, "male", "female",
            ...     threshold_low=140, threshold_mid=180, threshold_high=220)
            # Male 120Hz: +12st, Male 180Hz: +7st, Male 220Hz: +2st
        """
        try:
            if source_gender == target_gender:
                logger.info(f"Same gender, no pitch shift needed")
                import shutil
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(audio_path), str(output_path))
                return True
            
            logger.info(f"Adaptive pitch shifting (SMOOTH) {audio_path.name}: {source_gender} -> {target_gender}")
            
            # Load audio
            sound = parselmouth.Sound(str(audio_path))
            
            # Extract pitch using Praat with finer time step for smoother curves
            pitch = sound.to_pitch(time_step=0.005, pitch_floor=75.0, pitch_ceiling=400.0)
            
            # Get pitch values over time
            f0_values = pitch.selected_array['frequency']
            times = pitch.xs()
            
            # Determine target F0
            target_f0 = target_female_f0 if target_gender == "female" else target_male_f0
            
            # STEP 1: Calculate raw shift values with THRESHOLD-BASED SENSITIVITY
            raw_shifts = []
            valid_times = []
            valid_f0s = []
            
            logger.info(f"Using thresholds: Low={threshold_low}Hz, Mid={threshold_mid}Hz, High={threshold_high}Hz")
            
            # Track F0 distribution for detailed logging
            f0_distribution = {"below_low": 0, "low_to_mid": 0, "mid_to_high": 0, "above_high": 0}
            f0_samples = []  # [(f0, sensitivity, shift)]
            
            for time, f0 in zip(times, f0_values):
                if f0 > 0 and not np.isnan(f0):  # Voiced segment
                    # Calculate base shift needed to reach target
                    needed_shift = 12 * np.log2(target_f0 / f0)
                    
                    # Apply threshold-based sensitivity multiplier
                    # Lower F0 (below threshold_low) = full shift
                    # Higher F0 (above threshold_high) = minimal shift
                    if source_gender == "male" and target_gender == "female":
                        # Male to Female: reduce shift for higher pitches
                        if f0 < threshold_low:
                            # Aggressive shift for low pitches
                            sensitivity = 1.0
                            f0_distribution["below_low"] += 1
                        elif f0 < threshold_mid:
                            # Gradual reduction between low and mid
                            sensitivity = 1.0 - 0.3 * (f0 - threshold_low) / (threshold_mid - threshold_low)
                            f0_distribution["low_to_mid"] += 1
                        elif f0 < threshold_high:
                            # Further reduction between mid and high
                            sensitivity = 0.7 - 0.5 * (f0 - threshold_mid) / (threshold_high - threshold_mid)
                            f0_distribution["mid_to_high"] += 1
                        else:
                            # Minimal shift for already high pitches
                            sensitivity = 0.2
                            f0_distribution["above_high"] += 1
                        
                        actual_shift = np.clip(needed_shift * sensitivity, 0, max_shift_semitones)
                        
                    elif source_gender == "female" and target_gender == "male":
                        # Female to Male: similar logic but inverted
                        if f0 > threshold_high:
                            sensitivity = 1.0  # Aggressive shift for high pitches
                            f0_distribution["above_high"] += 1
                        elif f0 > threshold_mid:
                            sensitivity = 1.0 - 0.3 * (threshold_high - f0) / (threshold_high - threshold_mid)
                            f0_distribution["mid_to_high"] += 1
                        elif f0 > threshold_low:
                            sensitivity = 0.7 - 0.5 * (threshold_mid - f0) / (threshold_mid - threshold_low)
                            f0_distribution["low_to_mid"] += 1
                        else:
                            sensitivity = 0.2  # Minimal shift for already low pitches
                            f0_distribution["below_low"] += 1
                        
                        actual_shift = np.clip(needed_shift * sensitivity, -max_shift_semitones, 0)
                    else:
                        actual_shift = 0
                        sensitivity = 0
                    
                    # Collect sample data points for logging (every 100th frame)
                    if len(raw_shifts) % 100 == 0:
                        f0_samples.append((f0, sensitivity, actual_shift))
                    
                    raw_shifts.append(actual_shift)
                    valid_times.append(time)
                    valid_f0s.append(f0)
            
            if len(raw_shifts) < 3:
                logger.warning("Not enough voiced segments for adaptive shifting, using fixed shift")
                fixed_shift = max_shift_semitones if target_gender == "female" else -max_shift_semitones
                return self.pitch_shift_gender(audio_path, output_path, fixed_shift)
            
            # Log F0 distribution and sensitivity analysis
            total_frames = sum(f0_distribution.values())
            logger.info(f"=" * 60)
            logger.info(f"F0 DISTRIBUTION ANALYSIS ({total_frames} voiced frames):")
            logger.info(f"  Below {threshold_low}Hz (100% shift):  {f0_distribution['below_low']} frames ({100*f0_distribution['below_low']/total_frames:.1f}%)")
            logger.info(f"  {threshold_low}-{threshold_mid}Hz (100%->70% shift): {f0_distribution['low_to_mid']} frames ({100*f0_distribution['low_to_mid']/total_frames:.1f}%)")
            logger.info(f"  {threshold_mid:.0f}-{threshold_high:.0f}Hz (70%->20% shift):  {f0_distribution['mid_to_high']} frames ({100*f0_distribution['mid_to_high']/total_frames:.1f}%)")
            logger.info(f"  Above {threshold_high}Hz (20% shift):   {f0_distribution['above_high']} frames ({100*f0_distribution['above_high']/total_frames:.1f}%)")
            
            # Log sample pitch shift values
            if f0_samples:
                logger.info(f"SAMPLE PITCH SHIFTS (showing 5 examples):")
                for i, (f0, sens, shift) in enumerate(f0_samples[:5]):
                    logger.info(f"  F0={f0:.0f}Hz -> sensitivity={sens:.2f} -> shift={shift:+.2f}st (out of +{max_shift_semitones}st max)")
            logger.info(f"=" * 60)
            
            # STEP 2: Apply median filtering to smooth out sudden jumps (removes outliers)
            raw_shifts = np.array(raw_shifts)
            smoothed_shifts = median_filter(raw_shifts, size=min(smoothing_window, len(raw_shifts)))
            
            # STEP 3: Create cubic spline interpolation for smooth transitions
            # This creates natural curves instead of linear/step transitions
            try:
                # Cubic spline for ultra-smooth transitions (like human pitch glides)
                shift_interpolator = interp1d(
                    valid_times, 
                    smoothed_shifts, 
                    kind='cubic',
                    bounds_error=False,
                    fill_value=(smoothed_shifts[0], smoothed_shifts[-1])  # Extrapolate at edges
                )
            except Exception as e:
                logger.warning(f"Cubic interpolation failed: {e}, using linear")
                shift_interpolator = interp1d(
                    valid_times, 
                    smoothed_shifts, 
                    kind='linear',
                    bounds_error=False,
                    fill_value=(smoothed_shifts[0], smoothed_shifts[-1])
                )
            
            # STEP 4: Create manipulation object and new pitch tier
            manipulation = call(sound, "To Manipulation", 0.005, 75, 400)
            pitch_tier = call(manipulation, "Extract pitch tier")
            
            # STEP 5: Apply smoothly interpolated pitch shifts
            # Sample at finer intervals for smoother curves
            for time, f0 in zip(valid_times, valid_f0s):
                # Get interpolated shift value at this time point
                interpolated_shift = float(shift_interpolator(time))
                
                # Apply shift: new_f0 = original_f0 * 2^(shift/12)
                new_f0 = f0 * (2 ** (interpolated_shift / 12))
                
                # Add point to pitch tier
                call(pitch_tier, "Add point", time, new_f0)
            
            # STEP 6: Replace pitch tier and synthesize
            call([pitch_tier, manipulation], "Replace pitch tier")
            modified_sound = call(manipulation, "Get resynthesis (overlap-add)")
            
            # STEP 7: APPLY FORMANT SHIFTING (critical for gender quality!)
            # Formants are the vocal tract resonances that give "male" vs "female" quality
            # Without formant shifting, it sounds like high-pitched male, not female!
            logger.info(f"Applying formant shift for gender conversion...")
            
            if source_gender == "male" and target_gender == "female":
                # Male -> Female: Increase formants (shorter vocal tract)
                # Formant shift ratio: 1.2 means formants move 20% higher in frequency
                formant_ratio = 1.2
                logger.info(f"Male->Female: Formant shift ratio = {formant_ratio} (vocal tract shortened)")
            elif source_gender == "female" and target_gender == "male":
                # Female -> Male: Decrease formants (longer vocal tract)
                # Formant shift ratio: 0.85 means formants move 15% lower in frequency
                formant_ratio = 0.85
                logger.info(f"Female->Male: Formant shift ratio = {formant_ratio} (vocal tract lengthened)")
            else:
                formant_ratio = 1.0
            
            # Apply formant shifting using Praat's change_gender algorithm
            # This shifts formant frequencies while keeping pitch unchanged (we already shifted pitch)
            try:
                modified_sound = modified_sound.change_gender(
                    formant_shift_ratio=formant_ratio,  # Shift formants
                    new_pitch_median=0,                 # 0 = don't change pitch (already done)
                    pitch_range_factor=1.0,             # Keep pitch range
                    duration_factor=1.0                 # Keep same speed
                )
                logger.info(f"[OK] Formant shifting complete (this gives true gender quality!)")
            except Exception as e:
                logger.warning(f"Formant shift failed, trying alternative method: {e}")
                # Alternative: Use Praat's Change gender command via call
                modified_sound = call(modified_sound, "Change gender",
                                    75, 400,         # pitch floor/ceiling
                                    formant_ratio,   # formant shift
                                    0,               # new pitch median (0=unchanged)
                                    1.0, 1.0)        # pitch range, duration factors
                logger.info(f"[OK] Formant shifting complete (alternative method)")
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            modified_sound.save(str(output_path), "WAV")
            
            # Log statistics
            avg_shift = np.mean(smoothed_shifts)
            min_shift = np.min(smoothed_shifts)
            max_shift = np.max(smoothed_shifts)
            logger.info(f"FINAL RESULT: Avg shift={avg_shift:.2f}st, Range=[{min_shift:.2f}, {max_shift:.2f}]st")
            logger.info(f"Applied cubic spline interpolation for natural transitions")
            
            # Warning if shift is too subtle
            if abs(avg_shift) < 2.0:
                logger.warning(f"[!] AVERAGE SHIFT IS VERY LOW ({avg_shift:.2f}st)!")
                logger.warning(f"[!] Most vocals are in mid-high frequency range getting minimal shift")
                logger.warning(f"[!] SOLUTION: LOWER all threshold values to make shift more aggressive")
                logger.warning(f"[!] Try: Low=120Hz, Mid=170Hz, High=230Hz (for stronger effect)")
            
            logger.info(f"Adaptive pitch-shifted audio saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Adaptive pitch shift failed for {audio_path}: {e}")
            logger.warning(f"Falling back to fixed gender shift")
            # Fallback to fixed shift
            fixed_shift = max_shift_semitones if target_gender == "female" else -max_shift_semitones
            return self.pitch_shift_gender(audio_path, output_path, fixed_shift)
    
    def pitch_shift_gender(
        self,
        audio_path: Path,
        output_path: Path,
        semitones: float
    ) -> bool:
        """
        Shift the pitch of an audio file using Parselmouth for gender-aware conversion.
        
        Uses Praat's manipulation engine for natural-sounding pitch shifting
        that preserves formants and speech characteristics better than simple
        phase vocoder methods.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            semitones: Number of semitones to shift (positive = up, negative = down)
        
        Returns:
            True if successful, False otherwise
            
        Example:
            >>> processor = AudioProcessor()
            >>> processor.pitch_shift_gender(male_wav, shifted_wav, 5)  # Male -> Female
        """
        try:
            if semitones == 0:
                logger.info(f"No pitch shift needed (0 semitones), copying file")
                # Just copy the file if no shift needed
                import shutil
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(str(audio_path), str(output_path))
                return True
            
            logger.info(f"Pitch shifting {audio_path.name} by {semitones:+.1f} semitones (Parselmouth)")
            
            # Load audio with Parselmouth
            sound = parselmouth.Sound(str(audio_path))
            
            # Calculate pitch shift factor (2^(semitones/12))
            # For example: +12 semitones = 2.0 (double frequency)
            #              -12 semitones = 0.5 (half frequency)
            pitch_factor = 2 ** (semitones / 12)
            
            # Use Praat's Change Gender function
            # new_pitch_median: Multiply median pitch by this factor
            # formant_shift_ratio: 1.0 keeps formants unchanged (important for naturalness)
            # pitch_range_factor: 1.0 keeps pitch range proportional
            # duration_factor: 1.0 keeps duration the same
            manipulated = call(sound, "Change gender", 
                             75,              # Minimum pitch (Hz)
                             400,             # Maximum pitch (Hz) 
                             0.0,             # Formant shift ratio (0 = no formant shift)
                             pitch_factor,    # New pitch median (multiplier)
                             1.0,             # Pitch range factor
                             1.0)             # Duration factor
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            manipulated.save(str(output_path), "WAV")
            
            logger.info(f"Gender-aware pitch-shifted audio saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Parselmouth pitch shift failed for {audio_path}: {e}")
            logger.warning(f"Falling back to librosa pitch shift")
            # Fallback to librosa if Parselmouth fails
            return self.pitch_shift(audio_path, output_path, semitones)
    
    def resample(
        self,
        audio_path: Path,
        output_path: Path,
        target_sr: int = None
    ) -> bool:
        """
        Resample audio to a target sample rate.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            target_sr: Target sample rate (uses self.target_sr if None)
        
        Returns:
            True if successful, False otherwise
        """
        if target_sr is None:
            target_sr = self.target_sr
            
        try:
            logger.info(f"Resampling {audio_path.name} to {target_sr}Hz")
            
            # Load and resample
            audio, original_sr = librosa.load(str(audio_path), sr=target_sr, mono=True)
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio, target_sr)
            
            logger.info(f"Resampled audio saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Resampling failed for {audio_path}: {e}")
            return False
    
    def normalize_audio(
        self,
        audio_path: Path,
        output_path: Path,
        target_db: float = -20.0
    ) -> bool:
        """
        Normalize audio to a target loudness level.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            target_db: Target RMS level in dB (default: -20dB)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Normalizing {audio_path.name} to {target_db}dB")
            
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=None, mono=True)
            
            # Calculate current RMS
            current_rms = np.sqrt(np.mean(audio ** 2))
            
            if current_rms == 0:
                logger.warning("Audio is silent, skipping normalization")
                return False
            
            # Calculate target RMS from dB
            target_rms = 10 ** (target_db / 20)
            
            # Apply gain
            gain = target_rms / current_rms
            audio_normalized = audio * gain
            
            # Prevent clipping
            max_val = np.max(np.abs(audio_normalized))
            if max_val > 1.0:
                audio_normalized = audio_normalized / max_val * 0.99
                logger.warning(f"Applied limiting to prevent clipping (max={max_val:.2f})")
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio_normalized, sr)
            
            logger.info(f"Normalized audio saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Normalization failed for {audio_path}: {e}")
            return False
    
    def process_for_rvc(
        self,
        audio_path: Path,
        output_path: Path,
        pitch_shift_semitones: float = 0
    ) -> bool:
        """
        Prepare audio for RVC inference with optional pitch shifting.
        
        This is a convenience method that:
        1. Optionally applies pitch shift
        2. Resamples to RVC target sample rate (40kHz)
        3. Ensures mono channel
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path 
            pitch_shift_semitones: Pitch shift in semitones (0 = no shift)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=None, mono=True)
            
            # Apply pitch shift if requested
            if pitch_shift_semitones != 0:
                logger.info(f"Applying pitch shift: {pitch_shift_semitones:+.1f} semitones")
                audio = librosa.effects.pitch_shift(
                    audio,
                    sr=sr,
                    n_steps=pitch_shift_semitones
                )
            
            # Resample to target sample rate
            if sr != self.target_sr:
                logger.info(f"Resampling from {sr}Hz to {self.target_sr}Hz")
                audio = librosa.resample(audio, orig_sr=sr, target_sr=self.target_sr)
            
            # Save processed audio
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio, self.target_sr)
            
            logger.info(f"Audio processed for RVC: {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"RVC processing failed for {audio_path}: {e}")
            return False
    
    def apply_pitch_curve(
        self,
        audio_path: Path,
        output_path: Path,
        pitch_curve
    ) -> bool:
        """
        Apply time-varying pitch shift based on user-edited pitch curve.
        
        Uses Parselmouth (Praat) to apply smooth pitch modifications at each time point.
        The pitch curve is sampled using cubic spline interpolation for natural transitions.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            pitch_curve: PitchCurve object with control points (time, shift_semitones)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not pitch_curve or not pitch_curve.has_edits():
                logger.info("No pitch curve edits, skipping pitch curve processing")
                return True
            
            logger.info(f"Applying pitch curve ({len(pitch_curve.control_points)} control points)")
            
            # Load audio with Parselmouth
            sound = parselmouth.Sound(str(audio_path))
            duration = sound.get_total_duration()
            
            # Get control points directly
            curve_times = np.array([p.time for p in pitch_curve.control_points])
            curve_shifts = np.array([p.shift_semitones for p in pitch_curve.control_points])
            
            # Apply time-varying pitch shift using Praat's pitch tier manipulation  
            manipulation = call(sound, "To Manipulation", 0.01, 75, 600)
            # Extract the existing pitch tier from manipulation (has detected pitches)
            original_pitch_tier = call(manipulation, "Extract pitch tier")
            
            # Get all existing pitch points from the tier
            num_points = call(original_pitch_tier, "Get number of points")
            
            # Create a new pitch tier for modified values
            new_pitch_tier = call("Create PitchTier", "modified", 0, duration)
            
            # Modify each detected pitch point based on our curve
            for i in range(1, num_points + 1):  # Praat uses 1-based indexing
                time = call(original_pitch_tier, "Get time from index", i)
                original_pitch = call(original_pitch_tier, "Get value at index", i)
                
                # Interpolate shift value at this time from our curve  
                if len(curve_times) == 1:
                    semitones = curve_shifts[0]
                else:
                    semitones = float(np.interp(time, curve_times, curve_shifts))
                
                # Convert semitones to frequency ratio
                freq_ratio = 2.0 ** (semitones / 12.0)
                
                # Apply shift to this pitch point
                new_pitch = original_pitch * freq_ratio
                call(new_pitch_tier, "Add point", time, new_pitch)
            
            # Replace pitch tier and synthesize
            call([new_pitch_tier, manipulation], "Replace pitch tier")
            sound_shifted = call(manipulation, "Get resynthesis (overlap-add)")
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sound_shifted.save(str(output_path), "WAV")
            
            logger.info(f"Pitch curve applied, saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Pitch curve application failed for {audio_path}: {e}")
            return False
    
    def apply_volume_curve(
        self,
        audio_path: Path,
        output_path: Path,
        volume_curve
    ) -> bool:
        """
        Apply time-varying volume (gain) based on user-edited volume curve.
        
        Applies smooth gain adjustments in dB at each time point using cubic interpolation.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            volume_curve: VolumeCurve object with control points (time, gain_db)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not volume_curve or not volume_curve.has_edits():
                logger.info("No volume curve edits, skipping volume curve processing")
                return True
            
            logger.info(f"Applying volume curve ({len(volume_curve.control_points)} control points)")
            
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=None, mono=True)
            duration = len(audio) / sr
            
            # Create time points for each audio sample
            time_points = np.arange(len(audio)) / sr
            
            # Sample the volume curve at each time point
            curve_times = np.array([p.time for p in volume_curve.control_points])
            curve_gains_db = np.array([p.gain_db for p in volume_curve.control_points])
            
            # Use cubic spline for smooth interpolation
            from scipy.interpolate import interp1d, CubicSpline
            if len(curve_times) == 1:
                # Single point: constant gain
                gain_db_values = np.full(len(time_points), curve_gains_db[0])
            elif len(curve_times) == 2:
                # Two points: use linear interpolation (cubic needs 3+ points)
                interp_func = interp1d(
                    curve_times,
                    curve_gains_db,
                    kind='linear',
                    bounds_error=False,
                    fill_value=(curve_gains_db[0], curve_gains_db[-1])
                )
                gain_db_values = interp_func(time_points)
            else:
                # 3+ points: use CubicSpline with natural boundary conditions
                interp_func = CubicSpline(
                    curve_times,
                    curve_gains_db,
                    bc_type='natural',  # Natural spline: 2nd derivative = 0 at boundaries
                    extrapolate=True
                )
                gain_db_values = interp_func(time_points)
            
            # Convert dB to linear gain: linear_gain = 10^(dB/20)
            linear_gains = 10.0 ** (gain_db_values / 20.0)
            
            # Apply gain curve to audio
            audio_processed = audio * linear_gains
            
            # Prevent clipping
            max_val = np.abs(audio_processed).max()
            if max_val > 1.0:
                audio_processed = audio_processed / max_val
                logger.warning(f"Volume curve caused clipping, normalized to prevent distortion")
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_path), audio_processed, sr)
            
            logger.info(f"Volume curve applied, saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Volume curve application failed for {audio_path}: {e}")
            return False
    
    def apply_reverb_curve(
        self,
        audio_path: Path,
        output_path: Path,
        reverb_curve
    ) -> bool:
        """
        Apply time-varying reverb based on user-edited reverb curve.
        
        Uses pedalboard for high-quality reverb with time-varying wet/dry mix.
        
        Args:
            audio_path: Input audio file path
            output_path: Output audio file path
            reverb_curve: ReverbCurve object with control points (time, wet_percent)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not reverb_curve or not reverb_curve.has_edits():
                logger.info("No reverb curve edits, skipping reverb curve processing")
                return True
            
            logger.info(f"Applying reverb curve ({len(reverb_curve.control_points)} control points)")
            
            # Import pedalboard
            try:
                from pedalboard import Pedalboard, Reverb
                from pedalboard.io import AudioFile
            except ImportError:
                logger.error("pedalboard not installed! Install with: pip install pedalboard")
                return False
            
            # Load audio
            audio, sr = librosa.load(str(audio_path), sr=None, mono=False)
            if audio.ndim == 1:
                audio = audio[np.newaxis, :]  # Convert mono to 2D array
            
            duration = audio.shape[1] / sr
            
            # Sample the reverb curve
            curve_times = np.array([p.time for p in reverb_curve.control_points])
            curve_wet_percent = np.array([p.wet_percent for p in reverb_curve.control_points])
            
            # Process audio in chunks with varying reverb wet mix
            chunk_size_sec = 0.1  # 100ms chunks
            chunk_size_samples = int(chunk_size_sec * sr)
            num_chunks = int(np.ceil(audio.shape[1] / chunk_size_samples))
            
            processed_audio = np.zeros_like(audio)
            
            for i in range(num_chunks):
                start_sample = i * chunk_size_samples
                end_sample = min((i + 1) * chunk_size_samples, audio.shape[1])
                chunk = audio[:, start_sample:end_sample]
                
                # Get wet percentage at this time point
                chunk_time = start_sample / sr
                
                # Interpolate wet percentage
                from scipy.interpolate import interp1d
                if len(curve_times) == 1:
                    wet_percent = curve_wet_percent[0]
                elif len(curve_times) == 2:
                    # Two points: use linear interpolation
                    interp_func = interp1d(
                        curve_times,
                        curve_wet_percent,
                        kind='linear',
                        bounds_error=False,
                        fill_value=(curve_wet_percent[0], curve_wet_percent[-1])
                    )
                    wet_percent = interp_func(chunk_time)
                else:
                    # 3+ points: use cubic interpolation
                    interp_func = interp1d(
                        curve_times,
                        curve_wet_percent,
                        kind='linear',  # Linear for reverb (simpler transitions)
                        bounds_error=False,
                        fill_value=(curve_wet_percent[0], curve_wet_percent[-1])
                    )
                    wet_percent = float(interp_func(chunk_time))
                
                # Apply reverb with this wet level
                wet_level = wet_percent / 100.0  # Convert 0-100% to 0.0-1.0
                dry_level = 1.0 - wet_level
                
                # Create reverb effect
                board = Pedalboard([
                    Reverb(room_size=0.5, wet_level=wet_level, dry_level=dry_level)
                ])
                
                # Process chunk
                chunk_processed = board(chunk, sr)
                processed_audio[:, start_sample:end_sample] = chunk_processed
            
            # Save output
            output_path.parent.mkdir(parents=True, exist_ok=True)
            if processed_audio.shape[0] == 1:
                sf.write(str(output_path), processed_audio[0], sr)
            else:
                sf.write(str(output_path), processed_audio.T, sr)
            
            logger.info(f"Reverb curve applied, saved to {output_path.name}")
            return True
            
        except Exception as e:
            logger.error(f"Reverb curve application failed for {audio_path}: {e}")
            return False
