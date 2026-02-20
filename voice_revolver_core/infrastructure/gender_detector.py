"""Gender detection module using F0 (pitch) analysis.

This module analyzes the fundamental frequency (F0) of audio files to determine
the speaker's gender and calculate appropriate pitch shift values for cross-gender
voice conversion.

Gender Classification Based on Average F0:
- Male: 85-180 Hz (typical average ~120 Hz)
- Female: 165-255 Hz (typical average ~220 Hz)
- Ambiguous: 160-190 Hz overlap zone

Pitch Shift Recommendations (Adaptive):
- Analyzes actual voice pitch (F0) and calculates minimum shift needed
- Male → Female: 0-5 semitones (adapts based on how high/low the male voice is)
- Female → Male: 0-5 semitones (adapts based on how high/low the female voice is)
- Same gender: 0 semitones (no shift)
- Maximum capped at ±5 semitones to preserve audio quality
"""

import logging
from pathlib import Path
from typing import Literal, Tuple
import parselmouth
import numpy as np

logger = logging.getLogger(__name__)


class GenderDetector:
    """Detects speaker gender from audio using pitch analysis."""
    
    # F0 thresholds in Hz
    MALE_F0_MAX = 180  # Hz
    FEMALE_F0_MIN = 165  # Hz
    AMBIGUOUS_LOWER = 155  # Hz - below this is definitely male
    AMBIGUOUS_UPPER = 220  # Hz - above this is definitely female (raised from 190 to avoid misclassifying tenor males)
    
    # Pitch shift values in semitones
    MALE_TO_FEMALE_SHIFT = 5  # semitones (natural pitch raise)
    FEMALE_TO_MALE_SHIFT = -5  # semitones (natural pitch lower)
    
    # Target F0 values for pitch shifting (conservative middle values)
    TARGET_MALE_F0 = 130  # Hz - typical male speaking voice
    TARGET_FEMALE_F0 = 210  # Hz - typical female speaking voice
    
    def __init__(self):
        """Initialize the gender detector."""
        pass
    
    def detect_gender(self, audio_path: Path) -> Literal["male", "female", "unknown"]:
        """
        Detect speaker gender from audio file using F0 analysis.
        
        Args:
            audio_path: Path to audio file (WAV format preferred)
            
        Returns:
            "male", "female", or "unknown" if detection fails or ambiguous
        """
        try:
            # Load audio with Praat via parselmouth
            sound = parselmouth.Sound(str(audio_path))
            
            # Extract pitch using autocorrelation method
            # Use pitch_ceiling=400Hz for speech (prevents locking onto high harmonics)
            pitch = sound.to_pitch(time_step=0.01, pitch_floor=75.0, pitch_ceiling=400.0)
            
            # Get F0 values over time (NaN for unvoiced segments)
            f0_values = pitch.selected_array['frequency']
            
            # Filter out unvoiced frames (0 or NaN values)
            voiced_f0 = f0_values[(f0_values > 0) & (~np.isnan(f0_values))]
            
            if len(voiced_f0) == 0:
                logger.warning(f"No voiced segments found in {audio_path.name}")
                return "unknown"
            
            # Calculate median F0 (more robust than mean against outliers)
            median_f0 = np.median(voiced_f0)
            mean_f0 = np.mean(voiced_f0)
            p10_f0 = np.percentile(voiced_f0, 10)  # 10th percentile (lower range)
            
            # Octave error correction: Check if lower percentile suggests octave error
            # If 10th percentile is < 140Hz (male range) but median is > 200Hz, likely octave jumps
            if median_f0 > 200 and p10_f0 < 140:
                logger.warning(f"Octave error suspected: p10={p10_f0:.1f}Hz (male), median={median_f0:.1f}Hz (female)")
                logger.warning(f"Correcting: using lower percentile as reference")
                median_f0 = p10_f0  # Use lower percentile instead
                mean_f0 = np.percentile(voiced_f0, 50)  # Use 50th percentile
            
            logger.info(f"F0 analysis for {audio_path.name}: median={median_f0:.1f}Hz, mean={mean_f0:.1f}Hz")
            
            # Gender classification based on median F0
            if median_f0 < self.AMBIGUOUS_LOWER:
                return "male"
            elif median_f0 > self.AMBIGUOUS_UPPER:
                return "female"
            else:
                # Ambiguous zone - use mean as tiebreaker
                logger.warning(f"Ambiguous F0 range ({median_f0:.1f}Hz) for {audio_path.name}")
                if mean_f0 < 175:
                    logger.info("Classified as male based on mean F0")
                    return "male"
                else:
                    logger.info("Classified as female based on mean F0")
                    return "female"
                    
        except Exception as e:
            logger.error(f"Failed to detect gender for {audio_path}: {e}")
            return "unknown"
    
    def calculate_pitch_shift(
        self,
        original_audio: Path,
        reference_audio: Path
    ) -> Tuple[int, str]:
        """
        Calculate recommended pitch shift for voice conversion using adaptive algorithm.
        
        Detects gender and actual F0 of both voices, then calculates the minimum
        pitch shift needed to match target gender range. Avoids excessive shifting
        when the original voice is already close to the target range.
        
        Args:
            original_audio: Path to original vocal track (source)
            reference_audio: Path to reference voice (target)
            
        Returns:
            Tuple of (pitch_shift_semitones, explanation_string)
            
        Examples:
            >>> detector.calculate_pitch_shift(male_audio, female_audio)
            (3, "Male (145Hz) -> Female (210Hz): +3 semitones")
        """
        original_gender = self.detect_gender(original_audio)
        reference_gender = self.detect_gender(reference_audio)
        
        logger.info(f"Gender detection - Original: {original_gender}, Reference: {reference_gender}")
        
        # Handle unknown/detection failures
        if original_gender == "unknown" or reference_gender == "unknown":
            logger.warning("Gender detection failed, defaulting to no pitch shift")
            return 0, "Gender detection failed: no pitch shift applied"
        
        # Same gender - no pitch shift needed
        if original_gender == reference_gender:
            shift = 0
            explanation = f"Same gender ({original_gender}): no pitch shift needed"
            logger.info(explanation)
            return shift, explanation
        
        # Get actual F0 values for adaptive shifting
        original_stats = self.get_f0_statistics(original_audio)
        if "error" in original_stats:
            logger.warning(f"Could not get F0 stats, using default shift")
            shift = self.MALE_TO_FEMALE_SHIFT if original_gender == "male" else self.FEMALE_TO_MALE_SHIFT
            explanation = f"{original_gender.capitalize()} -> {reference_gender.capitalize()}: {shift:+d} semitones (default)"
            return shift, explanation
        
        original_f0 = original_stats["median_f0"]
        
        # Calculate adaptive pitch shift based on actual F0 and target gender
        if original_gender == "male" and reference_gender == "female":
            # Male to Female: shift up toward female range
            target_f0 = self.TARGET_FEMALE_F0
            calculated_shift = 12 * np.log2(target_f0 / original_f0)
            
            # Cap the shift at maximum 5 semitones to avoid overkill
            shift = int(np.clip(np.round(calculated_shift), 0, 5))
            explanation = f"Male ({original_f0:.0f}Hz) -> Female target ({target_f0}Hz): {shift:+d} semitones"
            
        elif original_gender == "female" and reference_gender == "male":
            # Female to Male: shift down toward male range
            target_f0 = self.TARGET_MALE_F0
            calculated_shift = 12 * np.log2(target_f0 / original_f0)
            
            # Cap the shift at maximum -5 semitones to avoid overkill
            shift = int(np.clip(np.round(calculated_shift), -5, 0))
            explanation = f"Female ({original_f0:.0f}Hz) -> Male target ({target_f0}Hz): {shift:+d} semitones"
        
        else:
            # Fallback (shouldn't reach here)
            shift = 0
            explanation = f"No shift needed"
        
        logger.info(explanation)
        return shift, explanation
    
    def get_f0_statistics(self, audio_path: Path) -> dict:
        """
        Get detailed F0 statistics for an audio file.
        
        Useful for debugging and advanced pitch analysis.
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            Dictionary with F0 statistics (mean, median, min, max, std)
        """
        try:
            sound = parselmouth.Sound(str(audio_path))
            pitch = sound.to_pitch(time_step=0.01, pitch_floor=75.0, pitch_ceiling=400.0)
            f0_values = pitch.selected_array['frequency']
            voiced_f0 = f0_values[(f0_values > 0) & (~np.isnan(f0_values))]
            
            if len(voiced_f0) == 0:
                return {"error": "No voiced segments found"}
            
            return {
                "mean_f0": float(np.mean(voiced_f0)),
                "median_f0": float(np.median(voiced_f0)),
                "min_f0": float(np.min(voiced_f0)),
                "max_f0": float(np.max(voiced_f0)),
                "std_f0": float(np.std(voiced_f0)),
                "num_voiced_frames": len(voiced_f0),
                "classified_gender": self.detect_gender(audio_path)
            }
            
        except Exception as e:
            logger.error(f"Failed to get F0 statistics: {e}")
            return {"error": str(e)}
