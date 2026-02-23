# Product Requirements Document: Voice Revolver AI

**Version**: 1.4 (Track Merger Workspace)  
**Date**: 2026-02-23  
**Author**: Sarah (Product Owner)  
**Quality Score**: 100/100

**Version History:**
- **v1.4** (2026-02-23): Added Track Merger workspace for combining multiple audio tracks
- **v1.3** (2026-02-23): Added Voice Enhancement workspace with Resemble Enhance AI, blend mode
- **v1.2** (2026-02-23): Added Voice Cloning workspace with dual reference modes, RVC parameter controls, curve editing
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

## Product Architecture: Workspace-Based Design

Voice Revolver AI features a **modular workspace system** with four distinct workspaces, each focused on specific audio processing tasks:

### Workspace Overview

| Workspace | Purpose | Key Features | Status |
|-----------|---------|--------------|--------|
| **Vocal Changer** | End-to-end voice replacement in songs | Dual reference modes (Audio/RVC), stem mixing, curve editing | ✅ Complete |
| **Audio Separation** | Standalone stem isolation and editing | 4-track editing (vocals, drums, bass, other), per-track curves | ✅ Complete |
| **Text-to-Speech** | Generate speech from text | 23 languages (MTL), Turbo mode (English), curve editing | ✅ Complete |
| **Voice Cloning** | Voice conversion with audio/model | ChatterBox VC + RVC, 6 RVC parameters, export controls | ✅ Complete |
| **Voice Enhancement** | Enhance audio quality with AI | Resemble Enhance, blend mode A/B comparison | ✅ Complete |
| **Track Merger** | Merge multiple audio tracks | Per-track volume/waveform/playback, curve editing, format export | ✅ Complete |

### Workspace 1: Vocal Changer (Original)

**Purpose**: Complete voice replacement pipeline for songs/videos

**User Flow**:
1. Load original audio/video file
2. Select reference (audio sample or RVC model)
3. Configure settings (gender detection, enhancement options)
4. Process → Demucs separation → Voice conversion → Audio enhancement
5. Edit curves (pitch, reverb, volume, blend, noise reduction)
6. Export final mix

**Key Features**:
- Dual reference modes (Audio/RVC)
- Gender-aware pitch adaptation (F0-based detection)
- Resemble Enhance integration (vocal clarity)
- 5-curve spectrum editor (pitch, reverb, volume, blend, noise)
- Per-stem volume control
- Video support (audio track replacement)

**UI Layout**: Vertical single panel with integrated controls

---

### Workspace 2: Audio Separation

**Purpose**: Isolate and edit individual audio stems

**User Flow**:
1. Load audio file
2. Select Demucs model (htdemucs_ft)
3. Optional: Enable vocal enhancement
4. Separate → 4 stems extracted
5. Edit each stem independently (pitch, reverb, volume curves)
6. Apply Changes → Preview edits
7. Export individual stems or mixed output

**Key Features**:
- 4 independent track editors (vocals, drums, bass, other)
- Per-track SpectrumEditor (scrollable container)
- Non-compounding curve edits (always process from original stem)
- Individual or batch export
- Preview with per-track volume controls

**UI Layout**: Left panel (controls) + Right panel (scrollable track list)

---

### Workspace 3: Text-to-Speech

**Purpose**: Generate speech from text with AI

**User Flow**:
1. Enter text (multiline support)
2. Select language (23 languages via MTL model)
3. Optional: Enable Turbo mode (English only) + Quality Boost
4. Generate speech
5. Edit curves (pitch, reverb, volume)
6. Apply Changes → Preview edits
7. Export as WAV/MP3/FLAC

**Key Features**:
- **Dual TTS Models**:
  - **MTL Model**: 23 languages (multilingual support)
  - **Turbo Model**: English only, special tokens ([laugh], [sigh]), better prosody
- **Turbo Quality Boost**: Enhanced emotion and pause placement
- **HuggingFace Token**: Stored in `~/.voice_revolver/config.json` (required for Turbo)
- **Curve Editing**: Post-processing with pitch/reverb/volume curves
- **Export Checkbox**: "Use edited version" (exports curve-edited audio vs. original TTS)

**Special Tokens** (Turbo mode):
- `[laugh]` - Generates laughter
- `[sigh]` - Generates sighing

**UI Layout**: Left panel (text input + controls) + Right panel (spectrum editor)

---

### Workspace 4: Voice Cloning **(NEW in v1.2)**

**Purpose**: Standalone voice cloning with dual reference modes

**User Flow**:
1. Load original audio (voice to be converted)
2. Select reference mode:
   - **Audio File**: ChatterBox VC (zero-shot, 5-30s sample)
   - **RVC Model**: RVC wrapper (trained .zip model)
