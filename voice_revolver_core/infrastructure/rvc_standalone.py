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


def run_rvc_inference(model_path, index_path, input_audio, output_audio, f0_method="rmvpe", f0_up_key=0):
    """
    Perform voice conversion using Applio's RVC implementation.
    
    Args:
        model_path: Path to .pth model file
        index_path: Path to .index file
        input_audio: Path to input audio file
        output_audio: Path to output audio file
        f0_method: F0 extraction method (e.g., "rmvpe", "crepe", "fcpe")
        f0_up_key: Pitch shift in semitones
    """
    try:
        print(f"[RVC] Processing audio: {input_audio}")
        print(f"[RVC] Model: {model_path}")
        print(f"[RVC] Index: {index_path}")
        print(f"[RVC] Pitch shift: {f0_up_key} semitones")
        print(f"[RVC] F0 method: {f0_method}")
        
        # Initialize Applio's VoiceConverter
        converter = VoiceConverter()
        
        # Perform conversion using Applio's API
        converter.convert_audio(
            audio_input_path=input_audio,
            audio_output_path=output_audio,
            model_path=model_path,
            index_path=index_path,
            pitch=f0_up_key,
            f0_method=f0_method,
            index_rate=0.75,
            volume_envelope=0.25,
            protect=0.33,
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
        print("Usage: python rvc_standalone.py <model.pth> <model.index> <input.wav> <output.wav> [f0_method] [f0_up_key]")
        sys.exit(1)
    
    model_path = sys.argv[1]
    index_path = sys.argv[2]
    input_audio = sys.argv[3]
    output_audio = sys.argv[4]
    f0_method = sys.argv[5] if len(sys.argv) > 5 else "rmvpe"
    f0_up_key = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    
    sys.exit(run_rvc_inference(model_path, index_path, input_audio, output_audio, f0_method, f0_up_key))
