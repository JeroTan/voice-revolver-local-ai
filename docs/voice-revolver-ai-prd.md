# Product Requirements Document: Voice Revolver AI

**Version**: 1.1 (Dual-Reference Update)  
**Date**: 2026-02-20  
**Author**: Sarah (Product Owner)  
**Quality Score**: 100/100

**Version History:**
- **v1.1** (2026-02-20): Added dual-reference voice conversion (Audio + Model modes), Applio RVC integration
- **v1.0** (2026-02-18): Initial release with ChatterBox VC

---

## Executive Summary

Voice Revolver AI is a local-first desktop application that enables users to replace vocals in any song with a reference voice. The system uses AI-powered stem separation (Demucs) to isolate vocals and instrumental tracks, then applies voice conversion using **dual-reference modes**:

1. **Audio Reference Mode (ChatterBox VC)**: Zero-shot voice cloning from 5-30 second audio samples
2. **Model Reference Mode (RVC via Applio)**: High-quality conversion using pre-trained voice models

All processing is done locally on the user's machine—no cloud dependency required.

The core business logic is built using Domain-Driven Design (DDD) architecture, with a dual virtual environment strategy to support both conversion engines simultaneously while avoiding dependency conflicts.

**Key Innovation**: First desktop app to offer BOTH audio-based and model-based voice conversion in a single unified interface.

---

## Problem Statement

**Current Situation**: Users who want to create karaoke versions or replace vocals in songs must rely on cloud-based services or expensive studio software. Existing solutions often require internet connection, have file size limits, or charge per conversion.

**Proposed Solution**: A portable desktop application that runs locally, using state-of-the-art AI models (Demucs for stem separation, ChatterBox VC for voice conversion) to provide unlimited vocal replacement without internet dependency after initial model download.

**Business Impact**: Democratizes AI audio manipulation for individual users and hobbyists who need a free, unlimited, privacy-friendly tool for vocal replacement and voice conversion experiments.

---

## Success Metrics

**Primary KPIs:**
- **Processing Time**: Complete vocal replacement within 3x the duration of the input audio (e.g., 3-minute song = ~9 minutes processing on GPU)
- **Model Load Time**: First model load under 30 seconds on standard hardware
- **User Satisfaction**: Successful completion rate of conversions (no crashes/soft failures)
- **Offline Capability**: Full functionality without internet after initial setup

**Validation**: Automated performance benchmarking on standard test hardware; user feedback collection via in-app rating system.

---

## User Personas

### Primary: Music Hobbyist
- **Role**: Home musician, karaoke enthusiast
- **Goals**: Create karaoke tracks, experiment with voice cloning for fun
- **Pain Points**: Limited free cloud conversions, privacy concerns with uploading personal voice samples
- **Technical Level**: Novice to Intermediate

### Secondary: Content Creator
- **Role**: YouTube/TikTok creator needing custom vocal tracks
- **Goals**: Quick turnaround, reliable results, no recurring costs
- **Pain Points**: Subscription costs for cloud services, upload/download wait times
- **Technical Level**: Intermediate

---

## User Stories & Acceptance Criteria

### Story 1: Vocal Replacement Workflow

**As a** music hobbyist
**I want to** load a song and a reference voice sample
**So that** I can hear my song with vocals replaced by the reference voice

**Acceptance Criteria:**
- [ ] User can drag/drop or browse to select original song file (MP3, WAV, FLAC, OGG)
- [ ] User can drag/drop or browse to select reference voice audio file
- [ ] System processes the audio through stem separation → voice conversion → mixing
- [ ] User can preview the result with play/pause/seek controls
- [ ] User can export the result to a chosen location with custom filename
- [ ] Progress is displayed during all processing stages

### Story 2: Model & Dependency Management

**As a** user running the app for the first time
**I want the** necessary models and FFmpeg to download automatically
**So that** I can start using the app immediately

**Acceptance Criteria:**
- [ ] On first launch, app detects missing models and FFmpeg
- [ ] Download progress is shown for each model (StemSeparator, VoiceConverter)
- [ ] Terminal window displays real-time download/logging information
- [ ] After download, subsequent launches skip download and start immediately
- [ ] App works fully offline after initial setup

### Story 3: Project Management

**As a** user working on multiple songs
**I want to** save and load my work sessions
**So that** I can continue later without re-selecting files

