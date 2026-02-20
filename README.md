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
- Virtual environment: `.venv` (main) + `venv-rvc` (RVC isolation)
- See `requirements.txt` for full dependencies

## License

MIT
