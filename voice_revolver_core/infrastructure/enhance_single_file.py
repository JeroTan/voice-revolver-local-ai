"""
Helper script to run Resemble Enhance on a single file.
This script is executed in venv-enhance via subprocess.

Includes patches for:
- Windows PosixPath bug in resemble-enhance YAML files
- CUDA device mismatch bug in inference_chunk
- Smaller chunk size (5s) for long audio GPU memory stability
- Aggressive GPU memory cleanup between chunks
"""
import gc
import sys
import argparse
from pathlib import Path, WindowsPath
import torch
import torch.nn.functional as F
import torchaudio

# WINDOWS FIX: Patch PosixPath to use WindowsPath on Windows
# resemble-enhance has PosixPath hardcoded in YAML files
import pathlib
if sys.platform == "win32":
    pathlib.PosixPath = pathlib.WindowsPath

# ============================================================================
# PATCH 1: Fix inference_chunk - device mismatch + memory cleanup
# ============================================================================
def patch_inference_chunk():
    """Fix device mismatch bug and add GPU memory cleanup per chunk."""
    import resemble_enhance.inference as inf_module
    
    @torch.inference_mode()
    def fixed_inference_chunk(model, dwav, sr, device, npad=441):
        assert model.hp.wav_rate == sr, f"Expected {model.hp.wav_rate} Hz, got {sr} Hz"
        
        length = dwav.shape[-1]
        abs_max = dwav.abs().max().clamp(min=1e-7)
        
        assert dwav.dim() == 1, f"Expected 1D waveform, got {dwav.dim()}D"
        dwav = dwav.to(device)
        dwav = dwav / abs_max.to(device)  # FIX: Move abs_max to same device
        dwav = F.pad(dwav, (0, npad))
        hwav = model(dwav[None])[0].cpu()
        hwav = hwav[:length]
        hwav = hwav * abs_max.to(hwav.device)  # FIX: Ensure same device
        
        # Aggressive memory cleanup after each chunk
        del dwav
        gc.collect()
        if str(device) == "cuda" or (hasattr(device, 'type') and device.type == "cuda"):
            torch.cuda.empty_cache()
        
        return hwav
    
    inf_module.inference_chunk = fixed_inference_chunk

# ============================================================================
# PATCH 2: Override inference() to use smaller chunks for long audio
# ============================================================================
def patch_inference_for_long_audio():
    """Replace default inference with smaller chunk processing (5s chunks).
    
    The default resemble-enhance uses ~10s chunks which can exhaust GPU memory
    on longer audio (5+ minutes). This patch reduces to 5s chunks with 1s overlap
    and crossfade stitching for seamless output.
    """
    import resemble_enhance.inference as inf_module
    
    # Save reference to the (already patched) chunk function
    patched_chunk_fn = inf_module.inference_chunk
    
    @torch.inference_mode()
    def small_chunk_inference(model, dwav, sr, device, chunk_seconds=5.0, overlap_seconds=1.0):
        """Process audio in small chunks with overlap and crossfade."""
        from tqdm import tqdm
        
        chunk_length = int(sr * chunk_seconds)
        overlap_length = int(sr * overlap_seconds)
        hop_length = chunk_length - overlap_length
        
        total_length = dwav.shape[-1]
        
        # Short audio: process in one go
        if total_length <= chunk_length:
            return patched_chunk_fn(model, dwav, sr, device), model.hp.wav_rate
        
        # Long audio: process in smaller chunks with crossfade
        print(f"Long audio detected ({total_length / sr:.1f}s), using {chunk_seconds}s chunks with {overlap_seconds}s overlap", file=sys.stderr)
        
        chunks = []
        starts = list(range(0, total_length, hop_length))
        
        for i, start in enumerate(tqdm(starts, desc="Enhancing chunks", file=sys.stderr)):
            end = min(start + chunk_length, total_length)
            chunk = dwav[start:end]
            
            # Pad last chunk if shorter than chunk_length
            actual_len = chunk.shape[-1]
            if actual_len < chunk_length:
                chunk = F.pad(chunk, (0, chunk_length - actual_len))
            
            processed = patched_chunk_fn(model, chunk, sr, device)
            
            # Trim padding from last chunk
            if actual_len < chunk_length:
                processed = processed[:actual_len]
            
            chunks.append(processed)
            
            # Memory cleanup between chunks
            gc.collect()
            if str(device) == "cuda" or (hasattr(device, 'type') and device.type == "cuda"):
                torch.cuda.empty_cache()
        
        # Crossfade overlapping regions for seamless stitching
        output = torch.zeros(total_length)
        weight = torch.zeros(total_length)
        
        for i, (start, chunk) in enumerate(zip(starts, chunks)):
            end = min(start + chunk.shape[-1], total_length)
            actual_len = end - start
            
            # Create fade window for crossfading
            fade = torch.ones(actual_len)
            if i > 0 and overlap_length > 0:
                fade_in_len = min(overlap_length, actual_len)
                fade[:fade_in_len] = torch.linspace(0, 1, fade_in_len)
            if i < len(starts) - 1 and overlap_length > 0:
                fade_out_len = min(overlap_length, actual_len)
                fade[-fade_out_len:] = torch.linspace(1, 0, fade_out_len)
            
            output[start:end] += chunk[:actual_len] * fade
            weight[start:end] += fade
        
        # Normalize by accumulated weight
        weight = weight.clamp(min=1e-8)
        output = output / weight
        
        return output, model.hp.wav_rate
    
    inf_module.inference = small_chunk_inference