**Acceptance Criteria:**
- [ ] User can save current session as a `.vra` project file
- [ ] Project file contains all references, settings, and processing state
- [ ] User can open existing `.vra` files to resume work
- [ ] User can rename and choose export location during export

### Story 4: Compute Control

**As a** user with specific hardware preferences
**I want to** choose between CPU and GPU processing
**So that** I can optimize for my available hardware

**Acceptance Criteria:**
- [ ] App auto-detects GPU availability and suggests appropriate option
- [ ] User can manually override to use CPU even if GPU is available
- [ ] Settings persist between sessions

### Story 5: Preview & Export

**As a** user wanting to review before saving
**I want to** preview the processed audio
**So that** I can decide whether to re-process with different settings

**Acceptance Criteria:**
- [ ] Preview player shows play/pause button
- [ ] Preview player displays current time and total duration
- [ ] Preview player has seekable timeline slider
- [ ] User can export in multiple formats (WAV, MP3, FLAC)

---

## Functional Requirements

### Core Features

#### Feature 1: Stem Separation (StemSeparator)
- **Description**: Uses Demucs to separate audio into stems (vocals, drums, bass, other)
- **Input**: Audio file (MP3, WAV, FLAC, OGG)
- **Output**: Dictionary of stems {vocals, drums, bass, other}
- **Models**: htdemucs_ft (default, best quality)
- **Edge Cases**: 
  - Mono files: Convert to stereo before processing
  - Very short files (<5 seconds): Show warning, proceed anyway
  - Very long files (>15 minutes): Show estimated time, allow cancel
- **Error Handling**: If model fails to load, show error with code STEM_LOAD_FAILED

#### Feature 2: Voice Conversion (VoiceConverter)
- **Description**: Uses ChatterBox VC (Resemble AI) to convert original vocals to match reference voice
- **Input**: Original vocal track, reference voice audio
- **Output**: Converted vocal track
- **Models**: ChatterBox VC (22K+ stars, state-of-the-art quality)
- **Edge Cases**:
  - Reference audio too short (<5 seconds): ChatterBox may still work but quality degrades
  - Reference audio noisy: ChatterBox handles noise robustly
  - Language mismatch: ChatterBox handles cross-lingual voice conversion
- **Error Handling**: Error codes VOICE_CONVERT_FAILED, REFERENCE_TOO_SHORT
- **Fallback**: OpenVoice V2 wrapper kept for legacy compatibility (can switch back if needed)

#### Feature 2.1: Dual-Reference Voice Conversion (MAJOR FEATURE)
- **Description**: Revolutionary dual-mode voice conversion system supporting two distinct approaches
- **Reference Modes**:
  1. **Audio Reference (ChatterBox VC)**:
     - User provides 5-30 second audio sample of target voice
     - Zero-shot voice cloning (no training required)
     - Fast inference (~30s for 3-minute song)
     - Best for natural speech, podcasts, dialogue
     - Model: ChatterBox VC v0.1.6
  
  2. **Model Reference (RVC via Applio)**:
     - User provides pre-trained RVC model (.zip with .pth + .index)
     - High-quality voice cloning with trained model characteristics
     - Supports pitch shifting, formant control, voice style preservation
     - Best for singing voice conversion, character voices
     - Framework: Applio (actively maintained, Feb 2026)
     - F0 Methods: RMVPE (default), Crepe, FCPE, hybrid combinations
     - Embedders: ContentVec (default), Spin, language-specific HuBERT variants

- **Technical Architecture**:
  - **Dual Virtual Environments**:
    - Main (.venv): ChatterBox, Demucs, UI dependencies (numpy 1.25.2)
    - RVC (venv-rvc): Applio dependencies (numpy 2.3.5)
  - **Subprocess Isolation**: RVC runs in separate Python process to avoid dependency conflicts
  - **Model Management**: Auto-extraction of .zip models, FAISS index loading, temp cleanup

- **UI/UX**:
  - Toggle between "Audio" and "Model" reference modes
  - File picker adapts: .wav/.mp3 for Audio mode, .zip for Model mode
  - Informational dialog explains RVC requirements (not warning/blocker)
  - Same processing pipeline, different conversion engine

- **RVC Model Format**:
  - `.zip` archive containing:
    - `.pth` file: PyTorch checkpoint with trained voice model weights
    - `.index` file: FAISS retrieval index for speaker features
  - Models trained externally using RVC training pipeline
  - Sample rate: 40kHz (auto-detected from model config)

