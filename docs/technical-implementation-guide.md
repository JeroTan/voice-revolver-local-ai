# Technical Implementation Guide

**Voice Revolver AI - Technical Architecture & Implementation Details**

This document serves as a technical reference for architecture decisions, library choices, and solutions implemented. Use this as a blueprint for similar projects.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Architecture Patterns](#architecture-patterns)
4. [Key Technical Challenges & Solutions](#key-technical-challenges--solutions)
5. [Dual-Environment Strategy](#dual-environment-strategy)
6. [Library Integration Details](#library-integration-details)
7. [Critical Implementation Notes](#critical-implementation-notes)
8. [Performance Considerations](#performance-considerations)
9. [Future Project Guidelines](#future-project-guidelines)

---

## Project Overview

**Voice Revolver AI** is a desktop application for AI-powered voice replacement in audio/video files. It uses:
- **Stem separation**: Isolate vocals from music/background
- **Voice conversion**: Transform vocals using either audio samples (ChatterBox) or trained models (RVC)
- **Audio mixing**: Recombine converted vocals with original instrumentals

**Core Innovation**: Dual-reference voice conversion system supporting both audio-based (ChatterBox) and model-based (RVC) approaches in a single application.

---

## Technology Stack

### Core Languages & Frameworks
- **Python 3.11.9**: Primary language
- **Tkinter**: Native cross-platform GUI (no external dependencies)
- **PyTorch 2.10.0**: Deep learning framework (CPU-optimized build)

### Audio Processing
| Library | Version | Purpose | Key Notes |
|---------|---------|---------|-----------|
| **librosa** | 0.11.0 | Audio I/O, feature extraction | Industry-standard for audio ML |
| **soundfile** | 0.12.1 | High-quality audio file I/O | Better than scipy.io.wavfile |
| **pydub** | 0.25.1 | Audio format conversion, slicing | Wrapper around ffmpeg |
| **ffmpeg** | Latest | Codec support, format conversion | External binary, bundled via ffmpeg-python |

### Voice Conversion Engines

#### ChatterBox VC (Audio Reference)
```python
# Primary environment (.venv)
chatterbox-vc==0.1.6
numpy==1.25.2  # Required by ChatterBox
torch==2.10.0+cpu
torchaudio==2.10.0+cpu
```

**Why ChatterBox?**
- Zero-shot voice conversion (no training required)
- Accepts audio samples as voice reference
- Lightweight, fast inference
- Python 3.11 compatible

#### Applio RVC (Model Reference)
```python
# Isolated environment (venv-rvc)
numpy==2.3.5  # Newer version required by Applio
scipy==1.16.3
librosa==0.11.0
soundfile==0.12.1
transformers==4.44.2
faiss-cpu==1.13.2
omegaconf>=2.0.6
torchfcpe  # F0 (pitch) extraction
torchcrepe
einops
pedalboard  # Audio effects processing
```

**Why Applio?**
- Active maintenance (updated Feb 2026)
- NO fairseq dependency (avoids Python 3.11 incompatibilities)
- Clean API for RVC inference
- Supports multiple F0 extractors (rmvpe, crepe, fcpe)
- Modern dependency stack

**Why NOT rvc-python 0.1.5?**
❌ Depends on fairseq 0.12.2 (has Python 3.11 dataclass bugs)
❌ Incompatible omegaconf version conflicts
❌ Abandoned (last update 2022)

### Stem Separation
```python
demucs==4.1.0a3  # State-of-the-art source separation
```

**Model Used**: `htdemucs_ft` (fine-tuned hybrid transformer + demucs)
- 4-stem separation: vocals, drums, bass, other
- GPU/CPU adaptive
- ~200MB model download on first use

### GUI Framework
```python
tkinter  # Built-in to Python
pillow==12.0.0  # Image loading for UI assets
```

**Why Tkinter?**
✅ Native to Python (no installation needed)
✅ Cross-platform (Windows, macOS, Linux)
✅ Lightweight (~3MB)
✅ Mature, stable API
❌ Limited styling options (acceptable for utility apps)

---

## Architecture Patterns

### 1. **Hexagonal Architecture (Ports & Adapters)**

```
voice_revolver_core/
├── domain/              # Core business logic (NO external dependencies)
│   ├── voice_converter.py        # Abstract interfaces
│   ├── stem_separator.py
│   ├── audio_mixer.py
│   └── format_converter.py
│
├── application/         # Use cases, orchestration
│   ├── voice_replacement_service.py  # Main processing pipeline
│   └── project_service.py
│
└── infrastructure/      # External integrations (adapters)
    ├── chatterbox_wrapper.py     # ChatterBox implementation
    ├── rvc_wrapper.py            # RVC subprocess implementation
    ├── demucs_wrapper.py         # Demucs implementation
    ├── openvoice_wrapper.py      # (Future: OpenVoice support)
    └── model_manager.py          # Model lifecycle management
```

**Benefits**:
- Testable core logic without external dependencies
- Easy to swap implementations (e.g., replace Demucs with Spleeter)
- Clear separation of concerns

### 2. **Strategy Pattern for Voice Conversion**

```python
# domain/voice_converter.py (abstract interface)
class VoiceConverter(ABC):
    @abstractmethod
    def convert(self, input_path: str, reference, output_path: str) -> None:
        pass

# infrastructure/chatterbox_wrapper.py
class ChatterBoxVoiceConverter(VoiceConverter):
    def convert(self, input_path, reference, output_path):
        # ChatterBox-specific implementation
        ...

# infrastructure/rvc_wrapper.py
class RVCVoiceConverter(VoiceConverter):
    def convert(self, input_path, reference, output_path):
        # RVC-specific implementation
        ...
```

**Runtime Selection**:
```python
# application/voice_replacement_service.py
if reference_type == "audio":
    converter = ChatterBoxVoiceConverter()
elif reference_type == "model":
    converter = RVCVoiceConverter()
```

### 3. **Subprocess Isolation Pattern**

**Problem**: RVC requires numpy 2.3.5, ChatterBox requires numpy 1.25.2
**Solution**: Isolate RVC in separate Python environment, call via subprocess

```python
# infrastructure/rvc_wrapper.py
def convert_voice_rvc(self, input_audio, reference, output_audio):
    rvc_python = project_root / "venv-rvc" / "Scripts" / "python.exe"
    standalone_script = project_root / "infrastructure" / "rvc_standalone.py"
    
    cmd = [
        str(rvc_python),
        str(standalone_script),
        str(model_path),
        str(index_path),
        str(input_audio),
        str(output_audio),
        f0_method,
        str(f0_up_key)
    ]
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding='utf-8',
        timeout=300
    )
```

**Key Insights**:
- ✅ Prevents dependency conflicts
- ✅ Isolated failures (RVC crash won't kill main app)
- ✅ Can use different Python versions if needed
- ⚠️ Slower than in-process (subprocess overhead ~500ms)
- ⚠️ Requires careful stdout/stderr encoding (Windows UTF-8 issues)

---

## Key Technical Challenges & Solutions

### Challenge 1: Numpy Version Conflict

**Problem**:
```
ChatterBox VC: requires numpy<=1.25.2
Applio RVC:    requires numpy>=2.3.5
```

**Attempted Solutions**:
1. ❌ numpy 1.23.5 compromise → ChatterBox worked, Applio failed
2. ❌ Upgrade ChatterBox deps → Broke internal torch compatibility
3. ✅ **Dual virtual environments** (final solution)

**Implementation**:
```
project_root/
├── .venv/           # Main environment (ChatterBox, Demucs, UI)
│   └── numpy 1.25.2
└── venv-rvc/        # RVC-only environment (Applio dependencies)
    └── numpy 2.3.5
```

**Code**:
```python
# Main app runs in .venv, calls RVC subprocess in venv-rvc
rvc_python = Path("venv-rvc/Scripts/python.exe")
subprocess.run([rvc_python, "rvc_standalone.py", ...])
```

### Challenge 2: Fairseq Python 3.11 Incompatibility

**Problem**:
```python
# Original plan: Use rvc-python 0.1.5
pip install rvc-python

# Error:
# fairseq/dataclass/configs.py line 45:
#     audio_paths: List[str] = List[str]()
# Python 3.11: "mutable default for dataclass field" error
```

**Root Cause**:
- fairseq 0.12.2 uses old dataclass pattern incompatible with Python 3.10+
- `field = List()` should be `field: List = field(default_factory=list)`

**Attempted Solutions**:
1. ❌ Automated patching (8 files) → omegaconf 2.0.6 rejected patched dataclasses
2. ❌ Upgrade omegaconf to 2.3+ → Dependency conflicts with rvc-python
3. ❌ Downgrade to Python 3.9 → ChatterBox requires 3.10+
4. ✅ **Switch to Applio** (no fairseq dependency)

**Why Applio Works**:
- Modern codebase (2024-2026)
- Uses transformers library instead of fairseq
- Native Python 3.11/3.12 support

### Challenge 3: Windows Console Encoding

**Problem**:
```python
# Subprocess output with emojis/unicode
print("Converting... 🎵")  # Crashes on Windows with:
# UnicodeEncodeError: 'charmap' codec can't encode character '\U0001f3b5'
```

**Solution**:
```python
# In subprocess script (rvc_standalone.py)
import sys, io
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(
        sys.stdout.buffer, 
        encoding='utf-8', 
        errors='replace'
    )

# In main process
result = subprocess.run(
    cmd,
    encoding='utf-8',      # Force UTF-8
    errors='replace',       # Replace invalid chars
    capture_output=True
)
```

**Additional Fix**: Remove ALL emoji from logging/print statements

### Challenge 4: RMVPE Model Auto-Download

**Problem**:
```python
# Applio expects models in rvc/models/predictors/rmvpe.pt
FileNotFoundError: 'rvc\\models\\predictors\\rmvpe.pt'
```

**Solution**: Manual download from Applio's HuggingFace repo
```powershell
# Create directory
New-Item -ItemType Directory -Path "rvc\models\predictors"

# Download RMVPE (137MB)
Invoke-WebRequest `
    -Uri "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt" `
    -OutFile "rvc\models\predictors\rmvpe.pt"
```

**Future Improvement**: Add auto-download in Python:
```python
import wget
import os

model_dir = "rvc/models/predictors"
model_path = f"{model_dir}/rmvpe.pt"

if not os.path.exists(model_path):
    os.makedirs(model_dir, exist_ok=True)
    print("Downloading RMVPE model...")
    wget.download(
        "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt",
        model_path
    )
```

---

## Dual-Environment Strategy

### Setup Instructions

**1. Create Main Environment (.venv)**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**requirements.txt** (main):
```
torch==2.10.0+cpu
torchaudio==2.10.0+cpu
numpy==1.25.2
librosa==0.10.2.post1
soundfile==0.13.1
demucs==4.1.0a3
chatterbox-vc==0.1.6
pydub==0.25.1
ffmpeg-python==0.2.0
Pillow==12.0.0
```

**2. Create RVC Environment (venv-rvc)**
```powershell
python -m venv venv-rvc
.\venv-rvc\Scripts\Activate.ps1

# Install Applio dependencies
pip install numpy==2.3.5 scipy==1.16.3
pip install librosa==0.11.0 soundfile==0.12.1
pip install transformers==4.44.2 faiss-cpu==1.13.2
pip install torchcrepe torchfcpe einops
pip install noisereduce pedalboard soxr stftpitchshift
pip install omegaconf>=2.0.6 matplotlib==3.10.8
pip install wget webrtcvad-wheels
```

**3. Install Applio RVC Module**
```powershell
# Clone Applio
git clone --depth 1 https://github.com/IAHispano/Applio.git applio_temp

# Copy rvc module to project
Copy-Item -Path "applio_temp\rvc" -Destination "." -Recurse -Force

# Download RMVPE predictor
New-Item -ItemType Directory -Path "rvc\models\predictors" -Force
Invoke-WebRequest `
    -Uri "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt" `
    -OutFile "rvc\models\predictors\rmvpe.pt"

# Cleanup
Remove-Item -Recurse -Force applio_temp
```

### Environment Switching

**Main App** (runs in .venv):
```python
# voice_revolver_ui/main.py
import sys
from pathlib import Path

# Ensure .venv is active
if not sys.prefix.endswith('.venv'):
    print("ERROR: Must run from .venv environment")
    sys.exit(1)

# Import ChatterBox (available in .venv)
from chatterbox.api import Chatterbox
```

**RVC Subprocess** (runs in venv-rvc):
```python
# voice_revolver_core/infrastructure/rvc_wrapper.py
def convert_voice_rvc(self, input_audio, reference, output_audio):
    project_root = Path(__file__).parent.parent.parent
    rvc_python = project_root / "venv-rvc" / "Scripts" / "python.exe"
    
    if not rvc_python.exists():
        raise RuntimeError(f"RVC environment not found: {rvc_python}")
    
    standalone_script = project_root / "voice_revolver_core" / "infrastructure" / "rvc_standalone.py"
    
    # Call venv-rvc Python interpreter
    cmd = [str(rvc_python), str(standalone_script), ...]
    result = subprocess.run(cmd, ...)
```

**Standalone Script** (executed in venv-rvc):
```python
# voice_revolver_core/infrastructure/rvc_standalone.py
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Applio (available in venv-rvc)
from rvc.infer.infer import VoiceConverter

def run_rvc_inference(model_path, index_path, input_audio, output_audio, ...):
    converter = VoiceConverter()
    converter.convert_audio(
        audio_input_path=input_audio,
        audio_output_path=output_audio,
        model_path=model_path,
        index_path=index_path,
        pitch=f0_up_key,
        f0_method="rmvpe",
        index_rate=0.75,
        embedder_model="contentvec",
        ...
    )
```

---

## Library Integration Details

### Applio RVC Integration

**Key Files**:
```
rvc/
├── infer/
│   ├── infer.py          # VoiceConverter class (main API)
│   └── pipeline.py       # Inference pipeline
├── lib/
│   ├── utils.py          # Audio loading, embeddings
│   └── predictors/
│       ├── RMVPE.py      # Pitch extraction
│       └── f0.py         # F0 processing
├── models/
│   ├── embedders/        # Speaker embeddings (contentvec, etc.)
│   └── predictors/       # F0 predictors (rmvpe.pt)
└── configs/
    └── config.py         # Device config (CPU/GPU)
```

**API Usage**:
```python
from rvc.infer.infer import VoiceConverter

converter = VoiceConverter()

converter.convert_audio(
    audio_input_path="vocals.wav",
    audio_output_path="converted.wav",
    model_path="hanni.pth",              # RVC trained model
    index_path="hanni.index",            # FAISS retrieval index
    pitch=0,                              # Semitone shift (-24 to +24)
    f0_method="rmvpe",                   # Pitch extractor: rmvpe, crepe, fcpe
    index_rate=0.75,                     # Index influence (0.0-1.0)
    volume_envelope=0.25,                # RMS mix rate
    protect=0.33,                        # Consonant protection (0.0-0.5)
    hop_length=128,                      # Audio processing hop
    split_audio=False,                   # Split long audio
    f0_autotune=False,                   # Auto-tune pitch
    clean_audio=False,                   # Noise reduction
    export_format="WAV",                 # Output format
    embedder_model="contentvec",         # Speaker embedding model
    sid=0,                               # Speaker ID (multi-speaker models)
)
```

**Model Format**:
- **RVC .pth**: PyTorch checkpoint with model weights + config
- **FAISS .index**: Vector index for speaker feature retrieval
- Typically distributed as `.zip` containing both files

**Downloaded Models** (on first use):
```
rvc/models/
├── embedders/
│   └── contentvec/
│       ├── pytorch_model.bin  (~300MB)
│       └── config.json
└── predictors/
    └── rmvpe.pt               (~137MB)
```

### ChatterBox VC Integration

**API**:
```python
from chatterbox.api import Chatterbox

chatterbox = Chatterbox(device="cpu")  # or "cuda"

chatterbox.convert(
    source_wav="vocals.wav",      # Input vocals
    target_wav="reference.wav",   # Voice reference sample
    out_path="converted.wav"
)
```

**Key Features**:
- Zero-shot (no training)
- Accepts 3-10 second reference audio
- Best for natural speech
- Fast inference (~1x realtime on CPU)

**Limitations**:
- Less control than RVC (no pitch shift, index rate, etc.)
- Quality depends on reference audio quality
- Not ideal for singing voice conversion

### Demucs Stem Separation

**API**:
```python
from demucs.apply import apply_model
from demucs.pretrained import get_model
import torch

# Load model
model = get_model('htdemucs_ft')
model.eval()

# Load audio (torch tensor)
wav = load_audio(input_path)

# Separate stems
with torch.no_grad():
    sources = apply_model(model, wav[None], device="cpu")[0]

# Extract stems
vocals = sources[model.sources.index('vocals')]
drums = sources[model.sources.index('drums')]
bass = sources[model.sources.index('bass')]
other = sources[model.sources.index('other')]
```

**Wrapper Implementation**:
```python
# infrastructure/demucs_wrapper.py
class DemucsWrapper(StemSeparator):
    def separate(self, input_path: str, output_dir: str):
        # Run demucs CLI (simpler than API)
        subprocess.run([
            "demucs",
            "--two-stems", "vocals",  # Only extract vocals
            "--out", output_dir,
            input_path
        ])
```

**Model Download**: Automatic on first use (~200MB)

---

## Critical Implementation Notes

### 1. Audio Sample Rate Handling

**Standards**:
- **Input**: Any sample rate (auto-detected)
- **Processing**: 16kHz (RVC/ChatterBox standard)
- **Output**: Match input sample rate

**Resampling**:
```python
import librosa

# Load and resample
audio, sr = librosa.load(input_path, sr=None)  # Preserve original SR
audio_16k = librosa.resample(audio, orig_sr=sr, target_sr=16000)

# Process at 16kHz
converted = voice_converter.convert(audio_16k, ...)

# Resample back to original SR
converted_original_sr = librosa.resample(
    converted, 
    orig_sr=16000, 
    target_sr=sr
)
```

### 2. Temporary File Management

**Pattern**:
```python
import tempfile
from pathlib import Path

class VoiceReplacementService:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "voice_revolver"
        self.temp_dir.mkdir(exist_ok=True)
    
    def process(self, input_path):
        # Create unique temp files
        vocals = self.temp_dir / f"vocals_{uuid.uuid4()}.wav"
        converted = self.temp_dir / f"converted_{uuid.uuid4()}.wav"
        
        try:
            # Processing...
            ...
        finally:
            # Cleanup
            vocals.unlink(missing_ok=True)
            converted.unlink(missing_ok=True)
```

### 3. Progress Tracking

**Observer Pattern**:
```python
# domain/progress_tracker.py
class ProgressObserver(ABC):
    @abstractmethod
    def on_progress(self, stage: str, percent: int):
        pass

class ProgressTracker:
    def __init__(self):
        self.observers: List[ProgressObserver] = []
    
    def attach(self, observer: ProgressObserver):
        self.observers.append(observer)
    
    def notify(self, stage: str, percent: int):
        for observer in self.observers:
            observer.on_progress(stage, percent)

# UI observer
class UIProgressObserver(ProgressObserver):
    def __init__(self, progress_bar, status_label):
        self.progress_bar = progress_bar
        self.status_label = status_label
    
    def on_progress(self, stage, percent):
        self.progress_bar.set(percent)
        self.status_label.configure(text=f"[{percent}%] {stage}")
```

### 4. Error Handling Strategy

**Custom Error Codes**:
```python
from enum import Enum

class ErrorCode(Enum):
    INVALID_INPUT = "Invalid input file"
    STEM_SEPARATION_FAILED = "Stem separation failed"
    VOICE_CONVERT_FAILED = "Voice conversion failed"
    MIXING_FAILED = "Audio mixing failed"
    FORMAT_CONVERSION_FAILED = "Format conversion failed"

class VoiceRevolverError(Exception):
    def __init__(self, code: ErrorCode, details: str = ""):
        self.code = code
        self.details = details
        super().__init__(f"{code.value}: {details}")
```

**Graceful Degradation**:
```python
def process_audio(self, input_path, reference):
    try:
        # Attempt processing
        return self._process_pipeline(input_path, reference)
    except VoiceRevolverError as e:
        # Specific errors (show to user)
        logger.error(f"Processing failed: {e.code.value}")
        raise
    except Exception as e:
        # Unexpected errors (log and wrap)
        logger.exception("Unexpected error during processing")
        raise VoiceRevolverError(
            ErrorCode.PROCESSING_FAILED,
            f"Internal error: {str(e)}"
        )
```

---

## Performance Considerations

### CPU vs GPU

**Current Implementation**: CPU-only (broader compatibility)

**GPU Acceleration** (future):
```python
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"

# ChatterBox
chatterbox = Chatterbox(device=device)

# Demucs
separator.device = device

# RVC/Applio (in subprocess)
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # Use first GPU
```

**Benchmark** (4-minute song, CPU: AMD Ryzen 7):
- Stem separation: ~60s (htdemucs_ft)
- Voice conversion: ~30s (ChatterBox) / ~45s (RVC)
- Mixing: ~2s
- **Total**: ~90-110s (~0.4x realtime)

**With GPU** (NVIDIA RTX 3060):
- Stem separation: ~15s
- Voice conversion: ~8s (ChatterBox) / ~12s (RVC)
- **Total**: ~25-30s (~0.1x realtime)

### Memory Optimization

**Lazy Loading**:
```python
class ModelManager:
    def __init__(self):
        self._chatterbox = None
        self._demucs = None
    
    @property
    def chatterbox(self):
        if self._chatterbox is None:
            self._chatterbox = Chatterbox(device="cpu")
        return self._chatterbox
    
    def unload_all(self):
        del self._chatterbox
        del self._demucs
        torch.cuda.empty_cache()  # If using GPU
```

**Memory Usage**:
- Demucs model: ~400MB
- ChatterBox model: ~200MB
- RVC model: ~50-100MB (model-dependent)
- **Peak**: ~600-700MB (all loaded)

---

## Future Project Guidelines

### When Building Similar Audio ML Apps

**1. Start with Environment Planning**
- ✅ Map dependencies FIRST (check numpy/torch version conflicts)
- ✅ Consider dual-environment pattern if conflicts exist
- ✅ Use `pip-compile` or Poetry for reproducible builds

**2. Choose GUI Framework Based on Needs**
| Framework | Best For | Avoid If |
|-----------|----------|----------|
| Tkinter | Utilities, internal tools | Needs modern UI |
| PyQt/PySide | Professional apps | Licensing concerns |
| Electron | Web tech familiarity | Large bundle size (~150MB) |
| Tauri | Modern web + small size | Bleeding edge risk |

**3. Audio Processing Best Practices**
- ✅ Always resample to model's expected SR before processing
- ✅ Use `soundfile` for I/O (better than `scipy.io.wavfile`)
- ✅ Normalize audio [-1.0, 1.0] before ML models
- ✅ Handle mono/stereo conversions explicitly

**4. ML Model Integration**
- ✅ Check Python version compatibility FIRST
- ✅ Prefer actively maintained libraries (check last commit date)
- ✅ Look for clean APIs (avoid CLI wrappers when possible)
- ✅ Cache downloaded models (don't download on every run)

**5. Subprocess Patterns**
```python
# Good: Proper error handling + encoding
result = subprocess.run(
    cmd,
    capture_output=True,
    text=True,
    encoding='utf-8',
    errors='replace',
    timeout=300,
    check=False  # Handle errors manually
)

if result.returncode != 0:
    raise RuntimeError(f"Subprocess failed: {result.stderr}")

# Bad: Shell=True (security risk)
subprocess.run(f"python {script} {args}", shell=True)  # ❌ NO!
```

**6. Testing Strategy**
- ✅ Unit tests for business logic (domain layer)
- ✅ Integration tests for adapters (infrastructure layer)
- ✅ Manual tests for UI/UX flows
- ✅ Use sample audio files (short 5-10s clips for fast tests)

**7. Distribution**
- ✅ PyInstaller for single-file executables
- ✅ Include ffmpeg binaries in bundle
- ✅ Pre-download critical models (or implement auto-download)
- ✅ Test on clean VM (check for missing DLLs/dependencies)

---

## Appendix: Quick Reference Commands

### Environment Setup
```powershell
# Main environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# RVC environment
python -m venv venv-rvc
.\venv-rvc\Scripts\Activate.ps1
pip install numpy==2.3.5 scipy==1.16.3 librosa==0.11.0 soundfile==0.12.1
pip install transformers==4.44.2 faiss-cpu==1.13.2 torchcrepe torchfcpe
pip install noisereduce pedalboard soxr wget
```

### Run Application
```powershell
.\.venv\Scripts\Activate.ps1
python run.py
```

### Test RVC Subprocess Directly
```powershell
.\venv-rvc\Scripts\python.exe voice_revolver_core\infrastructure\rvc_standalone.py `
    "path\to\model.pth" `
    "path\to\model.index" `
    "input.wav" `
    "output.wav" `
    "rmvpe" `
    0
```

### Download RMVPE Model
```powershell
Invoke-WebRequest `
    -Uri "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt" `
    -OutFile "rvc\models\predictors\rmvpe.pt"
```

---

## Version History

| Version | Date | Key Changes |
|---------|------|-------------|
| 1.0.0 | Feb 2026 | Initial release with dual-reference support |
| 1.0.1 | Feb 2026 | Migrated from rvc-python to Applio (Python 3.11 fix) |

---

**Document Maintained By**: Voice Revolver AI Development Team  
**Last Updated**: February 20, 2026  
**License**: MIT
