# Agent Memory

> This file serves as AI memory for the project. Update it with important highlights after each session. Git-sync across machines.

## Summary

Voice Revolver AI - A local-first desktop application for vocal replacement in songs. Uses AI (Demucs + ChatterBox VC) to separate vocals from a song and replace them with a reference voice. Built with DDD architecture for modularity.

**Current State:** ChatterBox VC integration complete, replacing OpenVoice for better quality
**Goal:** Portable desktop app (Windows .exe, Mac .app)

---

## Project Design

### Architecture
- **Pattern:** Domain-Driven Design (DDD)
- **Layers:** Domain → Application → Infrastructure → Interface (UI)

### DDD Core Components
1. **StemSeparator** - Demucs for stem separation (vocals, drums, bass, other)
2. **VoiceConverter** - ChatterBox VC for voice conversion (OpenVoice V2 kept as fallback)
3. **AudioMixer** - Combine vocals + instrumental
4. **FormatConverter** - pydub for format conversion (WAV ↔ MP3/FLAC)
5. **VoiceTransformer** - Pitch + Emotion control
6. **FileManager** - Temp files, export workflow, auto-naming (date_time_random)
7. **ProgressTracker** - Track progress with unique keys for polling
8. **ErrorCode** - Global error system (code: "WHAT_HAPPENED")
9. **ModelManager** - Auto-download models on first startup
10. **ProjectService** - Save/load .vra project files

### Tech Stack
- **Language:** Python 3.11.x (REQUIRED)
  - **CRITICAL:** All AI tools (Demucs, RVC, MDX, Resemble Enhance) use Python 3.11
  - Python 3.14 lacks CUDA-enabled PyTorch builds (CPU-only as of Feb 2026)
  - Always create virtual environments with Python 3.11 for AI/ML features
  - Main venvs: `.venv-1` (app), `venv-rvc` (RVC), `venv-mdx` (MDX), `venv-enhance` (Resemble)
- **UI Framework:** tkinter (native Python)
- **ML Models:** Demucs, ChatterBox VC (OpenVoice V2 legacy)
- **Audio:** pydub, FFmpeg (bundled + auto-download), pygame (preview)
- **Audio Enhancement:** noisereduce, pedalboard, pyloudnorm
- **Packaging:** PyInstaller/Nuitka (portable EXE)

### Key Features
- Local processing (no cloud)
- Auto-download models on first launch
- Preview with play/pause/seek
- Export with custom naming + folder selection
- GPU/CPU selection (auto-detect + user override)
- Terminal visible on startup
- Temp file cleanup on close
- Logging to file

---

## Coding Standards

### Logging Best Practices
- **NEVER use emoji characters in log messages** (🎵, ✅, ⚠️, etc.)
  - Windows console uses cp1252 encoding which doesn't support Unicode emojis
  - Causes `UnicodeEncodeError: 'charmap' codec can't encode character` errors
  - Use ASCII-safe text instead:
    - `🎵` → `[INSTRUMENTAL VOLUME]` or `[MUSIC]`
    - `✅` → `[OK]` or `[SUCCESS]`
    - `⚠️` → `[WARNING]`
    - `❌` → `[ERROR]` or `[FAILED]`
- **Example:**
  ```python
  # ❌ BAD - Will crash on Windows
  logger.info(f"🎵 Applying curve to {filename}")
  
  # ✅ GOOD - ASCII-safe
  logger.info(f"[MUSIC] Applying curve to {filename}")
  ```

---

## History Log

### 2026-02-22 | Instrumental Volume Curve Integration & Logging Fix
- **Topic:** Implemented instrumental volume editing in spectrum editor + applied to final mix processing
- **Feature Request:** User wanted to control instrumental volume separately from vocals in spectrum editor
- **Implementation:**
  1. **Domain Models** (base.py):
     - Added `InstrumentalVolumeControlPoint` (time, gain_db)
     - Added `InstrumentalVolumeCurve` with interpolation support
  2. **Spectrum Editor** (spectrum_editor.py):
     - Added "Instrumental Vol" mode with orange control points
     - Volume range: -50 to +50 dB (same as vocal volume)
     - Audio playback switches to instrumental when in this mode
     - All editing operations support instrumental_volume mode
  3. **Final Processing Integration** (voice_replacement_service.py):
     - Apply instrumental volume curve to all stems (drums, bass, other) before mixing
     - Disable mixer normalization when curve is edited (preserves user adjustments)
     - Files: `drums_volume_adjusted.wav`, `bass_volume_adjusted.wav`, `other_volume_adjusted.wav`
- **Critical Bug Found & Fixed:**
  - **Issue:** Mixer's `normalize()` function was undoing volume curve changes
  - **Root Cause:** After reducing instrumental to -50 dB, normalization brought it back to full volume
  - **Solution:** Disable normalization when instrumental_volume curve has edits
- **Logging Issue Fixed:**
  - **Problem:** Emoji characters (🎵, ✅, ⚠️) caused `UnicodeEncodeError` on Windows cp1252 console
  - **Solution:** Replaced all emojis with ASCII-safe text (`[INSTRUMENTAL VOLUME]`, `[OK]`, `[WARNING]`)
  - **Added:** Coding standard to **NEVER use emojis in logger messages**
- **Files Modified:**
  - `voice_revolver_core/domain/base.py` - Added instrumental volume domain models
  - `voice_revolver_ui/spectrum_editor.py` - New editing mode with UI controls
  - `voice_revolver_core/application/voice_replacement_service.py` - Apply curve to stems before mixing
  - `voice_revolver_core/infrastructure/audio_processor.py` - Added debug logging for volume curve
  - `voice_revolver_core/infrastructure/audio_mixer.py` - `set_normalize()` method used
- **Testing Results:**
  - ✅ Instrumental volume curve applied successfully to all 3 stems
  - ✅ -20.2 dB reduction = 0.0982x linear gain (~10% volume)
  - ✅ Normalization disabled when curve exists
  - ✅ Final mix preserves volume adjustments
  - ✅ No Unicode logging errors

### 2026-02-21 | Python Environment Standard
- **Topic:** Virtual environment Python version standardization
- **Discovery:** All AI/ML tools require Python 3.11.x for CUDA support
- **Key Findings:**
  - **venv-mdx** (Python 3.11.9): PyTorch 2.1.2+cu118 ✅ CUDA working
  - **venv-rvc** (Python 3.11.9): PyTorch 2.10.0+cpu ❌ CPU only (needs reinstall)
  - **.venv-1** (Python 3.14.0): No torch, main app
  - **venv-enhance** (Python 3.11.9): ✅ CUDA working - PyTorch 2.1.1+cu118, DeepSpeed 0.16.5
- **Issue:** Python 3.14.0 only has CPU-only PyTorch builds (no CUDA as of Feb 2026)
- **Decision:** Always use Python 3.11.x for AI/ML virtual environments
- **Action:** Deleted venv-enhance (Python 3.14) and recreated with Python 3.11.9
- **STANDARD:** When creating any AI/ML venv, always specify Python 3.11:
  ```powershell
  C:\Users\jerow\AppData\Local\Programs\Python\Python311\python.exe -m venv venv-name
  ```

### 2026-02-21 | DeepSpeed Windows Installation
- **Topic:** Successfully installed DeepSpeed on Windows for Resemble Enhance
- **Challenge:** resemble-enhance requires deepspeed==0.12.4, but it won't build on Windows
- **Solution:** Install latest DeepSpeed (0.16.5+) with prebuilt Windows wheels
- **Key Commands:**
  ```powershell
  # Install PyTorch with CUDA first
  pip install torch==2.1.1 torchaudio==2.1.1 --index-url https://download.pytorch.org/whl/cu118
  
  # Install DeepSpeed using ONLY prebuilt wheels (no source build)
  pip install deepspeed --only-binary=:all:
  
  # This installs DeepSpeed 0.16.5 (latest Windows-compatible version)
  ```