- **RVC Processing Parameters**:
  - Pitch shift: -24 to +24 semitones
  - Index rate: 0.0-1.0 (feature retrieval influence)
  - Volume envelope: 0.0-1.0 (RMS mix rate)
  - Protect: 0.0-0.5 (consonant protection)
  - F0 method: RMVPE, Crepe, FCPE, hybrid combinations
  - Embedder: ContentVec, Spin, language-specific variants

- **Installation Requirements**:
  ```powershell
  # Standard installation creates both environments
  # See docs/technical-implementation-guide.md for full setup
  ```

- **Edge Cases**:
  - Missing venv-rvc: Error code RVC_ENV_NOT_FOUND
  - Corrupted .zip model: Error code RVC_MODEL_INVALID
  - Missing RMVPE predictor: Auto-download (137MB) on first use
  - Missing embedder model: Auto-download from HuggingFace

- **Error Handling**: 
  - RVC_ENV_NOT_FOUND: venv-rvc not installed
  - RVC_MODEL_INVALID: Corrupted or invalid .zip file
  - RVC_SUBPROCESS_FAILED: Subprocess crashed (check stderr logs)
  - VOICE_CONVERT_FAILED: General conversion failure

- **Performance**:
  - ChatterBox (Audio mode): ~30s for 3-minute song
  - RVC (Model mode): ~45-60s for 3-minute song (CPU), ~15s (GPU)
  - Memory: +300MB peak when RVC subprocess active

#### Feature 3: Audio Mixing (AudioMixer)
- **Description**: Combines converted vocals with original instrumental stems
- **Input**: Converted vocals, instrumental tracks (drums, bass, other)
- **Output**: Final mixed audio
- **Edge Cases**:
  - Volume imbalance: Apply automatic loudness normalization
  - Timing mismatch: Align vocals to original timing
- **Error Handling**: Error code MIX_FAILED

#### Feature 4: Format Conversion (FormatConverter)
- **Description**: Converts between audio formats using pydub/FFmpeg
- **Input**: Audio file, target format
- **Supported Formats**: WAV, MP3, FLAC, OGG, AAC
- **Export Options**: 
  - WAV: Uncompressed, highest quality
  - MP3: 320kbps default
  - FLAC: Lossless compression
- **Error Handling**: Error code CONVERT_FAILED, UNSUPPORTED_FORMAT

#### Feature 5: Voice Transformation (VoiceTransformer)
- **Description**: Applies pitch adjustment and optional emotion control
- **Parameters**:
  - Pitch: -12 to +12 semitones
  - Note: ChatterBox VC auto-optimizes voice characteristics (no manual style controls)
  - Legacy: OpenVoice style parameters available if using OpenVoice wrapper
- **Edge Cases**: Extreme pitch values may cause artifacts—show warning
- **Error Handling**: Error code TRANSFORM_FAILED

#### Feature 6: File Management (FileManager)
- **Description**: Handles temp file storage, export workflow, and file naming
- **Auto-naming**: `{date}_{time}_{random}.{format}` (e.g., 2026-02-18_143052_aXb3kL9p.mp3)
- **Temp Location**: App data folder (cleared on app close)
- **Export Flow**: 
  1. Get processed temp file
  2. Convert to requested format (via FormatConverter)
  3. Store in export location with user-specified name
- **Error Handling**: Error code FILE_WRITE_FAILED, FILE_NOT_FOUND

#### Feature 7: Progress Tracking (ProgressTracker)
- **Description**: Tracks processing progress with unique keys for polling
- **API**:
  - `start_task(name)` → returns task_key (e.g., "abc-123")
  - `update_progress(key, percentage, stage)` → updates state
  - `get_progress(key)` → returns {stage, percentage, status}
  - `cancel(key)` → cancels task
- **Stages**: LOADING_MODELS → STEM_SEPARATION → VOICE_CONVERSION → MIXING → COMPLETE

#### Feature 8: Error Code System (ErrorCode)
- **Description**: Global error system for consistent error handling
- **Format**: `code: "WHAT_HAPPENED"` (e.g., "STEM_LOAD_FAILED: Model file corrupted")
- **Standard Codes**:
  - STEM_LOAD_FAILED
  - STEM_SEPARATION_FAILED
  - VOICE_CONVERT_FAILED
  - REFERENCE_TOO_SHORT
  - MIX_FAILED
  - CONVERT_FAILED
  - UNSUPPORTED_FORMAT
  - FILE_WRITE_FAILED
  - FILE_NOT_FOUND
  - GPU_NOT_AVAILABLE
  - CANCELLED

