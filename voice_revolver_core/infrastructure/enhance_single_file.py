"""
Helper script to run Resemble Enhance on a single file.
This script is executed in venv-enhance via subprocess.
"""
import sys
import argparse
from pathlib import Path, WindowsPath
import torch
import torchaudio

# WINDOWS FIX: Patch PosixPath to use WindowsPath on Windows
# resemble-enhance has PosixPath hardcoded in YAML files
import pathlib
if sys.platform == "win32":
    pathlib.PosixPath = pathlib.WindowsPath

# CUDA DEVICE FIX: Patch resemble-enhance device mismatch bug
# Bug: abs_max stays on original device while hwav may be on different device
def patch_inference_chunk():
    import resemble_enhance.inference as inf_module
    import torch.nn.functional as F
    
    original_func = inf_module.inference_chunk.__wrapped__
    
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
        
        return hwav
    
    inf_module.inference_chunk = fixed_inference_chunk

patch_inference_chunk()

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
    
    # Move to device
    device = torch.device(args.device if torch.cuda.is_available() else "cpu")
    dwav = dwav.to(device)
    print(f"Using device: {device}", file=sys.stderr)
    print(f"Audio shape: {dwav.shape}, sample rate: {sr}", file=sys.stderr)
    
    # Denoise first if requested
    if args.denoise:
        print("Applying denoising...", file=sys.stderr)
        dwav, new_sr = denoise(dwav, sr, device)
        sr = new_sr
    
    # Enhance
    print(f"Enhancing with solver={args.solver}, nfe={args.nfe}, tau={args.tau}", file=sys.stderr)
    enhanced, new_sr = enhance(dwav, sr, device, nfe=args.nfe, solver=args.solver, tau=args.tau)
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
