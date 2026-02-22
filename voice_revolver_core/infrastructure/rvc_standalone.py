#!/usr/bin/env python3
"""
Standalone RVC inference script using Applio's VoiceConverter.
This script is called via subprocess from the main application.
"""

import sys
import os
from pathlib import Path

# Add project root to path to find rvc module
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Applio's VoiceConverter
from rvc.infer.infer import VoiceConverter


def run_rvc_inference(
    model_path, 
    index_path, 
    input_audio, 
    output_audio, 
    f0_method="rmvpe", 
    f0_up_key=0,
     index_rate=0.5,      # DEFAULT: 0.75 (Balanced timbre - decrease to 0.5-0.6 for more natural, increase to 0.9 for more precise)
    filter_radius=2,      # DEFAULT: 3 (Natural pitch - decrease to 2 for more vibrato, increase to 5-7 for smoother/robotic)
    resample_sr=0,        # DEFAULT: 0 (Auto from model - set to 40000/48000 for custom sample rate)
    rms_mix_rate=0.15,    # DEFAULT: 0.25 (Slight dynamics preservation - decrease to 0.15 for more expression, increase to 0.5 for flatter)
    protect=0.2          # DEFAULT: 0.33 (Balanced consonants - decrease to 0.2 for smoother, increase to 0.4 for crisper)
):
    """
    Perform voice conversion using Applio's RVC implementation.
    
    Args:
        model_path: Path to .pth model file
        index_path: Path to .index file
        input_audio: Path to input audio file
        output_audio: Path to output audio file
        f0_method: F0 extraction method (e.g., "rmvpe", "crepe", "fcpe")
        f0_up_key: Pitch shift in semitones
        index_rate: Index influence strength (0.0-1.0)
                   DEFAULT: 0.75 - Balanced timbre match
                   NATURAL: 0.5-0.6 - More organic, less precise
                   PRECISE: 0.9-1.0 - Perfect match but can sound robotic
        filter_radius: Median filter for pitch curve (0-7)
                      DEFAULT: 3 - Natural with slight smoothing
                      VIBRATO: 2 - Preserves natural pitch wobbles
                      SMOOTH: 5-7 - Auto-tune effect, removes vibrato
        resample_sr: Output sample rate (0=auto from model)
                    DEFAULT: 0 - Use model's native sample rate
                    CUSTOM: 40000/48000 - Force specific sample rate
        rms_mix_rate: Volume envelope mixing (0.0-1.0)
                     DEFAULT: 0.25 - 75% converted + 25% source dynamics
                     EXPRESSIVE: 0.15 - More converted voice dynamics
                     STABLE: 0.3-0.5 - More source voice volume
        protect: Protect voiceless consonants (0.0-0.5)
                DEFAULT: 0.33 - Balanced consonant clarity
                SMOOTH: 0.2 - Less protection, more cohesive
                CRISP: 0.4-0.5 - Sharper "s", "t", "k" sounds
    """
    try:
        print(f"[RVC] Processing audio: {input_audio}")
        print(f"[RVC] Model: {model_path}")
        print(f"[RVC] Index: {index_path}")
        print(f"[RVC] Pitch shift: {f0_up_key} semitones")
        print(f"[RVC] F0 method: {f0_method}")
        print(f"[RVC] Advanced parameters:")
        print(f"  - Index rate: {index_rate} (feature retrieval strength)")
        print(f"  - Filter radius: {filter_radius} (pitch smoothing)")
        print(f"  - Resample SR: {resample_sr} (output sample rate)")
        print(f"  - RMS mix rate: {rms_mix_rate} (volume envelope)")
        print(f"  - Protect: {protect} (consonant protection)")
        
        # Initialize Applio's VoiceConverter
        converter = VoiceConverter()
        
        # Perform conversion using Applio's API with all advanced parameters
        converter.convert_audio(
            audio_input_path=input_audio,
            audio_output_path=output_audio,
            model_path=model_path,
            index_path=index_path,
            pitch=f0_up_key,
            f0_method=f0_method,
            index_rate=index_rate,                    # Use provided index_rate
            filter_radius=filter_radius,              # Use provided filter_radius
            volume_envelope=rms_mix_rate,             # Use provided rms_mix_rate
            protect=protect,                          # Use provided protect
            hop_length=128,
            split_audio=False,  # Don't split short audio clips
            f0_autotune=False,
            clean_audio=False,
            export_format="WAV",
            embedder_model="contentvec",  # Default Applio embedder
            embedder_model_custom=None,
            sid=0,
            proposed_pitch=False,
            proposed_pitch_threshold=155.0,
        )
        
        print(f"[RVC] Conversion completed: {output_audio}")
        return 0
        
    except Exception as e:
        print(f"[RVC ERROR] Conversion failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python rvc_standalone.py <model.pth> <model.index> <input.wav> <output.wav> [f0_method] [f0_up_key] [index_rate] [filter_radius] [resample_sr] [rms_mix_rate] [protect]")
        sys.exit(1)
    
    model_path = sys.argv[1]
    index_path = sys.argv[2]
    input_audio = sys.argv[3]
    output_audio = sys.argv[4]
    f0_method = sys.argv[5] if len(sys.argv) > 5 else "rmvpe"
    f0_up_key = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    
    # Advanced parameters (with defaults)
    index_rate = float(sys.argv[7]) if len(sys.argv) > 7 else 0.75
    filter_radius = int(sys.argv[8]) if len(sys.argv) > 8 else 3
    resample_sr = int(sys.argv[9]) if len(sys.argv) > 9 else 0
    rms_mix_rate = float(sys.argv[10]) if len(sys.argv) > 10 else 0.25
    protect = float(sys.argv[11]) if len(sys.argv) > 11 else 0.33
    
    sys.exit(run_rvc_inference(
        model_path, 
        index_path, 
        input_audio, 
        output_audio, 
        f0_method, 
        f0_up_key,
        index_rate,
        filter_radius,
        resample_sr,
        rms_mix_rate,
        protect
    ))