#### Feature 9: Model Management (ModelManager)
- **Description**: Auto-downloads and caches AI models
- **Behavior**:
  - On first launch: Download all models with progress UI
  - On subsequent launches: Check cache, skip download if present
  - Models stored in: `{app_data}/models/`
- **Models Required**:
  - Demucs stem separation model
  - OpenVoice V2 checkpoint
- **Error Handling**: Error code MODEL_DOWNLOAD_FAILED

#### Feature 10: Project Service (ProjectService)
- **Description**: Save/load user project sessions
- **Format**: `.vra` (JSON-based, single file)
- **Contents**:
  - Original file path
  - Reference voice file path
  - Settings (pitch, emotion, output format)
  - Processing state
  - Export history
- **Edge Cases**:
  - Original file moved: Prompt user to locate file
  - Reference file moved: Prompt user to locate file

### Out of Scope
- Real-time voice conversion (streaming)
- Video lip-sync
- Batch processing (multiple songs at once)
- Cloud deployment/API (reserved for future)
- Mobile platform support

---

## Technical Constraints

### Performance
- **GPU Processing**: 3x realtime (3-minute song = ~9 minutes)
- **CPU Processing**: 10x+ slower (inform user)
- **Memory**: Peak ~8GB RAM during processing
- **Storage**: ~3GB for models, ~2GB temp during processing

### Security
- **Local Processing Only**: No data leaves user's machine
- **File Access**: Only access user-selected files
- **No Telemetry**: No usage data collected

### Integration
- **Demucs**: Stem separation (vocal removal)
- **ChatterBox VC**: Zero-shot voice conversion from audio samples (Primary - Audio Reference Mode)
- **Applio RVC**: Model-based voice conversion using pre-trained RVC models (Primary - Model Reference Mode)
- **pydub**: Format conversion
- **FFmpeg**: Audio processing backend (bundled + auto-download)
- **Parselmouth**: Pitch manipulation (optional enhancement)

### Technology Stack
- **Language**: Python 3.11+
- **Voice Conversion**: 
  - ChatterBox VC v0.1.6 (Audio Reference Mode)
  - Applio RVC (Model Reference Mode, Feb 2026 release)
- **Dual Environment Strategy**:
  - Main environment (.venv): ChatterBox, Demucs, UI (numpy 1.25.2)
  - RVC environment (venv-rvc): Applio dependencies (numpy 2.3.5)
- **UI Framework**: Tkinter (native Python)
- **Packaging**: PyInstaller/Nuitka (portable EXE)
- **Platforms**: Windows (.exe), macOS (.app)
- **Build**: Separate build on each target platform

### Infrastructure
- **App Data**: `{user_documents}/VoiceRevolverAI/`
- **Models**: `{app_data}/models/`
- **Temp Files**: `{app_data}/temp/` (auto-cleanup on close)
- **Logs**: `{app_data}/logs/app.log`
- **Settings**: `{app_data}/settings.json`

---

## MVP Scope & Phasing

### Phase 1: MVP (Required for Initial Launch)
- Stem separation via Demucs
- Voice conversion via ChatterBox VC
- Vocal enhancement (noisereduce, pedalboard, pyloudnorm)
- Basic audio mixing
- Preview with play/pause/seek (5 separate tracks)
- Export to WAV/MP3
- Model auto-download on startup
- FFmpeg auto-download
- Progress tracking
- Error code system
- File caching cleanup
- File naming (auto date_time_random)
- Basic project save/load (.vra)
- GPU/CPU selection with suggestion
- Terminal window visible
- Temp file cleanup on close

### Phase 2: Enhancements - ✅ COMPLETED (2026-02-21)

**Phase 2.1-2.5: Interactive Spectrum Editor** (Completed)
- ✅ Format converter (FLAC, OGG, AAC, WAV export)
- ✅ Voice transformation (pitch automation curves)
- ✅ Custom output naming at export
- ✅ User-selectable output folder
- ✅ Cancel processing button
- ✅ Advanced project management (.vra save/load)
- ✅ Settings persistence
- ✅ Interactive waveform editor with matplotlib
- ✅ Three automation curves: Pitching, Reverb, Volume
- ✅ Cubic spline interpolation for smooth transitions
- ✅ Two-stage workflow (separation → editing → processing)
- ✅ Gender auto-detection after separation
- ✅ F12 log window toggle
- ✅ 6-track preview player with play/pause/seek
- ✅ Maximized dual-column layout