3. If RVC: Configure 6 parameters (F0 method, pitch shift, index rate, protection, filter radius, RMS mix)
4. Process → Voice conversion
5. Edit curves (pitch, reverb, volume)
6. Apply Changes → Preview edits
7. Export as WAV/MP3/FLAC/OGG (checkbox: "Use edited version")

**Key Features**:
- **Dual Reference Modes**:
  - **Audio File Mode**: ChatterBox VC (fast, zero-shot)
  - **RVC Model Mode**: RVC wrapper (high-quality, trained models)
- **Dynamic File Type Filtering**: File selector adapts based on reference mode
  - Audio mode: `.wav`, `.mp3`, `.flac`
  - RVC mode: `.zip` files (RVC model archives)
- **RVC Parameter Controls** (6 sliders with descriptions):
  1. **F0 Method**: Pitch extraction algorithm (rmvpe/harvest/crepe/pm)
  2. **Pitch Shift**: Semitone adjustment (-12 to +12)
  3. **Index Rate**: Feature retrieval strength (0.0-1.0, default: 0.75)
  4. **Protection**: Consonant protection (0.0-0.5, default: 0.33)
  5. **Filter Radius**: Pitch smoothing (0-7, default: 3)
  6. **RMS Mix Rate**: Volume envelope mix (0.0-1.0, default: 0.25)
- **Non-Compounding Curve Edits**: All edits start from original processed file
- **File Lock Prevention**: Releases audio handles before processing, cleans old temp files
- **Export Checkbox**: "Use edited version" (exports curve-edited vs. original clone)
- **Progress Callback Compatibility**: Handles both ChatterBox VC (single-arg) and RVC (dual-arg) callbacks

**RVC Parameter Help Text**: Each parameter includes descriptive text explaining purpose and recommended values

**Temp File Workflow**:
```
C:\Users\{user}\AppData\Local\VoiceRevolverAI\temp\voice_cloning\
├── processed.wav          # Original voice clone output (IMMUTABLE)
├── processed_edited.wav   # Latest curve-edited version (OVERWRITES)
├── temp_pitch.wav        # Intermediate: pitch applied
├── temp_volume.wav       # Intermediate: volume applied
└── temp_reverb.wav       # Intermediate: reverb applied
```

**Technical Highlights**:
- Uses `AudioProcessor` (not `VoiceTransformer`) for curve application
- Direct attribute access for curves: `spectrum_editor.pitch_curve`
- Method calls: `load_vocals()`, `reload_audio_only()`, `release_audio_file()`
- Temp file cleanup before processing to prevent Windows file locks

**UI Layout**: Left panel (original audio, reference selector, RVC params, export) + Right panel (spectrum editor wrapper)

**Critical Fixes Applied**:
- ✅ Emoji encoding errors (Windows console) - Replaced with ASCII
- ✅ Progress callback signature mismatch - Flexible callback with default message
- ✅ Method name errors - Corrected to `load_vocals()` with proper parameters
- ✅ Curve getter errors - Direct attribute access instead of getter methods
- ✅ File locking issues - Temp file cleanup before processing
- ✅ Reference mode filtering - Dynamic file type updates via `set_file_types()`
- ✅ VoiceTransformer missing method - Replaced with AudioProcessor

### Workspace 5: Voice Enhancement **(NEW in v1.3)**

**Purpose**: Enhance audio quality using Resemble Enhance AI

**User Flow**:
1. Load original audio file
2. Configure enhancement parameters (NFE, temperature, solver, denoise first)
3. Process → Resemble Enhance AI
4. Use blend mode: A/B comparison (original ↔ enhanced)
5. Edit curves (blend, pitch, volume, reverb)
6. Apply Changes → Preview edits
7. Export as WAV/MP3/FLAC/OGG

**Key Features**:
- **4 Enhancement Parameters**:
  - Quality (NFE): 1-128 (1=fast, 128=best quality)
  - Temperature: 0.01-1.0 (0.01=conservative, 1.0=aggressive)
  - Solver: euler/midpoint/rk4
  - Denoise First: Pre-process with noise reduction
- **Blend Mode**: Real-time A/B comparison between original and enhanced
- **Curve Order**: Blend → Pitch → Volume → Reverb
- **Sample Rate Preservation**: Enhanced audio matches original sample rate

### Workspace 6: Track Merger **(NEW in v1.4)**

**Purpose**: Merge multiple audio tracks into a single combined audio file

**User Flow**:
1. Add Track → Select audio files (unlimited, up to 999)
2. Per-track: Rename, adjust volume, preview playback
3. Merge Tracks → Combine with pydub overlay
4. Edit curves (pitch, volume, reverb) on merged output
5. Apply Changes → Preview edits
6. Export as WAV/MP3/FLAC/OGG

**Key Features**:
- **Unlimited Track Adding**: Add up to 999 tracks (internal limit)
- **Per-Track Controls**:
  - Editable track name (for organization)
  - Waveform visualization (65px canvas)
  - Volume slider (0-200%, default 100%)
  - Playback with seek slider and time display
  - Remove button (close track)
