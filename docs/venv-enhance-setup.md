# venv-enhance Setup Guide

## What is venv-enhance?

`venv-enhance` is a **separate virtual environment** for [Resemble Enhance](https://github.com/resemble-ai/resemble-enhance), an AI-powered speech denoising and enhancement tool.

It runs in isolation from the main Voice Revolver AI application to avoid dependency conflicts.

---

## Why Separate Environment?

Resemble Enhance has specific requirements that conflict with the main app:

| Dependency | Main App (.venv-1) | Resemble Enhance | Conflict? |
|------------|-------------------|------------------|-----------|
| Python     | 3.11.x            | >=3.10           | ✅ OK     |
| PyTorch    | 2.1.2             | >=2.1.1          | ✅ OK     |
| scipy      | 1.10.0            | >=1.11.4         | ❌ YES    |
| numpy      | <2.0              | >=1.26.2         | ❌ YES    |
| deepspeed  | Not installed     | >=0.12.4         | ⚠️ Windows issues |

**Solution:** Separate venv called via subprocess (like MDX integration)

---

## Installation

### Automatic Setup (Recommended)

Run the batch script:

```powershell
.\setup_venv_enhance.bat
```

This will:
1. Create `venv-enhance` virtual environment
2. Install `resemble-enhance` package
3. Install PyTorch with CUDA (GPU) or CPU support
4. Verify installation

**Estimated time:** 5-10 minutes (depending on internet speed)

---

### Manual Setup (Advanced)

If the batch script fails or you prefer manual control:

```powershell
# 1. Create virtual environment
python -m venv venv-enhance

# 2. Activate it
.\venv-enhance\Scripts\Activate.ps1

# 3. Install resemble-enhance
pip install resemble-enhance --upgrade

# 4a. For GPU (NVIDIA with CUDA 11.8):
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall

# 4b. For CPU only:
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu --force-reinstall

# 5. Verify
python -c "import resemble_enhance; import torch; print('✓ Installation successful')"
```

---

## Troubleshooting

### Issue: "deepspeed installation failed"

**Cause:** deepspeed has poor Windows support

**Solutions:**
1. **Try without deepspeed** (may work for inference only):
   ```powershell
   pip install resemble-enhance --upgrade --no-deps
   pip install torch torchaudio librosa soundfile scipy numpy omegaconf
   ```

2. **Use WSL** (Windows Subsystem for Linux):
   - Install Ubuntu WSL
   - Run installation in Linux environment

3. **Skip enhancement** (optional feature):
   - Don't check "Improve Vocals" checkbox
   - App works fine without enhancement

---

### Issue: "CUDA not available" (GPU mode)

**Check CUDA installation:**
```powershell
python -c "import torch; print(torch.cuda.is_available())"
```

If `False`:
1. Install [CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive)
2. Reinstall PyTorch with CUDA:
   ```powershell
   pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
   ```

**CPU fallback:**
- Enhancement will still work, just slower (~4x realtime vs 0.5x on GPU)

---

### Issue: "venv-enhance not found" when running app

**Cause:** Environment not created or in wrong location

**Solution:**
- Run `setup_venv_enhance.bat` from project root
- Verify folder exists: `F:\dev\Python\voice-revolver-local-ai\venv-enhance\`

---

## How It Works

When you enable "Improve Vocals" in Voice Revolver AI:

1. App separates vocals using Demucs/MDX → `vocals.wav`
2. App calls `resemble_enhance_wrapper.py`
3. Wrapper runs subprocess:
   ```powershell
   .\venv-enhance\Scripts\python.exe -m resemble_enhance.enhancer.inference vocals.wav vocals_enhanced.wav --solver rk4 --nfe 100 --temp 0.33
   ```
4. Enhanced vocals returned to main app → `vocals_enhanced.wav`
5. Spectrum editor loads BOTH original and enhanced
6. User can blend between them using 5th editing mode

---

## Performance

**Processing Times** (RK4, 100 steps):

| Audio Length | GPU (RTX 3060) | CPU (i7-10700) |
|--------------|----------------|----------------|
| 1 minute     | ~30 seconds    | ~4 minutes     |
| 3 minutes    | ~90 seconds    | ~12 minutes    |
| 5 minutes    | ~150 seconds   | ~20 minutes    |

**GPU Recommendation:** NVIDIA GPU with 6GB+ VRAM for best results

---

## Settings

The wrapper uses fixed high-quality settings:

- **Solver:** RK4 (highest quality, slowest)
- **Steps (NFE):** 100 (high quality)
- **Temperature:** 0.33 (recommended balance)
- **Denoise First:** False (vocals already separated)

No UI controls needed - optimized for best results.

---

## Uninstallation

To remove venv-enhance:

```powershell
# Simply delete the folder
Remove-Item -Recurse -Force venv-enhance
```

The main app will detect it's missing and disable the "Improve Vocals" feature.

---

## References

- **Resemble Enhance GitHub:** https://github.com/resemble-ai/resemble-enhance
- **Hugging Face Demo:** https://huggingface.co/spaces/ResembleAI/resemble-enhance
- **Resemble AI Website:** https://www.resemble.ai/enhance/
