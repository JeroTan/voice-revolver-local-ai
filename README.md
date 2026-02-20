# Voice Revolver AI

AI-powered voice replacement for audio/video files with dual-reference support (audio samples + RVC models).

## Quick Start

### Windows (Easy Way)
1. Install dependencies: `pip install -r requirements.txt`
2. Double-click **`run.bat`** or run: `run.bat`

### Manual Way
```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run application
python run.py
```

## Features

- 🎤 **Dual Voice Conversion Modes**:
  - Audio Reference (ChatterBox VC) - Use audio samples
  - Model Reference (RVC/Applio) - Use pre-trained models
  
- 🎵 **Stem Separation** - Isolate vocals from music using Demucs

- 🔀 **Gender-Aware Conversion** - Automatic pitch adaptation for cross-gender voice conversion

- 🎚️ **Audio Mixing** - Seamlessly recombine converted vocals with original instrumentals

## Documentation

- **[Technical Implementation Guide](docs/technical-implementation-guide.md)** - Architecture, setup, troubleshooting
- **[Product Requirements](docs/voice-revolver-ai-prd.md)** - Feature specifications

## Requirements

- Python 3.11.x (recommended)
- Virtual environments: 
  - `.venv` (main application)
  - `venv-rvc` (RVC model support - required)
  - `venv-mdx` (MDX stem separation - optional for best vocal isolation)
- **For GPU acceleration (NVIDIA GPUs)**:
  - CUDA Toolkit 11.8: [Download](https://developer.nvidia.com/cuda-11-8-0-download-archive)
  - After `pip install -r requirements.txt`, run:
    ```powershell
    pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
    pip install nvidia-cudnn-cu11 nvidia-cublas-cu11
    ```
  - Speed improvements: ~10-20x faster (Demucs: 2-5min → 15-30sec, MDX: 30min → 2min)
- See `requirements.txt` for full dependencies
- See **[AGENT_MEMORY.md](AGENT_MEMORY.md)** for detailed GPU setup troubleshooting

## License

MIT