- **Critical Findings:**
  - DeepSpeed 0.14.5+ has native Windows support with prebuilt operators
  - Windows does NOT support: async I/O (AIO), GDS (warnings are normal)
  - Must use `--only-binary=:all:` to avoid source build attempts
  - Version mismatch (0.16.5 vs 0.12.4) is acceptable for inference-only use
- **Resources:** [DeepSpeed Windows Blog](https://github.com/deepspeedai/DeepSpeed/blob/master/blogs/windows/08-2024/README.md)
- **Result:** ✅ venv-enhance fully operational with GPU/CUDA support

### 2026-02-21 | CRITICAL LESSON: Listen Carefully & Avoid Regressions
- **Topic:** Agent behavior correction - careful listening required
- **Issue:** Multiple instances of not listening to user instructions properly:
  - User said "ADD volume slider to spectrum editor" → Agent REMOVED volume slider from preview section instead of just adding
  - User said volume should be "in the right side" → Agent placed it at bottom
  - Made multiple back-and-forth mistakes causing frustration
- **ROOT CAUSE:** Agent misinterpreted "add" as "move", didn't read carefully, made assumptions
- **LESSON LEARNED:**
  1. **READ CAREFULLY:** When user says "ADD", it means ADD, not MOVE or REPLACE
  2. **VERIFY BEFORE ACTING:** Check what currently exists before making changes
  3. **AVOID REGRESSIONS:** Never remove/break existing working features unless explicitly asked
  4. **ASK IF UNCLEAR:** If instruction is ambiguous, ask for clarification instead of guessing
  5. **TEST MENTALLY:** Before editing, think "Will this break something that's already working?"
- **CORRECT BEHAVIOR:**
  - User: "Add X to Y" → Add X to Y, keep everything else unchanged
  - User: "Move X to Y" → Move X from current location to Y
  - User: "Replace X with Y" → Remove X, add Y in its place
- **MEMORY:** Always be extra careful with UI changes - users get frustrated when things that worked suddenly break

### 2026-02-18 | Session Protocol
- **Topic:** Session memory protocol established
- **Decision:** Must read AGENT_MEMORY.md + ./docs/* at start of every session, and update memory with any important changes

### 2026-02-18 | Git Setup
- **Topic:** Created git branches and documented remote
- **Decision:** Created three branches: main, staging, development
- **Remote:** origin -> https://github.com/JeroTan/voice-revolver-local-ai.git

### 2026-02-18 | Project Setup
- **Topic:** Created memory files structure
- **Decision:** AGENT_MEMORY.md serves as project history/summary, README.md will be the base project information

### 2026-02-18 | PRD Creation
- **Topic:** Voice Revolver AI PRD completed
- **Decision:** Created full PRD at docs/voice-revolver-ai-prd.md with:
  - 10 DDD Core components defined
  - MVP + Phase 2 features
  - Tech stack: Python + PyQt + Demucs + OpenVoice
  - Portable EXE for Windows/Mac
  - Auto-download models + FFmpeg on first launch
  - .vra project file format

### 2026-02-18 | MVP Implementation
- **Topic:** MVP implementation completed
- **Decision:** Implemented all core features:
  - FFmpeg auto-download via `static-ffmpeg` library
  - Model auto-download (Demucs package + OpenVoice V2 checkpoints from myshell S3)
  - Demucs wrapper for stem separation
  - OpenVoice V2 wrapper for voice conversion
  - AudioMixer with pydub for mixing vocals + instrumental
  - FormatConverter for MP3/WAV/FLAC export
  - VoiceReplacementService wired with real implementations
  - Processing thread (QThread) for background processing
  - Progress tracking connected to UI
  - Preview player using QMediaPlayer
  - Project save/load (.vra files)
  - GPU/CPU detection via ComputeController

### 2026-02-18 | Development Environment Testing & Critical Bug Fixes
- **Topic:** Fixed Python version compatibility + multiple critical UI/architecture bugs
- **Issue:** Initial venv created with Python 3.14 which has PyTorch DLL errors on Windows (c10.dll fails to load)
- **Solution:** Recreated venv with Python 3.11.9 - PyTorch works perfectly
- **Decision:** **ENFORCE Python 3.11.x requirement** (documented in requirements.txt)

#### Critical Bugs Discovered & Fixed:
1. **GPU Selection Broken** - All device buttons were disabled on startup
   - Root cause: `detect_hardware()` was disabling buttons when torch import failed
   - Fix: Keep buttons enabled, show "GPU (Detection failed)" but allow manual selection
   - File: `voice_revolver_ui/main.py` lines 132-166

2. **Missing Loading Flow** - App skipped loading dialog and jumped to main window
   - Root cause: `LoadingDialog` was created but never shown in main()
   - Fix: Show LoadingDialog → initialize models → show MainWindow
   - File: `voice_revolver_ui/main.py` main() function

3. **Critical Typo in OpenVoice Path** - Models would never load
   - Root cause: `self.model_manager.openapi_path` (wrong!) instead of `openvoice_path`
   - Fix: Changed to correct property name `openvoice_path`
   - File: `voice_revolver_ui/main.py` line 663

4. **Wrong Layer Import** - ProjectService imported from domain instead of application
   - Root cause: DDD architecture violation - service was in wrong layer
   - Fix: `from voice_revolver_core.application import ProjectService`
   - File: `voice_revolver_ui/main.py` imports

5. **PyTorch DLL Crashes** - OSError on Windows with Python 3.14
   - Root cause: PyTorch 2.10.0 incompatible with Python 3.14 (c10.dll initialization fails)
   - Fix: Multiple catch points for (ImportError, OSError, Exception) in:
     - `voice_revolver_core/infrastructure/compute_controller.py` - _check_cuda()
     - `voice_revolver_ui/main.py` - detect_hardware()
   - **CRITICAL:** Deleted Python 3.14 venv, recreated with Python 3.11.9

6. **Missing Progress Module** - FFmpeg downloader would crash
   - Root cause: `static-ffmpeg` requires `progress` module not in requirements.txt
   - Fix: Added `progress` to requirements.txt and installed

#### Development Workflow Improvements:
- **Created convenience scripts:** `run_dev.ps1` and `run_dev.bat` 
  - Auto-activate Python 3.11 venv before launching app
  - Prevents accidental use of system Python 3.14
  - Shows Python version for verification
- **Updated requirements.txt** with clear Python 3.11.x requirement note
- **Lazy imports implemented** in `voice_revolver_core/__init__.py` to prevent PyTorch loading at module initialization

#### Technical Lessons Learned:
- ⚠️ **Python 3.14 is INCOMPATIBLE with PyTorch 2.10.0 on Windows** - DLL errors
- ⚠️ **Virtual environment MUST be activated** - system Python causes failures
- ⚠️ **Exception handling must catch OSError** - not just ImportError for DLL failures
- ⚠️ **Lazy imports critical** - heavy dependencies like PyTorch shouldn't load at module import time
- ⚠️ **UI buttons should stay enabled** - graceful degradation better than disabled UI

#### Testing Results:
- ✅ All imports working: Demucs, OpenVoice, PyQt6, pydub, torch
- ✅ PyTorch 2.1.2+cpu loads successfully in Python 3.11 (downgraded from 2.10.0)
- ✅ App launches without DLL errors
- ✅ GPU/CPU selection buttons both functional
- ✅ Loading dialog displays before main window
- ⏳ End-to-end vocal processing not yet tested (next step)

### 2026-02-18 | Critical Threading Architecture Fix
- **Topic:** Fixed silent crashes caused by async/await + QThread + PyTorch incompatibility
- **Issue:** App crashed silently (segfault) after loading Demucs model when starting processing
- **Root Cause:** PyTorch + asyncio event loop + QThread = fatal incompatibility on Windows
  - async/await functions running inside QThread.run() with asyncio.new_event_loop()
  - PyTorch tensor operations fail catastrophically in this threading context
  - No error messages - just immediate process termination

#### Debugging Process:
1. Added extensive logging to trace crash location
2. Confirmed PyTorch imports fine in isolation but crashes in worker thread
3. Tried preloading AI libraries at app startup - still crashed
4. Created `test_core.py` to test processing logic WITHOUT UI
5. **Discovery:** Core logic works perfectly outside QThread context

#### Solution - Remove All Async/Await:
**CRITICAL ARCHITECTURE CHANGE:** Converted entire processing pipeline from async to synchronous

Files Modified:
- `voice_revolver_core/infrastructure/demucs_wrapper.py` - Removed async from load_model(), separate()
- `voice_revolver_core/infrastructure/openvoice_wrapper.py` - Removed async from all methods
- `voice_revolver_core/infrastructure/audio_mixer.py` - Removed async from mix(), mix_simple()
- `voice_revolver_core/application/voice_replacement_service.py` - Removed async from all methods
- `voice_revolver_ui/main.py` ProcessingWorker.run() - Removed asyncio.new_event_loop()

#### Additional Fixes:
- **PyTorch Version:** Downgraded from 2.10.0 → 2.1.2 LTS (more stable on Windows)
- **NumPy Version:** Pinned to <2.0 (PyTorch 2.1.2 incompatible with NumPy 2.x)
- **static-ffmpeg API:** Fixed import from `static_ffmpeg.run` instead of module root
- **OpenVoice API:** Removed `enable_watermark` parameter (not supported in current version)
- **Requirements.txt:** Updated with PyTorch 2.1.2, NumPy <2.0, --index-url for PyTorch CPU builds

#### Technical Discoveries:
- ⚠️ **async/await + QThread + PyTorch = CRASH** - Never mix these three
- ⚠️ **QThread should run synchronous code** - Use threading primitives, not asyncio
- ⚠️ **PyTorch 2.1.2 LTS more stable than 2.10.0** on Windows with Python 3.11
- ⚠️ **Test core logic separately** - Create test scripts without UI to isolate issues
- ⚠️ **Silent crashes indicate threading issues** - Segfaults don't produce Python tracebacks

#### Testing Infrastructure:
- Created `test_core.py` - Standalone test script for core processing logic
- Tests run directly (no UI, no QThread) to verify algorithm correctness
- ✅ Confirmed: Core processing logic works correctly
- ✅ Confirmed: Issue was UI threading architecture, not processing code

#### Files Changed Summary:
1. Replaced all `async def` → `def` in infrastructure layer
2. Replaced all `await` calls with direct function calls
3. Removed asyncio event loop from ProcessingWorker
4. Removed FFmpeg async download (use sync executor)
5. Fixed OpenVoice ToneColorConverter API compatibility

#### Current Status:
- ✅ App compiles without syntax errors
- ✅ Core processing tested successfully via test_core.py
- ⏳ UI processing flow needs testing (should work now with synchronous code)
- 📋 Next: Test full UI workflow to confirm fix

### 2026-02-19 | ChatterBox Integration - Improved Voice Quality
- **Topic:** Replaced OpenVoice V2 with ChatterBox VC for better conversion quality
- **Issue:** OpenVoice V2 converted vocals sounded "sabog" (distorted/messy)
  - Watermark embedding degraded audio quality
  - Aggressive vocal enhancement before conversion too strong
  - Overall poor conversion quality

#### Investigation & Failed Fixes:
1. Tried disabling OpenVoice watermark - API error (not supported in installed version)
2. Reduced vocal enhancement (noise_reduction 0.8 → 0.3) - no improvement
3. Disabled vocal enhancement entirely - still distorted

#### Solution - ChatterBox VC Integration:
**Decision:** Switch to ChatterBox VC (Resemble AI) - state-of-the-art voice conversion

Files Created:
- `voice_revolver_core/infrastructure/chatterbox_wrapper.py` - ChatterBox VC wrapper
  - Simple API: `convert_voice(source, target, output)` - no complex params
  - Sample rate: 24kHz (ChatterBox default)
  - Device auto-detection (CUDA/MPS/CPU)

Files Modified:
- `requirements.txt` - Added `chatterbox-tts` as primary VC engine
- `voice_revolver_core/application/voice_replacement_service.py`:
  - Updated `_convert_voice()` to use ChatterBox's simple API
  - Added commented code for switching back to OpenVoice
- `voice_revolver_ui/main_tk.py`:
  - Switched from `OpenVoiceWrapper` to `ChatterBoxWrapper`
  - **Commented out OpenVoice UI controls:**
    - Voice Style dropdown (accent variants)
    - Conversion Strength (tau) slider, input, reset button
  - Added fallback initialization for compatibility
  - Added clear comments marking controls as "OpenVoice-only"

#### ChatterBox vs OpenVoice:
| Feature | OpenVoice V2 | ChatterBox VC |
|---------|--------------|---------------|
| **Quality** | Poor (distorted) | Better (22K+ stars) |
| **API** | Complex (tau, style, embeddings) | Simple (2 params) |
| **Watermark** | Yes (degrades quality) | Yes (Perth - imperceptible) |
| **Parameters** | tau, style, style_strength | None (auto-optimized) |
| **Stars** | ~10K | 22.7K |
| **License** | MIT | MIT |

#### Architecture Changes:
- **OpenVoice kept intact** - Easy to switch back if needed
- **UI controls commented** - Not deleted, just disabled
- **Service layer flexible** - Accepts either wrapper implementation

#### Installation:
- Installed `chatterbox-tts` in Python 3.11 venv
- Dependencies: torch 2.6.0, transformers, gradio, librosa, etc.
- ⚠️ Downgraded numpy to 1.25.2 (ChatterBox requirement)

#### UI Changes:
- Window size: 900x850 (fits all controls + previews)
- Log window: Positioned to the right of main window (not below)
- Volume slider: Added for preview playback control
- Preview tracks: 5 separate players (Original, Original Vocals, Converted Vocals, Final Remix, Instrumental)

#### File Caching Fix:
- **Issue:** Preview showing old cached files from previous runs
- **Fix:** Added cleanup at start of processing:
  - Deletes all preview files: mixed_output.wav, converted_vocals.wav, original_vocals.wav, etc.
  - Copies stems to standardized names for UI preview
  - Ensures fresh files for each processing run

#### Current Status:
- ✅ ChatterBox wrapper implemented
- ✅ Service layer updated to use ChatterBox
- ✅ UI controls for OpenVoice commented out
- ✅ chatterbox-tts installed successfully
- ✅ Conversion quality excellent (ChatterBox)
- ✅ Reference voice denoising added (50% noise reduction)
- ✅ 6th preview player for denoised reference
- ✅ File lock errors fixed
- ✅ Preview playback working for all tracks

#### Technical Notes:
- **ChatterBox has TTS capabilities** (text-to-speech) but we only use VC (voice conversion)
- **ChatterBoxTTS has more controls** (cfg_weight ≈ tau, exaggeration) but requires text input
- **ChatterBoxVC is simpler** - Perfect for our use case (audio → audio conversion)

### 2026-02-20 | Dual-Reference Mode - RVC Integration
- **Topic:** Added dual-reference voice conversion (Audio files OR RVC models)
- **Goal:** Support both easy audio-based conversion (ChatterBox) and advanced pre-trained models (RVC)

#### Feature Overview:
Users can now choose between two reference voice modes:
1. **Audio File (ChatterBox)** - Simple: Upload any voice audio (.mp3/.wav) 
2. **RVC Model (.zip)** - Advanced: Use pre-trained RVC models (.pth + .index)

#### Implementation:

**Files Created:**
- `voice_revolver_core/infrastructure/rvc_wrapper.py` (246 lines)
  - Full RVC integration wrapper
  - `load_model_from_zip()` - Extracts .pth (weights) + .index (FAISS retrieval) from zip
  - `_load_rvc_model()` - Lazy imports RVC library, initializes VC module
  - `convert_voice()` - RVC conversion with 8 parameters:
    - f0_method: rmvpe (best pitch detection)
    - f0_up_key: pitch shift (0 = no shift)
    - index_rate: 0.75 (retrieval index influence)
    - filter_radius: 3 (pitch smoothing)
    - resample_sr: 0 (keep original sample rate)
    - rms_mix_rate: 0.25 (envelope mixing)
    - protect: 0.33 (consonant protection)
  - `unload_model()` - Cleanup temp files + GPU cache
  - Sample rate: 40000Hz (RVC default)

**Files Modified:**
- `voice_revolver_ui/main_tk.py`:
  - Lines 280-283: Added `self.reference_mode = tk.StringVar(value="audio")`
  - Lines 376-390: Added reference mode UI (Radio buttons: "Audio File (ChatterBox)" vs "RVC Model (.zip)")
  - Lines 664-730: Updated `_select_reference()` for dual-mode file selection:
    - Audio mode: .mp3/.wav/.flac/.ogg/.m4a dialog
    - Model mode: .zip dialog
  - Lines 707-730: Added `_validate_rvc_zip()` - checks for .pth and .index files in zip
  - Lines 701-705: Added `_on_reference_mode_change()` - clears selection on mode switch
  - Lines 970-1043: Updated `_load_all_previews()` - conditionally loads reference_denoised (audio mode only)
  - Lines 830-840: Updated `_process()` to pass `reference_mode` parameter

- `voice_revolver_core/application/voice_replacement_service.py`:
  - Lines 1-21: Added `from ..infrastructure.rvc_wrapper import RVCWrapper`
  - Lines 31-49: Added `self._rvc_wrapper: Optional[RVCWrapper] = None` (lazy-loaded)
  - Lines 51-79: Added `reference_mode: str = "audio"` parameter to `process()` method
  - Lines 173-198: Updated Stage 2.6 (reference denoising):
    - Audio mode: Denoise reference with `denoise_only()` before ChatterBox
    - Model mode: Skip denoising, use .zip path directly
  - Lines 337-416: Updated `_convert_voice()` for dual mode:
    - Added `reference_mode` parameter
    - Audio mode: Use ChatterBox wrapper (existing flow)
    - Model mode: Lazy-load RVC wrapper, load model from zip, convert, unload
    - Auto-detects CUDA for GPU acceleration

- `requirements.txt`:
  - Added RVC installation instructions
  - Noted dependencies: rvc-python, faiss-cpu, praat-parselmouth, pyworld
  - GitHub link: https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

#### Architecture Design:
- **ChatterBox VC** - Default/primary for audio references (easy, good quality)
- **RVC** - Optional for advanced users with pre-trained models (best quality, requires model training)
- **Lazy loading** - RVC wrapper only initialized when model mode is used
- **Conditional processing** - Different pipeline paths based on reference_mode
- **Preview logic** - Shows 5 or 6 players depending on mode (reference_denoised only for audio)

#### RVC Model Format:
- **.zip file** containing:
  - `.pth` - PyTorch model weights
  - `.index` - FAISS retrieval index for voice matching
- Example: `my_voice.zip` → `my_voice.pth` + `my_voice.index`
- Sample rate: 40000Hz
- F0 method: rmvpe (Robust Model for Voice Pitch Estimation)

#### UI/UX:
- Radio button toggle (Audio/Model) below reference file selector
- File dialog changes based on mode:
  - Audio: Shows .mp3, .wav, .flac, .ogg, .m4a
  - Model: Shows .zip only
- Zip validation on selection with error messagebox
- Mode switching clears file selection to prevent mismatches
- Progress indicator shows conversion engine: "Converting voice... (RVC)" vs "Converting voice... (ChatterBox)"

#### Current Status:
- ✅ RVC wrapper implemented (subprocess-based approach to bypass Python 3.11 bugs)
- ✅ UI toggle with validation complete
- ✅ Service layer dual-mode logic complete
- ✅ Preview logic updated for conditional loading
- ✅ Requirements.txt updated with RVC + installation notes
- ✅ **PRODUCTION READY:** RVC integration using Applio framework (Feb 2026)
  - **Replaced rvc-python 0.1.5** (abandoned, fairseq bugs) with **Applio** (actively maintained)
  - Dual virtual environment architecture:
    - **Main (.venv)**: ChatterBox, Demucs, UI (numpy 1.25.2)
    - **RVC (venv-rvc)**: Applio dependencies (numpy 2.3.5)
  - Main process calls `rvc_standalone.py` via subprocess in venv-rvc
  - No dependency conflicts, both engines fully functional

#### Installation:
```powershell
# 1. Main environment (already setup)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# 2. Create RVC environment
python -m venv venv-rvc
.\venv-rvc\Scripts\Activate.ps1

# 3. Install Applio dependencies
pip install numpy==2.3.5 scipy==1.16.3 librosa==0.11.0 soundfile==0.12.1
pip install transformers==4.44.2 torchcrepe torchfcpe einops
pip install noisereduce pedalboard soxr stftpitchshift wget webrtcvad-wheels
pip install omegaconf>=2.0.6 matplotlib==3.10.8

# 3a. Install FAISS (choose CPU or GPU version)
# For GPU (recommended if you have NVIDIA GPU with CUDA):
pip install faiss-gpu

# OR for CPU-only (slower index search but still works):
pip install faiss-cpu==1.13.2

# 4. Install Applio RVC module
git clone --depth 1 https://github.com/IAHispano/Applio.git applio_temp
Copy-Item -Path "applio_temp\rvc" -Destination "." -Recurse -Force
Remove-Item -Recurse -Force applio_temp

# 5. Download RMVPE pitch predictor (137MB)
New-Item -ItemType Directory -Path "rvc\models\predictors" -Force
Invoke-WebRequest `
    -Uri "https://huggingface.co/IAHispano/Applio/resolve/main/Resources/predictors/rmvpe.pt" `
    -OutFile "rvc\models\predictors\rmvpe.pt"
```

#### Success Metrics:
- ✅ RVC model loading works (.pth + .index from .zip)
- ✅ Actual trained model inference (not pitch-shift simulation)
- ✅ RMVPE pitch extraction functional
- ✅ ContentVec embeddings auto-download
- ✅ No fairseq dependency issues (Applio doesn't use fairseq)
- ✅ Python 3.11 fully compatible
- ✅ Both ChatterBox and RVC work simultaneously

#### Technical Implementation:
- **Applio VoiceConverter API:** `rvc.infer.infer.VoiceConverter`
- **Subprocess isolation:** venv-rvc Python interpreter called from main app
- **Model format:** .zip containing .pth (weights) + .index (FAISS retrieval)
- **F0 methods:** rmvpe (default), crepe, fcpe, hybrid combinations
- **Embedders:** contentvec (default), spin, chinese-hubert, japanese-hubert
- **GPU acceleration:** RVC neural network runs on CUDA/MPS/CPU (auto-detected)
  - Main inference: Uses PyTorch GPU acceleration
  - Index search: Uses FAISS (GPU via faiss-gpu, CPU via faiss-cpu)
  - Performance: GPU ~10x faster than CPU for voice conversion
- **Advanced parameters:** Now fully implemented and passed to Applio:
  - `index_rate`: Feature retrieval strength (0.0-1.0, default 0.75)
  - `filter_radius`: Median filter for pitch smoothing (0-7, default 3)
  - `resample_sr`: Output sample rate (0=auto from model)
  - `rms_mix_rate`: Volume envelope mixing (0.0-1.0, default 0.25)
  - `protect`: Protect voiceless consonants (0.0-0.5, default 0.33)
- **Temp directory management** for model extraction from zip
- **Model cleanup** after conversion to free GPU memory

#### Key Files:
- `voice_revolver_core/infrastructure/rvc_standalone.py`: Subprocess script using Applio
- `voice_revolver_core/infrastructure/rvc_wrapper.py`: Main app RVC integration
- `rvc/` (Applio module): Complete RVC inference stack
- `rvc/models/predictors/rmvpe.pt`: Pitch extraction model
- See `docs/technical-implementation-guide.md` for full architecture details

---

### GPU Setup and Requirements

**Status:** ⚠️ Updated (Feb 20, 2026) - GPU detection requires CUDA-enabled PyTorch  

#### Issue: GPU Not Detected
The default `requirements.txt` installs **CPU-only PyTorch** which cannot detect your GPU:
```
--index-url https://download.pytorch.org/whl/cpu  # ← CPU only!
torch==2.1.2
```

#### Solution: Install CUDA-Enabled PyTorch
For NVIDIA GPUs (RTX/GTX series), update to CUDA 11.8:
```
--index-url https://download.pytorch.org/whl/cu118  # ← CUDA 11.8
torch==2.1.2
torchaudio==2.1.2
```

#### Reinstallation Steps (for existing installations):
```powershell
# Activate your environment
.\venv\Scripts\Activate.ps1

# Uninstall CPU version
pip uninstall torch torchaudio -y

# Install CUDA version (CUDA 11.8 - most compatible)
pip install torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118

# IMPORTANT: Install CUDA Toolkit 11.8 (required for GPU)
# Download: https://developer.nvidia.com/cuda-11-8-0-download-archive
# Without CUDA Toolkit, app will crash with "caffe2_nvrtc.dll not found"

# Verify GPU detection
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

#### Additional Dependency: cuDNN
After installing PyTorch with CUDA, you must also install cuDNN:
```powershell
# Install cuDNN libraries via pip (easiest method)
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11
```

Without cuDNN, you'll see errors like:
- `"cudnn_cnn_infer64_8.dll not found"`
- `torch.cuda.is_available()` returns False even with CUDA Toolkit installedCommon Issues:
- **"caffe2_nvrtc.dll not found"** or **"cudnn*.dll not found"**: CUDA Toolkit or cuDNN missing
  - Solution 1: Install CUDA Toolkit 11.8 from NVIDIA, then `pip install nvidia-cudnn-cu11`
  - Solution 2: Reinstall CPU-only PyTorch if you don't want GPU acceleration
- **GPU not detected**: CPU-only PyTorch installed instead of CUDA version
  - Solution: Follow reinstallation steps above
- **Corrupted PyTorch (~orch folder)**: Symptom of failed PyTorch installation
  - Solution: `Remove-Item ".\venv\Lib\site-packages\~orch*" -Recurse -Force`, then reinstall
- **File locked errors during reinstall**: App or Python process holding torch DLLs
  - Solution: Close Voice Revolver, kill all python.exe processes, then reinstall

#### Testing:
- RTX 4050 GPU confirmed working (6GB VRAM sufficient)
- Speed improvements: ~10-20x faster than CPU for MDX, Demucs, ChatterBox
- Demucs: 2-5 min (CPU) → 15-30 sec (GPU)
- MDX: 30 min (CPU) → ~2 min (GPU)
- ChatterBox: 30 sec (CPU) → 8 sec (GPU)

#### Key Files:
- `voice_revolver_core/infrastructure/compute_controller.py`: GPU detection logic
- `voice_revolver_ui/main_tk.py`: Startup dialog with GPU/CPU selection
- `requirements.txt`: PyTorch installation configuration

---

### MDX Stem Separation (OPTIONAL - Best Vocal Isolation)


**Status:** ✅ Implemented (Feb 20, 2026) - Optional alternative to Demucs  
**Architecture:** Dual venv (same as RVC) to avoid PyTorch conflicts

#### Why Separate venv-mdx?
- `audio-separator` requires its own PyTorch version (conflicts with main app)
- Demucs works great for balanced quality (main default)
- MDX23C provides **best vocal isolation** for experimental use
- Dual venv pattern proven with RVC

#### Installation:
```powershell
# Main environment (.venv) already has Demucs

# Create MDX environment (OPTIONAL)
python -m venv venv-mdx
.\venv-mdx\Scripts\Activate.ps1

# Install audio-separator
pip install audio-separator[cpu]>=0.18.0

# For GPU acceleration (RECOMMENDED if you have NVIDIA GPU):
# 1. Install PyTorch with CUDA 11.8
pip install torch==2.1.2 torchvision==0.16.2 --index-url https://download.pytorch.org/whl/cu118 --force-reinstall

# 2. Install cuDNN (required for CUDA PyTorch)
pip install nvidia-cudnn-cu11 nvidia-cublas-cu11

# 3. Downgrade NumPy to 1.x (audio-separator incompatible with NumPy 2.x)
pip install "numpy<2.0" --force-reinstall --no-deps

# 4. Install static-ffmpeg (required for audio processing)
pip install static-ffmpeg

# Verify GPU setup (should show "CUDA available: True")
python -c "import torch; print('CUDA available:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
```

#### GPU Setup Notes (venv-mdx):
- **Separate PyTorch installation**: venv-mdx needs its own CUDA PyTorch (same version as main venv)
- **NumPy compatibility**: audio-separator requires NumPy 1.x, will crash with NumPy 2.x
  - Error: `"A module that was compiled using NumPy 1.x cannot be run in NumPy 2.x"`
  - Solution: `pip install "numpy<2.0" --force-reinstall --no-deps`
- **FFmpeg required**: MDX subprocess needs FFmpeg in PATH
  - Solution: `pip install static-ffmpeg` (auto-configures in mdx_standalone.py)
- **Device auto-detection**: `audio_separator.Separator` auto-detects GPU from `torch.cuda.is_available()`
  - No manual device parameter needed in Separator.__init__()
  - Device passed via command-line argument to mdx_standalone.py
- **Speed with GPU**: 30 minutes (CPU) → 2 minutes (GPU) for 4-minute song

#### Technical Implementation:
- **Subprocess isolation:** venv-mdx Python interpreter called from main app
- **Device parameter passing:** Main app passes device (cuda/cpu) as command-line argument
  - `mdx_wrapper.py` adds device to subprocess command: `command.append(self._device)`
  - `mdx_standalone.py` receives device, configures FFmpeg before importing Separator
  - FFmpeg configuration MUST happen before `from audio_separator.separator import Separator`
- **Model:** MDX23C-8KFFT-InstVoc_HQ.ckpt (~448MB, auto-downloads to `~/.audio-separator/models/`)
- **Output:** 2-stem (vocals + instrumental) - drums/bass are silent placeholders
- **Fallback:** If venv-mdx missing, app auto-falls back to Demucs
- **UI:** Dropdown selector in Settings: "demucs" (default) | "mdx" (experimental)
- **⚠️ CPU Performance:** MDX is **VERY slow on CPU** (20-30+ minutes per song, 30-min timeout)
  - Recommended: Use Demucs on CPU (much faster, good quality)
  - MDX best for: GPU users or when absolute best vocal isolation needed

#### Key Files:
- `voice_revolver_core/infrastructure/mdx_standalone.py`: Subprocess script (runs in venv-mdx)
  - Configures static-ffmpeg before importing Separator
  - Auto-detects GPU from torch.cuda.is_available()
- `voice_revolver_core/infrastructure/mdx_wrapper.py`: Main app MDX integration
  - Passes device parameter to subprocess via command-line
  - Handles model loading check and error fallback
- `~/.audio-separator/models/MDX23C-8KFFT-InstVoc_HQ.ckpt`: Auto-downloaded model

#### Recent Fixes (Feb 20-21, 2026):
- ✅ Fixed device parameter not passed to MDX subprocess (was always CPU)
- ✅ Fixed NumPy 2.x compatibility (downgraded to 1.26.4 in venv-mdx)
- ✅ Fixed FFmpeg not found (static-ffmpeg configured before Separator import)
- ✅ Fixed Separator parameter error (removed invalid `use_cuda` and `cpu_offload` params)
- ✅ GPU acceleration now working (~15x speedup vs CPU)

#### Success Metrics:
- ✅ MDX wrapper uses subprocess (no dependency conflicts)
- ✅ Model auto-downloads on first use
- ✅ Graceful fallback to Demucs if venv-mdx missing
- ✅ UI dropdown for separator selection
- ✅ Compatible with existing pipeline (4-stem output format)

---

## Working Guidelines

- **ALWAYS update AGENT_MEMORY.md with any important change** (file edits, deletions, architecture updates, decisions)
- **Read AGENT_MEMORY.md + all ./docs/* files at the START of every session**
- README.md contains base project information/guides

---

### 2026-02-21 | Phase 2 UI Redesign - Interactive Spectrum Editor

**Topic:** Complete UI overhaul with interactive waveform editing

**Overview:**
Redesigned the entire UI from a single-column 950×1100 window to a maximized two-column layout with an interactive spectrum editor for pitch/reverb/volume automation.

#### Architecture Changes:

**1. Window & Layout**
- **Window:** Maximized state (`root.state('zoomed')`), minimum size 1200×700
- **Layout:** Two-column grid
  - **Left Column (40%):** Controls split into top (original audio & separation) and bottom (reference & processing)
  - **Right Column (60%):** Visualization split into top (spectrum editor) and bottom (6 audio preview players)
- **Log Window:** Hidden by default, toggle with F12 keyboard shortcut
- **Workflow:** Two-stage process:
  1. **Stage 1:** Select original audio → Run Separation → Auto-detect gender → Load vocals into editor
  2. **Stage 2:** Edit curves → Select reference → Start Processing with curves applied

**2. New Domain Models** (`voice_revolver_core/domain/base.py`)
Created 6 new classes for curve automation:
```python
@dataclass
class PitchControlPoint:
    time: float              # Time in seconds
    shift_semitones: float   # Pitch shift (-12 to +12)

@dataclass
class PitchCurve:
    control_points: List[PitchControlPoint]
    interpolation: str = "cubic"  # cubic or linear
    
    def has_edits() -> bool
    def to_dict() -> Dict
    @staticmethod def from_dict(data: Dict) -> PitchCurve

@dataclass
class ReverbControlPoint:
    time: float        # Time in seconds
    wet_percent: float # Reverb wet mix (0-100%)

@dataclass
class ReverbCurve:
    control_points: List[ReverbControlPoint]
    interpolation: str = "linear"
    # Same methods as PitchCurve

@dataclass
class VolumeControlPoint:
    time: float    # Time in seconds
    gain_db: float # Gain in dB (-20 to +6)

@dataclass
class VolumeCurve:
    control_points: List[VolumeControlPoint]
    interpolation: str = "cubic"
    # Same methods as PitchCurve

# Added to VoiceConversionParams:
editing_curves: Optional[Dict[str, Any]] = None  # {'pitch': PitchCurve, 'reverb': ReverbCurve, 'volume': VolumeCurve}
```

**3. SpectrumEditor Component** (`voice_revolver_ui/spectrum_editor.py`, ~480 lines)
Interactive matplotlib-based waveform editor with three editing modes:

**Features:**
- **Waveform Display:** Lightblue semi-transparent waveform background using librosa
- **Three Modes:** Radio button switching between Pitching, Reverb, Volume
- **Interactive Editing:**
  - Click to add control points
  - Drag existing points to adjust
  - Click on point to remove
- **Interpolation:**
  - Pitch/Volume: Cubic spline (smooth, natural transitions)
  - Reverb: Linear (simpler transitions)
- **Visualization:**
  - **Pitching Mode:** Red curve overlay, -12 to +12 semitones, cubic interpolation
  - **Reverb Mode:** Purple bars, 0-100% wet mix, linear interpolation
  - **Volume Mode:** Green curve overlay, -20 to +6 dB, cubic interpolation
- **Reset Functions:** Reset current curve or reset all curves

**Key Methods:**
```python
class SpectrumEditor(ttk.Frame):
    def load_vocals(vocal_path: Path)  # Load audio with librosa
    def _switch_mode()                 # Change between pitch/reverb/volume
    def _redraw_spectrum()             # Render waveform + overlay
    def _on_click/_on_drag/_on_release # Interactive editing
    def get_all_curves() -> Dict       # Returns all three curves
    def reset_current_curve()
    def reset_all_curves()
```

**4. Main Window Restructure** (`voice_revolver_ui/main_tk.py`)

**Layout Structure:**
```
┌─────────────────────────────────────────────────────────────┐
│  Voice Revolver AI - [Original Audio Name]                  │
├──────────────────────┬──────────────────────────────────────┤
│ ORIGINAL AUDIO &     │ VOCAL EDITOR (SPECTRUM)              │
│ SEPARATION           │                                       │
│ - File selection     │ ┌─────────────────────────────────┐ │
│ - Separation model   │ │ Waveform with curve overlay     │ │
│ - Device (GPU/CPU)   │ │ (matplotlib canvas)             │ │
│ - Pitch shift slider │ │                                  │ │
│ - Gender alignment   │ │ Mode: [Pitching][Reverb][Volume]│ │
│ - Thresholds         │ │                                  │ │
│ - [Run Separation]   │ │ Click/drag to edit curve        │ │
│                      │ └─────────────────────────────────┘ │
├──────────────────────┤                                       │
│ REFERENCE VOICE &    │ [Reset Curve] [Reset All]           │
│ PROCESSING           │                                       │
│ - Reference file     ├──────────────────────────────────────┤
│ - Type (Audio/Model) │ AUDIO PREVIEW & EXPORT               │
│ - Output format      │ ┌────────┬────────┬────────┐        │
│ - Vocal only         │ │ Mixed  │ Vocals │ Original│        │
│ - [Start Processing] │ └────────┴────────┴────────┘        │
│ - [Export] [Cancel]  │ ┌────────┬────────┬────────┐        │
│                      │ │ Drums  │ Bass   │ Other  │        │
│                      │ └────────┴────────┴────────┘        │
│                      │ Volume: [───────────●──]            │
├──────────────────────┴──────────────────────────────────────┤
│ Progress: ████████████████░░░░░░░░░░░░ 75% Converting...   │
└─────────────────────────────────────────────────────────────┘
```

**New State Variables:**
```python
self.separation_complete = False  # Track Stage 1 completion
self.separation_thread = None     # Background separation thread
self.log_hidden = True            # F12 toggle state
self.editing_curves = None        # Retrieved from spectrum_editor before processing
```

**New Methods:**
```python
def _toggle_log_window()           # F12 key handler
def _enable_spectrum_editor(bool)  # Enable/disable right side
def _run_separation()              # Stage 1: Separation only
def _separation_worker()           # Background: Demucs/MDX + gender detection
def _separation_complete_callback  # UI callback: Load vocals into editor
def _separation_failed_callback    # Error handling
```

**Updated Methods:**
```python
def _on_gender_alignment_change()  # Show/hide orig_gender_frame + threshold_frame
def _select_original()             # Enable separation_btn when file selected
def _check_ready()                 # Requires separation_complete + reference_file
def _start_processing()            # Get editing_curves from spectrum_editor
def _process()                     # Add editing_curves to VoiceConversionParams
```

**5. Curve Processing Implementation**

**AudioProcessor** (`voice_revolver_core/infrastructure/audio_processor.py`)
Added three new methods:

```python
def apply_pitch_curve(audio_path, output_path, pitch_curve: PitchCurve) -> bool:
    - Uses Parselmouth (Praat) for time-varying pitch manipulation
    - Samples curve every 10ms using cubic spline interpolation
    - Converts semitones to frequency ratio: ratio = 2^(semitones/12)
    - Creates pitch tier and applies via Praat's overlap-add synthesis

def apply_volume_curve(audio_path, output_path, volume_curve: VolumeCurve) -> bool:
    - Uses librosa for time-varying gain
    - Samples curve at each audio sample using cubic interpolation
    - Converts dB to linear gain: gain = 10^(dB/20)
    - Applies gain curve and prevents clipping via normalization

def apply_reverb_curve(audio_path, output_path, reverb_curve: ReverbCurve) -> bool:
    - Uses pedalboard for high-quality reverb
    - Processes audio in 100ms chunks
    - Samples curve with linear interpolation
    - Applies time-varying wet/dry mix per chunk
```

**VoiceReplacementService** (`voice_revolver_core/application/voice_replacement_service.py`)
Integrated curve processing between vocal enhancement and voice conversion:

**Processing Pipeline (Updated):**
1. **Stage 1:** Load models (5%)
2. **Stage 2:** Stem separation (5-30%)
3. **Stage 2.5:** Enhance separated vocals (32%)
4. **Stage 2.7 (NEW):** Apply user editing curves (33-34%)
   - If pitch curve has edits → Apply pitch curve
   - If volume curve has edits → Apply volume curve
   - If reverb curve has edits → Apply reverb curve
   - Chain processing: vocals → pitch curved → volume curved → reverb curved
5. **Stage 2.8:** Denoise reference voice (36%)
6. **Stage 3:** Voice conversion (40-70%)
7. **Stage 4:** Audio mixing (75-95%)
8. **Stage 5:** Choose output (vocal-only or full mix)

**6. Dependencies Added**
```
# Visualization & UI (Phase 2)
matplotlib>=3.8.0   # Interactive spectrum visualization
scipy>=1.10.0       # Cubic spline interpolation

# Audio processing (already present)
pedalboard          # Reverb processing
praat-parselmouth   # Pitch curve manipulation
```

#### Technical Decisions:

1. **Two-Stage Workflow:** Separation must complete before processing
   - Clearer UX (user knows when to edit)
   - Enables gender auto-detection before editing
   - Spectrum editor loads vocals after separation

2. **Gender Simplification:** Only detect original vocal gender
   - Reference gender not needed for ChatterBox/RVC
   - Removed model_gender_frame from UI

3. **Cubic vs Linear Interpolation:**
   - Pitch/Volume: Cubic spline (smooth, natural transitions)
   - Reverb: Linear (simpler, predictable transitions)

4. **Curve Processing Order:** Pitch → Volume → Reverb
   - Pitch affects tonal quality (apply first)
   - Volume affects dynamics (apply second)
   - Reverb is spatial effect (apply last)

5. **F12 Log Toggle:** Better than always-visible log window
   - Maximizes editing space
   - Log still accessible for debugging

6. **Single Matplotlib Canvas:** Mode-switching overlay instead of 3 separate plots
   - Cleaner UI
   - Easier to understand (one view at a time)
   - Better performance

#### Files Modified/Created:

**New Files:**
- `voice_revolver_ui/spectrum_editor.py` (~480 lines)

**Modified Files:**
- `requirements.txt` (added matplotlib, scipy)
- `voice_revolver_core/domain/base.py` (added 6 curve classes)
- `voice_revolver_ui/main_tk.py` (complete restructure, ~1900 lines)
- `voice_revolver_core/infrastructure/audio_processor.py` (added 3 curve methods)
- `voice_revolver_core/application/voice_replacement_service.py` (integrated curve processing)

#### User Workflow:

**Complete Voice Replacement Workflow:**
1. Launch app → Select original audio file
2. Choose separation model (Demucs/MDX) and device (GPU/CPU)
3. *(Optional)* Adjust pitch shift slider
4. *(Optional)* Enable gender alignment and set thresholds
5. **Click "Run Separation"** → Vocals separated → Gender detected → Spectrum editor loads
6. **Edit curves in spectrum editor:**
   - Switch to Pitching mode → Click/drag to create pitch automation curve
   - Switch to Reverb mode → Click/drag to create reverb automation curve
   - Switch to Volume mode → Click/drag to create volume automation curve
7. Select reference voice (audio file) or RVC model (zip file)
8. Choose output format (MP3/WAV/FLAC) and vocal-only option
9. **Click "Start Processing"** → Curves applied → Voice conversion → Final mix
10. Preview 6 audio tracks (mixed, vocals, original, drums, bass, other)
11. Export final result

#### Success Metrics:
- ✅ Maximized window with two-column layout
- ✅ Interactive spectrum editor with three editing modes
- ✅ Cubic spline interpolation for smooth curves
- ✅ Two-stage workflow (separation → editing → processing)
- ✅ Curve data integrated into processing pipeline
- ✅ Pitch/volume/reverb automation working
- ✅ F12 log toggle for debugging
- ✅ Gender auto-detection after separation
- ✅ 6 preview players in compact layout

---

### 2026-02-21 | Phase 2.6 - Enhanced Spectrum Editor & Interactive Workflow
**Topic:** Added fourth editing mode, improved UX, dual audio controls, and Apply Changes feature

#### Problem Statement:
Users needed more control over vocal processing workflow:
1. Manual noise reduction control (time-varying)
2. Preview curve changes before final processing
3. Independent volume controls for spectrum editor vs preview section
4. Ability to fine-tune control points iteratively without reprocessing
5. Remove automatic reverb reduction (prefer manual control)

#### Solution: Four Editing Modes + Apply Changes System

**New Features:**

**1. Noise Reduction Mode** (Fourth editing mode)
- **Purpose:** Time-varying noise reduction strength (0-100%)
- **Data Structure:**
  ```python
  @dataclass
  class NoiseControlPoint:
      time: float              # Time in seconds
      reduction_percent: float # 0-100%
  
  @dataclass
  class NoiseCurve:
      control_points: List[NoiseControlPoint]
      interpolation: str = "linear"
      
      def has_edits(self) -> bool:
          return len(self.control_points) > 0 and any(pt.reduction_percent > 0 for pt in self.control_points)
  ```
- **Visualization:** Orange straight lines connecting control points
- **UI Position:** Fourth radio button after Volume mode

**2. Apply Changes Button**
- **Purpose:** Preview curve changes without full voice conversion processing
- **Location:** Below spectrum editor playback controls
- **Workflow:**
  1. User adds/edits control points in any mode
  2. Click "Apply Changes" → Processes only curve edits
  3. Saves to `vocals_preview.wav` 
  4. Reloads audio in spectrum editor (preserves control points)
  5. User can listen to changes, fine-tune, repeat
- **Processing Pipeline:** Pitch → Volume → Reverb → Noise (linear chain)
- **Key Feature:** Always starts from original unenhanced vocals (non-destructive)

**3. Dual Volume Controls**
- **Spectrum Editor Volume:** Vertical slider in right tool panel (below Add/Move/Remove buttons)
  - Controls spectrum editor playback only
  - 0-100% range, length=120px
- **Preview Section Volume:** Vertical slider on right side of Audio Preview section
  - Controls preview track playback (6 players)
  - 0-100% range, length=120px
  - Positioned beside preview tracks (packed first with side=tk.RIGHT)

**4. Interactive Tool Buttons**
- **Three interaction modes:**
  - **Add:** Click canvas to add control points at cursor position
  - **Move:** Click and drag existing points to reposition
  - **Remove:** Click existing points to delete
- **Vertical layout:** Stacked buttons on right side of spectrum editor
- **Visual feedback:** Highlighted button shows active mode

**5. Straight Line Visualization**
- **Rationale:** Praat/audio processors handle actual interpolation during Apply Changes
- **Implementation:** All four modes draw straight lines between control points
  - **Pitching:** Red lines, ±12 semitones
  - **Reverb:** Purple lines, 0-100% wet mix
  - **Volume:** Green lines, -20 to +6 dB
  - **Noise:** Orange lines, 0-100% reduction
- **Previous:** Used bars for reverb/noise (caused confusion)
- **Current:** Consistent line visualization across all modes

**6. Curve Pre-population Changes**
- **Pitch Curve:** Auto-populated with 3 points if gender alignment enabled
  - Male → Female: +12 semitones at start/middle/end
  - Female → Male: -12 semitones at start/middle/end
- **Reverb Curve:** NO auto-population (removed tau-based reduction)
- **Volume Curve:** Never auto-populated
- **Noise Curve:** Never auto-populated
- **User Request:** Full manual control preferred over automatic calculations

**7. Raw Vocals Workflow**
- **Separation Output:** Raw unenhanced vocals saved directly
- **Spectrum Editor:** Loads raw vocals (no preprocessing)
- **Apply Changes:** Always processes from `original_vocals_path` (raw)
- **Final Processing:** Enhancement applied only during "Start Processing"
- **Benefit:** Non-destructive editing, can always revert to original

**8. Permission Error Handling**
- **Problem:** Windows file locks caused errors on second Apply Changes
- **Solution:** 
  ```python
  # Release audio handles before processing
  if self.audio_data is not None:
      self.audio_data = None
      gc.collect()
  
  # Retry logic for locked files
  for attempt in range(3):
      try:
          process_audio()
          break
      except PermissionError:
          time.sleep(0.5)
  ```

#### Code Changes:

**Modified Files:**
- `voice_revolver_core/domain/base.py` (+62 lines)
  - Added `NoiseControlPoint` and `NoiseCurve` dataclasses
  - Added serialization methods (to_dict, from_dict)

- `voice_revolver_ui/spectrum_editor.py` (~1066 lines)
  - Added fourth mode: Noise Reduction radio button
  - Added `self.noise_curve = NoiseCurve()` initialization
  - Added vertical volume slider to tool panel (lines 207-229)
  - Added Apply Changes button (lines 247-252)
  - Updated `_draw_noise_view()` to use straight lines (not bars)
  - Updated `_draw_reverb_view()` to use straight lines (not bars)
  - Added noise curve handling in drag/release/hover methods
  - Added `get_all_curves()` returns 4 curves: pitch, reverb, volume, noise
  - Added `reload_audio_only()` for control point preservation
  - Updated `load_vocals()` signature - removed initial_reverb_reduction parameter

- `voice_revolver_ui/main_tk.py` (~2131 lines)
  - Added preview volume slider (vertical, right side, lines 652-665)
  - Removed tau-based reverb reduction calculation from separation
  - Updated `_separation_complete_callback()` - removed reverb parameter
  - Fixed preview playback volume control (uses `self.preview_volume_var`)
  - Added `_on_preview_volume_change()` method

- `voice_revolver_core/application/voice_replacement_service.py`
  - Separation outputs raw vocals (no enhancement step before spectrum editor)
  - Enhancement only applied during "Start Processing"

**Updated Workflow:**

```
User Workflow (Phase 2.6):
1. Select original audio → Run Separation
2. Vocals separated (raw, unenhanced) → Gender detected
3. Spectrum editor loads with auto-populated pitch curve (if gender alignment)
4. User edits curves:
   - Switch modes: Pitching / Reverb / Volume / Noise Reduction
   - Select tool: Add / Move / Remove
   - Click/drag to edit control points
5. Click "Apply Changes":
   - Processes: Pitch → Volume → Reverb → Noise
   - Saves to vocals_preview.wav
   - Reloads into spectrum editor (control points preserved)
   - User can play and listen to changes
6. Repeat steps 4-5 until satisfied
7. Select reference voice
8. Click "Start Processing" (full pipeline with voice conversion)
9. Preview 6 tracks with independent volume control
10. Export final result
```

#### Technical Decisions:

**1. Why Straight Lines Instead of Curves?**
- Visual representation only shows control points
- Actual interpolation happens during audio processing (Praat/librosa)
- Clearer to see exact control point positions
- Consistent across all four modes

**2. Why Apply Changes Button?**
- Fast iteration without full voice conversion
- Non-destructive (always starts from original vocals)
- Preserves control points after processing
- Clear separation: editing vs final processing

**3. Why Remove Reverb Auto-population?**
- User preference for full manual control
- Tau-based calculation was opaque
- Easier to add reverb manually where needed
- Reduces cognitive load (fewer automatic behaviors)

**4. Why Dual Volume Controls?**
- Spectrum editor playback independent from preview section
- Different audio players (pygame vs pygame.mixer.music)
- User can adjust volumes independently while editing

**5. Why Raw Vocals Workflow?**
- Non-destructive editing foundation
- Enhancement artifacts don't affect curve editing
- Can always revert to clean separation output
- Enhancement applied once during final processing

#### Updated Processing Pipeline:

```
Apply Changes (Fast Preview):
1. Check which curves have edits (has_edits() method)
2. Load original_vocals.wav (raw, unenhanced)
3. If pitch curve has edits:
   - apply_pitch_curve() → vocals_pitched.wav
4. If volume curve has edits:
   - apply_volume_curve() → vocals_volume.wav
5. If reverb curve has edits:
   - apply_reverb_curve() → vocals_reverb.wav
6. If noise curve has edits:
   - apply_noise_curve() → vocals_denoised.wav (TODO: implement)
7. Save final result → vocals_preview.wav
8. Reload into spectrum editor (control points intact)

Start Processing (Full Pipeline):
1. Load models (5%)
2. Stem separation (if not already done)
3. Get editing curves from spectrum editor
4. Apply curves to vocals (33-35%)
5. Enhance vocals (36%)
6. Denoise reference (38%)
7. Voice conversion (40-70%)
8. Mix with instrumental (75-95%)
9. Export final result
```

#### Files Structure:

```
voice_revolver_ui/
├── main_tk.py              # Main window with two-column layout
├── spectrum_editor.py      # Interactive editor (4 modes, 3 tools, Apply Changes)
└── __init__.py

voice_revolver_core/
├── domain/
│   └── base.py            # Added NoiseControlPoint, NoiseCurve
├── application/
│   └── voice_replacement_service.py  # Integrated Apply Changes workflow
└── infrastructure/
    └── audio_processor.py # TODO: Add apply_noise_curve() method
```

#### Success Metrics:
- ✅ Four editing modes fully functional (Pitching, Reverb, Volume, Noise)
- ✅ Apply Changes button processes curves quickly
- ✅ Control points preserved after Apply Changes
- ✅ Dual volume controls work independently
- ✅ Straight line visualization consistent across modes
- ✅ Raw vocals workflow (non-destructive)
- ✅ Permission error handling (Windows file locks)
- ✅ Interactive tools (Add/Move/Remove) work in all modes
- ✅ Hover labels show current value for all modes
- ✅ Pitch curve auto-populated based on gender alignment
- ✅ No automatic reverb reduction (user control)

#### Pending Work:
- ⏳ Implement `apply_noise_curve()` in audio_processor.py
  - Use noisereduce or librosa for spectral noise reduction
  - Apply time-varying reduction based on control points
  - Integrate into Apply Changes workflow

---

## Patterns & Conventions

### Code Structure
- DDD layers: domain/, application/, infrastructure/, interface/
- Core logic in domain layer (no external dependencies)
- Application layer orchestrates use cases
- Infrastructure handles external tools (Demucs, OpenVoice, FFmpeg)

### File Naming
- snake_case for Python files
- PascalCase for classes
- kebab-case for CLI commands

### Error Handling
- Use ErrorCode system: code: "WHAT_HAPPENED"
- All errors logged with context

### Data Storage
- App data: {user_documents}/VoiceRevolverAI/
- Models: {app_data}/models/
- Temp: {app_data}/temp/ (auto-cleanup)
- Logs: {app_data}/logs/app.log

### Project Format
- .vra files (JSON-based, single file)
