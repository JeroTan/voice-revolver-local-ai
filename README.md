# Voice Revolver AI

> **AI-Powered Audio Workstation** for voice cloning, vocal replacement, stem separation, and custom voice model training - 100% local, no cloud required.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)](https://github.com/JeroTan/voice-revolver-local-ai)

**Transform any voice into another** using state-of-the-art AI models, separate audio stems, enhance vocal quality, and train custom voice models - all running locally on your computer.

---

## 📋 Table of Contents

- [What is Voice Revolver AI?](#what-is-voice-revolver-ai)
- [Key Features](#key-features)
- [7 Specialized Workspaces](#7-specialized-workspaces)
- [Installation](#installation)
  - [For Beginners](#for-beginners-recommended)
  - [For Advanced Users](#for-advanced-users)
  - [For Developers](#for-developers)
- [Quick Start Guide](#quick-start-guide)
- [System Requirements](#system-requirements)
- [GPU Acceleration](#gpu-acceleration-optional)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 What is Voice Revolver AI?

Voice Revolver AI is a **comprehensive audio workstation** that uses deep learning to:

- **Replace vocals** in songs with your own voice or any reference voice
- **Clone voices** from audio samples or pre-trained RVC models
- **Separate audio** into individual stems (vocals, drums, bass, instrumental)
- **Enhance audio quality** with AI-powered denoising and effects
- **Train custom voice models** for personalized voice conversion
- **Generate speech** from text with voice cloning (23 languages supported)
- **Merge multiple audio tracks** with professional mixing controls

All processing happens **100% locally** on your computer - no cloud uploads, no API keys required (except optional HuggingFace for advanced TTS).

---

## ✨ Key Features

###  Professional Quality
- **State-of-the-art AI models**: ChatterBox VC, RVC/Applio, Demucs, MDX23C, Resemble Enhance
- **GPU acceleration** - 10-20x faster processing with NVIDIA GPUs
- **Lossless export** - WAV, FLAC support plus MP3, OGG for compression

### 🎨 User-Friendly Interface
- **7 specialized workspaces** for different audio tasks
- **Interactive waveform editor** with visual curve editing
- **Real-time audio preview** - Hear changes before exporting
- **Drag-and-drop** file management (coming soon in v1.3)

### 🛠️ Advanced Controls
- **Fine-tune everything**: pitch, reverb, volume, blend curves
- **RVC model training** - Create your own voice models
- **Batch processing** ready (developer API available)
- **Project files (.vra)** - Save and resume work anytime

---

## 🎛️ 7 Specialized Workspaces

### 1. 🎤 **Vocal Changer** - Replace Vocals in Songs
Transform existing songs by replacing the original vocals with any reference voice.

**Use Cases:**
- Upload your voice and hear yourself sing your favorite songs
- Change gender/accent of vocals
- Restore old recordings with modern voices
- Create personalized voice content

**Features:**
- Dual AI engines: ChatterBox VC (easy) + RVC models (professional)
- Automatic stem separation (Demucs/MDX)
- 5-curve editing: vocal volume, pitch, reverb, blend, instrumental volume
- Gender-aware pitch adaptation
- 6-track preview player

---

### 2. 🎵 **Audio Separation** - Extract Individual Stems
Isolate vocals, drums, bass, and other instruments from any song.

**Use Cases:**
- Create karaoke tracks (extract instrumental)
- Sample individual instruments for remixes
- Remove vocals for background music
- Analyze musical arrangements

**Features:**
- Demucs (4-stem: vocals, drums, bass, other)
- MDX23C (2-stem: vocals, instrumental - faster)
- Per-stem pitch/volume/reverb editing
- Individual export with format conversion
- Waveform visualization

---

### 3. 🗣️ **Text to Speech** - Generate Speech with Voice Cloning
Convert text to natural-sounding speech using AI voice models.

**Use Cases:**
- Audiobook narration
- Voiceovers for videos
- Accessibility (text-to-audio conversion)
- Language learning (pronunciation examples)

**Features:**
- 23 languages supported (MTL engine)
- English high-quality mode (Turbo engine)
- Special tokens: [laugh], [sigh], [pause]
- Voice cloning from audio samples
- Pitch/reverb/volume curve editing

---

### 4. 🎭 **Voice Cloning** - Clone Any Voice
Clone voices using either simple audio samples or professional RVC models.

**Use Cases:**
- Character voices for animations/games
- Personalized virtual assistants
- Voice impersonation for creative projects
- Voice preservation (save loved ones' voices)

**Features:**
- **Audio File mode**: Upload 30-60 seconds of voice → instant cloning (ChatterBox)
- **RVC Model mode**: Use professionally trained models (.zip files)
- 6 RVC parameters: pitch shift, index rate, protection, filter radius, RMS mix, F0 method
- Non-destructive editing (always keep original)
- Export comparison (edited vs original)

---

### 5. ✨ **Voice Enhancement** - AI Audio Quality Improvement
Enhance audio quality with AI-powered denoising and professional effects.

**Use Cases:**
- Clean up podcast recordings
- Remove background noise from vocals
- Improve phone call recordings
- Restore old/damaged audio

**Features:**
- Resemble Enhance AI (denoise + enhance in one step)
- Blend mode: A/B comparison original vs enhanced
- Pedalboard effects: Reverb, Compressor, Limiter, Gain, Chorus, Phaser, Delay
- 8 effect presets: Studio Vocal, Warm & Rich, Bright & Clear, Radio, etc.
- Curve editing: blend → pitch → volume → reverb

---

### 6. 🎚️ **Track Merger** - Merge Multiple Audio Files
Combine unlimited audio tracks into a single mixed output.

**Use Cases:**
- Podcast editing (merge intro + content + outro)
- Music mashups (combine multiple songs)
- Layered sound design
- Audio collage creation

**Features:**
- Up to 999 tracks supported
- Per-track volume control (0-200%)
- Per-track playback with seek slider
- Waveform visualization for each track
- Auto-normalize prevents clipping
- Curve editing on merged output

---

### 7. 🎓 **Audio Training** - Train Custom RVC Voice Models
Train your own RVC voice models from audio samples for highest-quality voice cloning.

**Use Cases:**
- Create professional character voices
- Build custom voice datasets
- Voice preservation projects
- Commercial voice model development

**Features:**
- 4-step pipeline: preprocess → extract → train → index
- Windows single-GPU compatible (RTX 4050 tested)
- Training time: ~2 hours for 200 epochs (17s audio sample)
- Real-time training logs and progress
- Export as .zip for Voice Cloning workspace
- Recommended: 1-5 minutes audio, 200-500 epochs

---

## 📥 Installation

### For Beginners (Recommended)

**Option 1: One-Click Installer** (Coming Soon - v1.3)
- Download `VoiceRevolverAI-Installer.exe`
- Double-click to install
- Launch from desktop shortcut

**Option 2: Simple Setup** (Current - 5 minutes)

1. **Install Python 3.11** from [python.org](https://www.python.org/downloads/)
   - ⚠️ Check "Add Python to PATH" during installation
   - ⚠️ Use Python 3.11.x (not 3.14 - incompatible with GPU acceleration)

2. **Download Voice Revolver AI:**
   - Click the green `Code` button above → `Download ZIP`
   - Extract to `C:\VoiceRevolverAI\` (or any folder)

3. **Install Dependencies:**
   - Open the folder in File Explorer
   - Double-click **`run.bat`** (installs dependencies automatically on first run)

4. **Done!** The app will launch automatically.

---

### For Advanced Users

#### CPU-Only Installation (No GPU)
```powershell
# Clone repository
git clone https://github.com/JeroTan/voice-revolver-local-ai.git
cd voice-revolver-local-ai

# Install CPU-only dependencies
pip install -r requirements.txt

# Run application
python run.py
```

#### GPU-Accelerated Installation (NVIDIA GPUs - 10-20x Faster)
```powershell
# Clone repository
git clone https://github.com/JeroTan/voice-revolver-local-ai.git
cd voice-revolver-local-ai

# Install base dependencies
pip install -r requirements.txt

# Install CUDA-enabled PyTorch (CUDA 11.8)
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall

# Install cuDNN libraries
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11

# Run application
python run.py
```

**Note:** GPU acceleration requires [CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive) installed separately.

#### RVC Environment Setup (Required for Voice Cloning & Audio Training)
```powershell
# Create isolated RVC environment
python -m venv venv-rvc
.\venv-rvc\Scripts\Activate.ps1

# Install Applio dependencies
pip install numpy==2.3.5 scipy==1.16.3 librosa==0.11.0 soundfile==0.12.1
pip install transformers==4.44.2 torchcrepe torchfcpe einops
pip install noisereduce pedalboard soxr stftpitchshift
pip install faiss-cpu==1.13.2  # Or faiss-gpu for faster index search

# Clone Applio RVC module
git clone --depth 1 https://github.com/IAHispano/Applio.git
Copy-Item -Path "Applio\rvc" -Destination "." -Recurse -Force
Remove-Item -Recurse -Force Applio

# Download RMVPE pitch predictor (137MB)
New-Item -ItemType Directory -Path "rvc\models\predictors" -Force
Invoke-WebRequest `
    -Uri "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt" `
    -OutFile "rvc\models\predictors\rmvpe.pt"

# Deactivate and return to main environment
deactivate
```

---

### For Developers

#### Full Development Setup
```powershell
# Clone with full git history
git clone https://github.com/JeroTan/voice-revolver-local-ai.git
cd voice-revolver-local-ai

# Create main virtual environment
python -m venv .venv-1
.\.venv-1\Scripts\Activate.ps1

# Install main dependencies
pip install -r requirements.txt

# For GPU development (NVIDIA GPUs)
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11

# Setup additional virtual environments
python -m venv venv-rvc      # RVC models (see RVC setup above)
python -m venv venv-mdx      # MDX separation (optional)

python -m venv venv-mdx      # MDX separation (optional)
python -m venv venv-enhance  # Resemble Enhance (optional)

# Run development server
python run.py

# Run tests (when available)
python -m pytest tests/
```

**Project Structure:**
```
voice-revolver-local-ai/
├── voice_revolver_core/      # Domain-driven core (DDD architecture)
│   ├── domain/               # Business logic (stem separation, voice conversion)
│   ├── application/          # Use cases (voice replacement service)
│   └── infrastructure/       # External integrations (Demucs, RVC, ChatterBox)
├── voice_revolver_ui/        # User interface (tkinter)
│   ├── features/             # 7 workspaces + dialogs
│   └── components/           # Reusable UI widgets
├── rvc/                      # Applio RVC module (voice training/cloning)
├── docs/                     # Documentation
└── tests/                    # Unit/integration tests
```

See **[AGENT_MEMORY.md](AGENT_MEMORY.md)** for development history and technical lessons learned.

---

## 🚀 Quick Start Guide

### First Launch

1. **Run the application:**
   - Double-click `run.bat` (Windows)
   - Or: `python run.py` in terminal

2. **Choose your device:**
   - **GPU (CUDA)** - For NVIDIA graphics cards (10-20x faster)
   - **CPU** - For any computer (works but slower)

3. **Wait for models to download** (first time only):
   - Demucs models (~350MB)
   - ChatterBox VC models (~200MB)
   - This happens automatically, takes 5-10 minutes

4. **Start using:**
   - Select a workspace from the menu: `Workspace → [Choose Feature]`
   - Load an audio file
   - Process and export!

### Example: Replace Vocals in a Song

1. **Launch** → Select **Vocal Changer** workspace
2. **Load Input**: Click "Browse" → Select your song (MP3/WAV/FLAC)
3. **Load Reference**: Click "Browse Reference" → Select voice sample (30-60 seconds)
4. **Configure**:
   - Separator: Demucs (balanced) or MDX (faster)
   - Reference Mode: Audio File
   - Gender Difference: Auto (or manual -12/+12 semitones)
5. **Process**: Click "Start Processing" → Wait 2-10 minutes
6. **Preview**: Play each track to hear results
7. **Export**: Choose format → Click "Export Final Mix"

### Example: Train a Custom Voice Model

1. **Launch** → Select **Audio Training** workspace
2. **Prepare Audio**: 1-5 minutes of clean voice audio (WAV/MP3)
3. **Configure**:
   - Model Name: `my_voice_model`
   - Epochs: 200-300 (more = better quality)
   - Sample Rate: 40000 Hz (balanced)
   - F0 Method: rmvpe (recommended)
4. **Start Training**: Click "Start Training" → Wait ~2 hours (RTX 4050)
5. **Export Model**: Select checkpoint → Export as .zip
6. **Use in Voice Cloning**: Load the .zip in Voice Cloning workspace!

---

## 💻 System Requirements

### Minimum (CPU Processing)
- **OS**: Windows 10/11 (64-bit)
- **CPU**: Intel Core i5 / AMD Ryzen 5 (4+ cores)
- **RAM**: 8 GB
- **Storage**: 5 GB free space
- **Python**: 3.11.x

**Performance**: 
- Stem separation: 2-5 minutes per song
- Voice conversion: 30-60 seconds per minute of audio
- RVC training: 8-12 hours for 200 epochs (not recommended)

### Recommended (GPU Acceleration)
- **OS**: Windows 10/11 (64-bit)
- **CPU**: Intel Core i7 / AMD Ryzen 7
- **GPU**: NVIDIA RTX 3060 / RTX 4050 or better (6GB+ VRAM)
- **RAM**: 16 GB
- **Storage**: 10 GB free space (models + temp files)
- **Python**: 3.11.x
- **CUDA**: Toolkit 11.8

**Performance**:
- Stem separation: 15-30 seconds per song (10-20x faster!)
- Voice conversion: 3-5 seconds per minute of audio
- RVC training: 2-3 hours for 200 epochs

### Supported File Formats

**Input:**
- Audio: WAV, MP3, FLAC, OGG, M4A
- RVC Models: .zip (containing .pth + .index)
- Projects: .vra (Voice Revolver AI project files)

**Output:**
- Audio: WAV (lossless), MP3 (compressed), FLAC (lossless compressed), OGG (compressed)
- RVC Models: .zip (exportable from Audio Training)

---

## ⚡ GPU Acceleration (Optional)

GPU acceleration provides **10-20x speed improvements** for all AI operations.

### Why GPU?
| Task | CPU Time | GPU Time | Speedup |
|------|----------|----------|---------|
| Demucs Separation (4min song) | 2-5 min | 15-30 sec | **10x** |
| MDX Separation (4min song) | 30 min | 2 min | **15x** |
| Voice Conversion (1min audio) | 30-60 sec | 3-5 sec | **10x** |
| RVC Training (200 epochs) | 10-15 hr | 2-3 hr | **5-7x** |

### Setup Instructions

#### 1. Install CUDA Toolkit 11.8
Download from: [NVIDIA CUDA Toolkit 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive)

- Choose: Windows → x86_64 → 10/11 → exe (local)
- Install all components (drivers, runtime, toolkit)
- Reboot after installation

#### 2. Install PyTorch with CUDA Support
```powershell
# Activate your virtual environment
.\.venv-1\Scripts\Activate.ps1

# Uninstall CPU-only PyTorch
pip uninstall torch torchaudio -y

# Install CUDA-enabled PyTorch
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall

# Install cuDNN libraries
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11
```

#### 3. Verify GPU Detection
```powershell
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

Expected output:
```
CUDA available: True
GPU: NVIDIA GeForce RTX 4050 Laptop GPU
```

If you see `False`, check:
- CUDA Toolkit installed correctly
- NVIDIA drivers up to date
- cuDNN libraries installed (`pip list | grep nvidia`)

See **[Troubleshooting](#troubleshooting)** for common GPU issues.

---

## 📚 Documentation

### For Users
- **[Quick Start Video Tutorial](docs/)** (Coming Soon)
- **[User Guide](docs/voice-revolver-ai-prd.md)** - Feature details and use cases
- **[FAQ](docs/)** (Coming Soon)

### For Developers
- **[Technical Implementation Guide](docs/technical-implementation-guide.md)** - Architecture, DDD patterns, workspace design
- **[AGENT_MEMORY.md](AGENT_MEMORY.md)** - Development history, critical lessons, debugging guides
- **[API Documentation](docs/)** (Coming Soon) - Core API for batch processing

### External Resources
- **RVC Training Guide**: [Applio Documentation](https://github.com/IAHispano/Applio)
- **Demucs Models**: [Facebook Research](https://github.com/facebookresearch/demucs)
- **ChatterBox VC**: [Resemble AI](https://github.com/resemble-ai/chatterbox)

---

## 🔧 Troubleshooting

### Common Issues

#### "Python not found" or "pip not found"
- **Solution**: Install Python 3.11.x from [python.org](https://www.python.org/downloads/)
- During installation, check **"Add Python to PATH"**
- Restart terminal after installation

#### "GPU not detected" or "CUDA not available"
1. **Check GPU compatibility**: Must be NVIDIA GPU (GTX 900 series or newer)
2. **Install CUDA Toolkit**: [CUDA 11.8](https://developer.nvidia.com/cuda-11-8-0-download-archive)
3. **Update NVIDIA drivers**: [GeForce Drivers](https://www.nvidia.com/download/index.aspx)
4. **Reinstall PyTorch with CUDA**:
   ```powershell
   pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall
   pip install nvidia-cudnn-cu11 nvidia-cublas-cu11
   ```

#### "DLL load failed" or "caffe2_nvrtc.dll not found"
- **Cause**: cuDNN libraries missing
- **Solution**: `pip install nvidia-cudnn-cu11 nvidia-cublas-cu11`

#### "Out of memory" during processing
- **For GPU**: Reduce batch size in RVC training, or use CPU mode
- **For CPU**: Close other applications, increase virtual memory, upgrade RAM

#### "ModuleNotFoundError: No module named 'rvc'"
- **Cause**: RVC environment not set up
- **Solution**: Follow [RVC Environment Setup](#rvc-environment-setup-required-for-voice-cloning--audio-training)

#### Models not downloading automatically
- **Check internet connection**
- **Manually download**:
  - Demucs: [Facebook Research](https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/)
  - ChatterBox: Loaded from HuggingFace automatically
- **Place in**: `C:\Users\[YourName]\AppData\Local\VoiceRevolverAI\models\`

#### Slow processing even with GPU
- **Verify GPU is being used**: Check Task Manager → Performance → GPU
- **If GPU shows 0% usage**: Re-install CUDA PyTorch (see GPU section)
- **If GPU shows 100% usage**: This is normal, GPU is working

### Still Having Issues?

1. **Check logs**: `C:\Users\[YourName]\AppData\Local\VoiceRevolverAI\logs\app.log`
2. **Read**: [AGENT_MEMORY.md](AGENT_MEMORY.md) - Critical Lessons Learned section
3. **Open an issue**: [GitHub Issues](https://github.com/JeroTan/voice-revolver-local-ai/issues)
4. **Include**:
   - Error message (full traceback)
   - Python version: `python --version`
   - GPU info: `nvidia-smi` output (if using GPU)
   - OS version

---

## 🤝 Contributing

We welcome contributions! Voice Revolver AI is actively developed and looking for:

### How to Contribute

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Test thoroughly** (add unit tests if possible)
5. **Commit**: `git commit -m "Add amazing feature"`
6. **Push**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Areas We Need Help

- **UI/UX improvements** - Better layouts, dark mode, accessibility
- **Mac/Linux support** - Port to macOS and Linux
- **Portable .exe packaging** - PyInstaller/Nuitka build scripts
- **Documentation** - Tutorials, videos, translations
- **Testing** - Unit tests, integration tests, bug reports
- **New features** - See [Issues](https://github.com/JeroTan/voice-revolver-local-ai/issues) for ideas

### Development Guidelines

- **Follow DDD architecture** - Keep domain logic separate from infrastructure
- **Read AGENT_MEMORY.md** - Learn from past mistakes and critical lessons
- **Test on Windows first** - Primary platform, then Mac/Linux
- **Document everything** - Update docs/ and AGENT_MEMORY.md with changes
- **Zero regressions** - Don't break existing features

---

## 🏗️ Tech Stack & Architecture

### AI Models
- **[Demucs](https://github.com/facebookresearch/demucs)** (v4 Hybrid Transformer) - Stem separation
- **[MDX23C](https://github.com/kuielab/mdx-net)** - Fast vocal separation
- **[ChatterBox VC](https://github.com/resemble-ai/chatterbox)** - Voice conversion
- **[RVC/Applio](https://github.com/IAHispano/Applio)** - Advanced voice conversion with training
- **[Resemble Enhance](https://github.com/resemble-ai/resemble-enhance)** - AI audio enhancement

### Framework & Libraries
- **Python 3.11.x** - Core language
- **PyTorch 2.1.2** - Deep learning framework
- **tkinter** - Native cross-platform GUI
- **pydub** - Audio manipulation and mixing
- **librosa** - Audio analysis and visualization
- **soundfile** - Audio I/O
- **pygame** - Audio playback

### Architecture Pattern
- **Domain-Driven Design (DDD)** - Clean separation of concerns
- **Layers**: Domain → Application → Infrastructure → UI
- **Component-based UI** - Reusable React-like components
- **Workspace pattern** - 7 isolated feature modules

### Why Local-First?
- **No API costs**: Free forever, no subscriptions
- **Offline**: Works without internet after setup
- **Control**: Full ownership of models and data
- **Performance**: GPU acceleration beats cloud latency

---

## 🙏 Acknowledgments

Voice Revolver AI stands on the shoulders of giants. Huge thanks to:

- **[Demucs](https://github.com/facebookresearch/demucs)** by Facebook Research - Revolutionary stem separation
- **[RVC Project](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)** - Voice conversion breakthrough
- **[Applio](https://github.com/IAHispano/Applio)** - Production-ready RVC implementation
- **[ChatterBox](https://github.com/resemble-ai/chatterbox)** by Resemble AI - High-quality voice cloning
- **[PyTorch](https://pytorch.org/)** - Deep learning made accessible
- **Open source community** - For making AI democratized and accessible

### Special Thanks
- **Contributors** who improve this project daily
- **User community** for bug reports and feature requests
- **AI researchers** who publish models openly

---

## 📄 License

This project is licensed under the **MIT License** - see [LICENSE](LICENSE) file for details.

### Third-Party Licenses
- Demucs: MIT License
- RVC/Applio: MIT License
- ChatterBox: MIT License (with Perth watermark)
- PyTorch: BSD License

**Note**: ChatterBox adds an inaudible "Perth" watermark to outputs. This is imperceptible and does not affect quality.

---

## ⭐ Star History

If you find Voice Revolver AI useful, please consider giving it a star! ⭐

Your support helps the project grow and motivates continued development.

---

## 📞 Contact & Support

- **Issues**: [GitHub Issues](https://github.com/JeroTan/voice-revolver-local-ai/issues)
- **Discussions**: [GitHub Discussions](https://github.com/JeroTan/voice-revolver-local-ai/discussions)
- **Email**: (Coming Soon)

<p align="center">
  <sub>📝 This documentation was written by AI (Claude Sonnet 4.6)</sub><br>
  <sub><i>"Automation with Human Touch"</i></sub>
</p>
