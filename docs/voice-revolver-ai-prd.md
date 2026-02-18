# Product Requirements Document: Voice Revolver AI

**Version**: 1.0
**Date**: 2026-02-18
**Author**: Sarah (Product Owner)
**Quality Score**: 100/100

---

## Executive Summary

Voice Revolver AI is a local-first desktop application that enables users to replace vocals in any song with a reference voice sample. The system uses AI-powered stem separation (Demucs) to isolate vocals and instrumental tracks, then applies voice conversion (OpenVoice) to transform the original vocals to match the reference voice identity. The application is designed as a portable executable for Windows and Mac, with all processing done locally on the user's machine—no cloud dependency required.

The core business logic is built using Domain-Driven Design (DDD) architecture, allowing the domain layer to be reused across different interface types (CLI, API, Desktop UI) in future iterations.

---

## Problem Statement

**Current Situation**: Users who want to create karaoke versions or replace vocals in songs must rely on cloud-based services or expensive studio software. Existing solutions often require internet connection, have file size limits, or charge per conversion.

**Proposed Solution**: A portable desktop application that runs locally, using state-of-the-art AI models (Demucs for stem separation, OpenVoice for voice conversion) to provide unlimited vocal replacement without internet dependency after initial model download.

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
- **Description**: Uses OpenVoice to convert original vocals to match reference voice
- **Input**: Original vocal track, reference voice audio
- **Output**: Converted vocal track
- **Models**: OpenVoice V2 (better quality, multi-language support)
- **Edge Cases**:
  - Reference audio too short (<3 seconds): Show warning, proceed with available data
  - Reference audio noisy: Attempt to clean, warn user if quality poor
  - Language mismatch: OpenVoice handles cross-lingual, but may warn
- **Error Handling**: Error codes VOICE_CONVERT_FAILED, REFERENCE_TOO_SHORT

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
- **Description**: Applies pitch adjustment and emotion control via OpenVoice
- **Parameters**:
  - Pitch: -12 to +12 semitones
  - Emotion/Style: Controlled via OpenVoice style parameters
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
- **OpenVoice V2**: Voice conversion with style/emotion control
- **pydub**: Format conversion
- **FFmpeg**: Audio processing backend (bundled + auto-download)
- **Parselmouth**: Pitch manipulation (optional enhancement)

### Technology Stack
- **Language**: Python 3.10+
- **UI Framework**: PyQt/PySide
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
- Voice conversion via OpenVoice
- Basic audio mixing
- Preview with play/pause/seek
- Export to WAV/MP3
- Model auto-download on startup
- FFmpeg auto-download
- Progress tracking
- Error code system
- File naming (auto date_time_random)
- Basic project save/load (.vra)
- GPU/CPU selection with suggestion
- Terminal window visible
- Temp file cleanup on close

### Phase 2: Enhancements (Post-Launch)
- Format converter (FLAC, OGG, AAC export)
- Voice transformation (pitch, emotion control)
- Custom output naming at export
- User-selectable output folder
- Cancel processing button
- Advanced project management
- Settings persistence

### Future Considerations
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
- **OpenVoice**: https://github.com/myshell-ai/OpenVoice
- **pydub**: Audio format conversion
- **PyQt/PySide**: Desktop UI framework
- **FFmpeg**: Audio processing (bundled)

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
- OpenVoice Usage: https://github.com/myshell-ai/OpenVoice/blob/main/docs/USAGE.md
- PyQt Documentation: https://doc.qt.io/qtforpython/
- Parselmouth Pitch Manipulation: https://parselmouth.readthedocs.io/en/stable/examples/pitch_manipulation.html

---

*This PRD was created through interactive requirements gathering with quality scoring to ensure comprehensive coverage of business, functional, UX, and technical dimensions.*