**Phase 2.6: Enhanced Interactive Workflow** (Completed)
- ✅ **Noise Reduction Mode**: Fourth editing mode with time-varying noise reduction (0-100%)
- ✅ **Apply Changes Button**: Fast preview of curve edits without full voice conversion
- ✅ **Dual Volume Controls**: Independent sliders for spectrum editor and preview section
- ✅ **Interactive Tools**: Add/Move/Remove modes for control point editing
- ✅ **Straight Line Visualization**: Consistent across all four editing modes
- ✅ **Raw Vocals Workflow**: Non-destructive editing always from original unenhanced vocals
- ✅ **Control Point Preservation**: Curves maintained after Apply Changes
- ✅ **Manual Curve Control**: Removed automatic reverb reduction, user has full control
- ✅ **Pitch Auto-population**: Optional gender-based pitch curve initialization
- ✅ **Permission Error Handling**: Windows file lock retry logic
- ✅ **Hover Labels**: Real-time value display for all editing modes

**Four Editing Modes:**
1. **Pitching**: ±12 semitones pitch automation (red curve)
2. **Reverb**: 0-100% wet mix reverb strength (purple curve)
3. **Volume**: -20 to +6 dB gain automation (green curve)
4. **Noise Reduction**: 0-100% noise reduction strength (orange curve)

**Interactive Workflow:**
1. Run Separation → Vocals extracted
2. Edit curves in spectrum editor (4 modes, 3 tools)
3. Click "Apply Changes" → Preview curve effects
4. Fine-tune curves iteratively
5. Start Processing → Full voice conversion pipeline
6. Preview 6 tracks with independent playback
7. Export final result

### Phase 3: Future Enhancements (Planned)
- API layer for cloud deployment
- Batch processing
- Multiple voice reference blending
- Plugin system for other stem separators/voice converters

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation Strategy |
|------|------------|--------|---------------------|
| Model download failure (slow internet) | Medium | High | Retry logic, offline installer option |
| GPU not available on user machine | High | Medium | Clear CPU fallback, show warning |
| Audio quality issues in output | Medium | Medium | Add normalization, quality warning |
| Very long audio crashes app | Medium | High | Add timeout, chunked processing |
| FFmpeg bundled size too large | Low | Medium | Use minimal build, offer download option |
| PyInstaller EXE too large | Medium | Low | Exclude unnecessary dependencies, Nuitka for optimization |

---

## Dependencies & Blockers

**Dependencies:**
- **Demucs**: https://github.com/facebookresearch/demucs
- **ChatterBox VC**: https://github.com/resemble-ai/chatterbox (Primary - Audio Reference)
- **Applio RVC**: https://github.com/IAHispano/Applio (Primary - Model Reference)
- **OpenVoice**: https://github.com/myshell-ai/OpenVoice (Legacy/Fallback)
- **pydub**: Audio format conversion
- **tkinter**: Desktop UI framework (native Python)
- **FFmpeg**: Audio processing (bundled)
- **Audio Enhancement**: noisereduce, pedalboard, pyloudnorm

**Known Blockers:**
- None identified at requirements stage

---

## Appendix

### Glossary
- **Stem Separation**: Splitting audio into individual instrument tracks
- **Voice Conversion**: Transforming voice characteristics to match another voice
- **DDD**: Domain-Driven Design - software architecture approach
- **Portable EXE**: Single executable that runs without installation
- **vra**: Voice Revolver AI project file format

### References
- Demucs Windows Installation: https://github.com/facebookresearch/demucs/blob/main/docs/windows.md
- ChatterBox GitHub: https://github.com/resemble-ai/chatterbox
- ChatterBox VC Example: https://github.com/resemble-ai/chatterbox/blob/master/example_vc.py
- Applio GitHub: https://github.com/IAHispano/Applio
- Applio Documentation: https://docs.applio.org/
- OpenVoice Usage: https://github.com/myshell-ai/OpenVoice/blob/main/docs/USAGE.md (Legacy)
- tkinter Documentation: https://docs.python.org/3/library/tkinter.html
- Parselmouth Pitch Manipulation: https://parselmouth.readthedocs.io/en/stable/examples/pitch_manipulation.html
- RVC Project (Original): https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI

---

*This PRD was created through interactive requirements gathering with quality scoring to ensure comprehensive coverage of business, functional, UX, and technical dimensions.*