- **Merge Logic**:
  - pydub AudioSegment overlay
  - Per-track volume applied as dB change
  - Auto-normalize if merged audio clips
- **Curve Editing**: Pitch, volume, reverb on merged output
- **Export**: WAV, MP3, FLAC, OGG with "Use edited version" checkbox

**Track Item UI Layout**:
```
┌────────────────────────────────────────────────┐
│ [Editable Track Name]              [✕ Close] │  Row 0
├────────────────────────────────────────────────┤
│ [███ Waveform Canvas ███] [Vol] [100%] │  Row 1
├────────────────────────────────────────────────┤
│ [▶] [=== Seek Slider ===] [0:00/3:45]  │  Row 2
└────────────────────────────────────────────────┘
```

**Temp File Workflow**:
```
C:\Users\{user}\AppData\Local\VoiceRevolverAI\temp\track_merger\
├── merged.wav              # Merged audio (IMMUTABLE after merge)
├── merged_edited.wav       # Latest curve-edited version
├── temp_pitch.wav         # Intermediate: pitch applied
├── temp_volume.wav        # Intermediate: volume applied
└── temp_reverb.wav        # Intermediate: reverb applied
```

**UI Layout**: 50/50 split - Track list (left) | Spectrum editor (right)

**Critical Technical Details**:
- Uses pydub `AudioSegment.overlay()` for track merging
- Volume applied as dB: `20 * log10(volume_multiplier)`
- Auto-normalize if `merged.max_dBFS > -1.0`
- Waveform generated async with librosa (8kHz, 60s max)
- Playback via pygame.mixer.music
- Tools panel pack order fix: pack tools FIRST, then canvas

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

**Phase 2.7: Resemble Enhance Integration** (Completed)
- ✅ Vocal clarity enhancement (Resemble Enhance)
- ✅ Optional phase after voice conversion
- ✅ Separate venv-enhance environment (dependency isolation)
- ✅ GPU acceleration support
- ✅ Configurable enhancement strength

**Phase 2.8: Voice Cloning Workspace** (Completed - 2026-02-23)
- ✅ **Standalone Voice Cloning Workspace**: Dedicated UI workspace for voice conversion tasks
- ✅ **Dual Reference Mode UI**:
  - Radio buttons: "Audio File" / "RVC Model"
  - Dynamic file type filtering (audio files vs. .zip models)
  - RVC parameters panel (shows/hides based on mode)
- ✅ **RVC Parameter Controls**: 6 sliders with help text descriptions
  - F0 Method dropdown (rmvpe, harvest, crepe, pm)
  - Pitch Shift slider (-12 to +12 semitones)
  - Index Rate slider (0.0-1.0, default: 0.75)
  - Protection slider (0.0-0.5, default: 0.33)
  - Filter Radius slider (0-7, default: 3)
  - RMS Mix Rate slider (0.0-1.0, default: 0.25)
  - "Reset All to Defaults" button
- ✅ **Spectrum Editor Integration**: Output panel wraps SpectrumEditor component
- ✅ **Non-Compounding Curve Editing**: Always process from original `processed.wav`
- ✅ **File Lock Prevention**: Release audio + clean temp files before processing
- ✅ **Export Controls**:
  - Checkbox: "Use edited version" (exports curve-edited vs. original)
  - Format selector: WAV, MP3, FLAC, OGG
  - Browse button for output directory
- ✅ **Progress Tracking**: Compatible with both ChatterBox VC and RVC callbacks
- ✅ **Dynamic FileSelector**: `set_file_types()` method for runtime filter updates
- ✅ **Error Handling**: Windows encoding fixes (Unicode → ASCII logging)
- ✅ **AudioProcessor Integration**: Apply curves individually (pitch → volume → reverb)
- ✅ **Menu Integration**: "Voice Cloning" menu item enabled in menu bar
- ✅ **Workspace Switching**: Integrated into main window's workspace manager

**Voice Cloning Workspace Components**:
```
voice_revolver_ui/features/voice_cloning/
├── __init__.py                    # Package exports (VoiceCloningWorkspace)
├── workspace.py                   # Main workspace frame (487 lines)
└── components/
    ├── __init__.py               # Component exports
    ├── input_panel.py            # Left panel controls (503 lines)
    └── output_panel.py           # Right panel spectrum editor (114 lines)
```

**Key Technical Patterns**:
- **Temp File Workflow**: `processed.wav` (immutable) → `processed_edited.wav` (overwrites)
- **Curve Application**: Sequential processing (pitch → volume → reverb)
- **File Selector**: Dynamic filtering via `on_reference_mode_changed()`
- **Spectrum Editor**: Direct attribute access (`pitch_curve`, `reverb_curve`, `volume_curve`)
- **Method Calls**: `load_vocals()`, `reload_audio_only()`, `release_audio_file()`

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
