# Agent Memory

> This file serves as AI memory for the project. Update it with important highlights after each session. Git-sync across machines.

## Summary

Voice Revolver AI - A local-first desktop application for vocal replacement in songs. Uses AI (Demucs + OpenVoice) to separate vocals from a song and replace them with a reference voice. Built with DDD architecture for modularity.

**Current State:** Core structure implemented, UI ready, needs ML model integration
**Goal:** Portable desktop app (Windows .exe, Mac .app)

---

## Project Design

### Architecture
- **Pattern:** Domain-Driven Design (DDD)
- **Layers:** Domain → Application → Infrastructure → Interface (UI)

### DDD Core Components
1. **StemSeparator** - Demucs for stem separation (vocals, drums, bass, other)
2. **VoiceConverter** - OpenVoice V2 for voice conversion
3. **AudioMixer** - Combine vocals + instrumental
4. **FormatConverter** - pydub for format conversion (WAV ↔ MP3/FLAC)
5. **VoiceTransformer** - Pitch + Emotion control
6. **FileManager** - Temp files, export workflow, auto-naming (date_time_random)
7. **ProgressTracker** - Track progress with unique keys for polling
8. **ErrorCode** - Global error system (code: "WHAT_HAPPENED")
9. **ModelManager** - Auto-download models on first startup
10. **ProjectService** - Save/load .vra project files

### Tech Stack
- **Language:** Python 3.10+
- **UI Framework:** PyQt/PySide
- **ML Models:** Demucs, OpenVoice V2
- **Audio:** pydub, FFmpeg (bundled + auto-download)
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

## History Log

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

---

## Working Guidelines

- **ALWAYS update AGENT_MEMORY.md with any important change** (file edits, deletions, architecture updates, decisions)
- **Read AGENT_MEMORY.md + all ./docs/* files at the START of every session**
- README.md contains base project information/guides

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