# Apply all patches before importing enhance/denoise
patch_inference_chunk()
patch_inference_for_long_audio()

# Now import after patching
from resemble_enhance.enhancer.inference import enhance, denoise


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=str, help="Input audio file")
    parser.add_argument("output", type=str, help="Output audio file")
    parser.add_argument("--solver", type=str, default="midpoint", help="Solver: euler, midpoint, rk4")
    parser.add_argument("--nfe", type=int, default=64, help="Number of function evaluations")
    parser.add_argument("--tau", type=float, default=0.5, help="CFM prior temperature")
    parser.add_argument("--denoise", action="store_true", help="Denoise first")
    parser.add_argument("--device", type=str, default="cuda", help="Device: cuda or cpu")
    
    args = parser.parse_args()
    
    # Load audio
    print(f"Loading audio: {args.input}", file=sys.stderr)
    dwav, sr = torchaudio.load(args.input)
    dwav = dwav.mean(dim=0)  # Convert to mono if stereo
    
    # Store original sample rate for final output
    original_sr = sr
    
    # Move to device
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    dwav = dwav.to(device)
    print(f"Using device: {device}", file=sys.stderr)
    print(f"Audio shape: {dwav.shape}, sample rate: {sr}", file=sys.stderr)
    
    # Clear GPU memory before starting enhancement
    if device.type == "cuda":
        gc.collect()
        torch.cuda.empty_cache()
        free_mem = torch.cuda.mem_get_info()[0] / 1024**2
        total_mem = torch.cuda.mem_get_info()[1] / 1024**2
        print(f"GPU memory: {free_mem:.0f}MB free / {total_mem:.0f}MB total", file=sys.stderr)
    
    # Denoise first if requested
    if args.denoise:
        print("Applying denoising...", file=sys.stderr)
        dwav, new_sr = denoise(dwav, sr, device)
        sr = new_sr
    
    # Enhance
    print(f"Enhancing with solver={args.solver}, nfe={args.nfe}, tau={args.tau}", file=sys.stderr)
    enhanced, new_sr = enhance(dwav, sr, device, nfe=args.nfe, solver=args.solver, tau=args.tau)
    
    # Resample back to original sample rate if model changed it
    if new_sr != original_sr:
        print(f"Resampling from {new_sr}Hz back to {original_sr}Hz", file=sys.stderr)
        enhanced = torchaudio.functional.resample(enhanced, orig_freq=new_sr, new_freq=original_sr)
        sr = original_sr
    else:
        sr = new_sr
    
    # Save output
    print(f"Saving enhanced audio: {args.output}", file=sys.stderr)
    enhanced = enhanced.unsqueeze(0).cpu()  # Add channel dimension and move to CPU
    torchaudio.save(args.output, enhanced, sr)
    
    print(f"Enhancement complete! Saved to {args.output}", file=sys.stderr)
    print("SUCCESS", file=sys.stdout)  # Signal success to wrapper


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
