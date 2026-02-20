"""
MDX Standalone - Subprocess Script
Runs in isolated venv-mdx environment to avoid dependency conflicts
"""

import sys
import json
import logging
from pathlib import Path

# Configure logging to stderr
logging.basicConfig(
    level=logging.INFO,
    format='[MDX] %(message)s',
    stream=sys.stderr
)


def separate_audio(audio_path: str, output_dir: str, model_name: str = "MDX23C-8KFFT-InstVoc_HQ.ckpt", device: str = "cpu"):
    """
    Separate audio using MDX model in isolated environment.
    
    Args:
        audio_path: Path to input audio file
        output_dir: Directory to save separated stems
        model_name: MDX model checkpoint name
        device: Compute device ('cpu' or 'cuda')
    
    Returns:
        JSON with {success, vocals_path, instrumental_path, error}
    """
    try:
        import os
        
        # CRITICAL: Configure static-ffmpeg BEFORE importing Separator
        # (Separator checks for ffmpeg during __init__)
        try:
            from static_ffmpeg import run
            ffmpeg_path, ffprobe_path = run.get_or_fetch_platform_executables_else_raise()
            # Add FFmpeg to PATH
            ffmpeg_dir = str(Path(ffmpeg_path).parent)
            os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
            print(f"[MDX] FFmpeg configured: {ffmpeg_path}", file=sys.stderr, flush=True)
        except Exception as e:
            print(f"[MDX] Error configuring FFmpeg: {e}", file=sys.stderr, flush=True)
            raise RuntimeError("FFmpeg not available") from e
        
        # Now import Separator (will find ffmpeg in PATH)
        from audio_separator.separator import Separator
        
        print(f"[MDX] Processing audio: {audio_path}", file=sys.stderr, flush=True)
        print(f"[MDX] Output directory: {output_dir}", file=sys.stderr, flush=True)
        print(f"[MDX] Model: {model_name}", file=sys.stderr, flush=True)
        print(f"[MDX] Device: {device}", file=sys.stderr, flush=True)
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Progress callback to show what's happening
        def log_progress(message, progress=None):
            if progress is not None:
                print(f"[MDX] Progress: {progress}% - {message}", file=sys.stderr, flush=True)
            else:
                print(f"[MDX] {message}", file=sys.stderr, flush=True)
        
        # Initialize separator (auto-detects device from torch.cuda.is_available())
        separator = Separator(
            model_file_dir=Path.home() / '.audio-separator' / 'models',
            output_dir=output_dir,
            output_format='wav',
            normalization_threshold=0.9,
            invert_using_spec=True,
            sample_rate=44100,
            log_level=logging.INFO
        )
        
        # Load model
        print(f"[MDX] Loading model: {model_name}", file=sys.stderr)
        separator.load_model(model_filename=model_name)
        
        # Separate
        print(f"[MDX] Separating stems...", file=sys.stderr)
        output_files = separator.separate(audio_path)
        
        # MDX returns 2 files: (Vocals) and (Instrumental)
        vocals_path = None
        instrumental_path = None
        
        for file_path in output_files:
            if '(Vocals)' in file_path or 'vocals' in file_path.lower():
                vocals_path = file_path
            elif '(Instrumental)' in file_path or 'instrumental' in file_path.lower():
                instrumental_path = file_path
        
        if not vocals_path:
            raise RuntimeError("MDX separation did not produce vocals file")
        
        print(f"[MDX] Separation complete!", file=sys.stderr)
        print(f"[MDX] Vocals: {vocals_path}", file=sys.stderr)
        print(f"[MDX] Instrumental: {instrumental_path}", file=sys.stderr)
        
        # Return result as JSON
        result = {
            "success": True,
            "vocals_path": vocals_path,
            "instrumental_path": instrumental_path or "",
            "error": None
        }
        
        print(json.dumps(result))
        return 0
        
    except Exception as e:
        import traceback
        error_msg = f"MDX separation failed: {str(e)}\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        
        result = {
            "success": False,
            "vocals_path": None,
            "instrumental_path": None,
            "error": str(e)
        }
        
        print(json.dumps(result))
        return 1


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mdx_standalone.py <audio_path> <output_dir> [model_name] [device]", file=sys.stderr)
        sys.exit(1)
    
    audio_path = sys.argv[1]
    output_dir = sys.argv[2]
    model_name = sys.argv[3] if len(sys.argv) > 3 else "MDX23C-8KFFT-InstVoc_HQ.ckpt"
    device = sys.argv[4] if len(sys.argv) > 4 else "cpu"
    
    exit_code = separate_audio(audio_path, output_dir, model_name, device)
    sys.exit(exit_code)
