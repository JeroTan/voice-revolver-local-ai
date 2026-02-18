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
