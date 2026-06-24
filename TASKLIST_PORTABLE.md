# Portable App Checklist

## Source Of Truth

- [x] Treat `run_dev.bat` as true stable runner.
- [x] Preserve `run_dev.bat` behavior until installed app proves equal.
- [ ] Build portable/installer flow as wrapper/bootstrap around stable launch path, not replacement first.
- [ ] After every portability change, retest `run_dev.bat`.

## Current Situation

- [x] `run_dev.bat` activates repo-local `venv`.
- [x] `run_dev.bat` prints Python version with `.\venv\Scripts\python.exe --version`.
- [x] `run_dev.bat` launches app with `.\venv\Scripts\python.exe run.py`.
- [x] `run.py` sets Windows console UTF-8 handling.
- [x] `run.py` adds repo root to `sys.path`.
- [x] `run.py` calls `voice_revolver_ui.main_tk.main()`.
- [x] `main_tk.main()` requires Python 3.11.
- [x] `main_tk.main()` preloads PyTorch.
- [x] `main_tk.main()` configures FFmpeg.
- [x] `main_tk.main()` opens startup device dialog.
- [x] `main_tk.main()` opens loading dialog.
- [x] `main_tk.main()` starts Tkinter main UI.
- [x] Current Windows app data root is `%LOCALAPPDATA%/VoiceRevolverAI`.
- [x] Current temp root is `%LOCALAPPDATA%/VoiceRevolverAI/temp`.
- [x] Current log path is `%LOCALAPPDATA%/VoiceRevolverAI/logs/app.log`.
- [x] Current OpenVoice cache is `%LOCALAPPDATA%/VoiceRevolverAI/models/checkpoints_v2`.
- [x] Current RVC bundled weights are repo `rvc/models/...`.
- [x] Current MDX cache is `%USERPROFILE%/.audio-separator/models`.
- [x] Demucs cache uses package default unless redirected.
- [x] ChatterBox cache uses HuggingFace/default cache unless redirected.
- [x] Resemble Enhance cache uses package default unless redirected.
- [x] Current dependency reality is four Python environments: `venv`, `venv-rvc`, `venv-mdx`, `venv-enhance`.
- [x] `requirements.txt` is not enough for reproducible installer.
- [x] Existing packaging files are partial: `build_portable.py`, `voice_revolver.spec`, `runtime_hook.py`, `build_installer.py`, `installer.iss`.
- [ ] Replace partial packaging assumptions with tested installer/bootstrap flow.

## Hard Rules

- [ ] Do not regress stable `run_dev.bat` flow.
- [ ] Do not move stable runtime behavior until installer path abstraction is proven.
- [ ] Use exact dependency versions from working local envs.
- [ ] Use real progress signals only: bytes, subprocess output, stage completion, verification results.
- [ ] Keep installed app console visible beside UI.
- [ ] Ask user for install location.
- [ ] Default install location to `%ProgramFiles%/Voice Revolver AI`.
- [ ] Ask user for model/weights location.
- [ ] Ask user whether to create shortcut.
- [ ] Use admin/UAC only when required by selected install path.
- [ ] Test complete installer flow before marking done.

## Phase 0 - Baseline Audit

- [ ] Record git status before edits.
- [ ] Freeze `venv` into `requirements-main.lock.txt`.
- [ ] Freeze `venv-rvc` into `requirements-rvc.lock.txt`.
- [ ] Freeze `venv-mdx` into `requirements-mdx.lock.txt`.
- [ ] Freeze `venv-enhance` into `requirements-enhance.lock.txt`.
- [ ] Record Python version for every env.
- [x] Current observed env Python version: Python 3.11.9.
- [x] Current main env uses CUDA PyTorch `2.1.2+cu118`.
- [x] Current `venv-rvc` has mixed CUDA/CPU torch packages.
- [x] Current `venv-mdx` uses CUDA PyTorch `2.1.2+cu118`.
- [x] Current `venv-enhance` uses CUDA PyTorch `2.1.1+cu118`.
- [ ] Record package indexes needed for each lock file.
- [ ] Record installed model files and sizes under `rvc/models`.
- [ ] Record OpenVoice S3 zip source.
- [ ] Record HuggingFace ChatterBox MTL/Turbo sources.
- [ ] Record Demucs model source/cache behavior.
- [ ] Record MDX audio-separator model source/cache behavior.
- [ ] Record Resemble Enhance source/cache behavior.
- [ ] Record static-ffmpeg binary source/cache behavior.
- [ ] Create tiny audio fixtures for installer smoke tests if none exist.

## Phase 1 - Portable Path Design

- [ ] Add one config source for install root.
- [ ] Add one config source for app data root.
- [ ] Add one config source for temp root.
- [ ] Add one config source for logs root.
- [ ] Add one config source for model root.
- [ ] Add one config source for venv root.
- [ ] Support `VOICE_REVOLVER_APP_DATA`.
- [ ] Support `VOICE_REVOLVER_TEMP_DIR`.
- [ ] Support `VOICE_REVOLVER_MODEL_DIR`.
- [ ] Support `VOICE_REVOLVER_VENV_DIR`.
- [ ] Redirect `HF_HOME` before AI imports.
- [ ] Redirect `HF_HUB_CACHE` before AI imports.
- [ ] Redirect `TRANSFORMERS_CACHE` before AI imports.
- [ ] Redirect `TORCH_HOME` before AI imports.
- [ ] Redirect `XDG_CACHE_HOME` before AI imports.
- [ ] Redirect audio-separator `model_file_dir`.
- [ ] Redirect static-ffmpeg cache/path if package supports it.
- [ ] Keep default app data root as `%LOCALAPPDATA%/VoiceRevolverAI`.
- [ ] Keep default temp root as `%LOCALAPPDATA%/VoiceRevolverAI/temp`.
- [ ] Default model root to `%LOCALAPPDATA%/VoiceRevolverAI/models` unless user chooses another path.
- [ ] Make model root movable after install through config file.

## Phase 2 - Installer UX

- [ ] Build installer `.exe`.
- [ ] Installer asks install location.
- [ ] Installer asks model/weights location.
- [ ] Installer asks create desktop shortcut.
- [ ] Installer offers run app after install.
- [ ] Installer elevates through UAC when selected path requires admin.
- [ ] Installer progress shows current stage.
- [ ] Installer progress shows current command/log line.
- [ ] Installer progress shows current item progress.
- [ ] Installer progress shows total progress.
- [ ] Installer shows error details and log path when stage fails.
- [ ] Final success dialog says install succeeded.
- [ ] Final success dialog has `Run the app` button.
- [ ] Final success dialog has `Close` button.

## Phase 3 - Bootstrap Engine

- [ ] Detect Scoop.
- [ ] Install Scoop if missing and user approves.
- [ ] Install Python 3.11.x through Scoop.
- [ ] Create main env under chosen venv root.
- [ ] Create RVC env under chosen venv root.
- [ ] Create MDX env under chosen venv root.
- [ ] Create Enhance env under chosen venv root.
- [ ] Install main lock file with exact versions.
- [ ] Install RVC lock file with exact versions.
- [ ] Install MDX lock file with exact versions.
- [ ] Install Enhance lock file with exact versions.
- [ ] Select CUDA or CPU torch packages based on detection/user choice.
- [ ] Validate imports after main env install.
- [ ] Validate imports after RVC env install.
- [ ] Validate imports after MDX env install.
- [ ] Validate imports after Enhance env install.
- [ ] Download models into chosen model root.
- [ ] Write final app config file.
- [ ] Skip existing valid Python.
- [ ] Skip valid venv when lock hash matches.
- [ ] Skip existing model when manifest verification passes.
- [ ] Resume downloads when supported.
- [ ] Capture stdout/stderr from every subprocess into installer log.
- [ ] Fail with actionable message and log path.

## Phase 4 - App Launcher

- [ ] Create installed app launcher `.exe`.
- [ ] Launcher opens visible console.
- [ ] Launcher sets config/env vars before importing app code.
- [ ] Launcher starts `run.py` equivalent.
- [ ] Launcher preserves current UI flow: startup dialog, loading dialog, main UI.
- [ ] Launcher works without repo cwd.
- [ ] Launcher resolves relative paths from installed app/configured roots.
- [ ] Subprocess wrappers find isolated envs through `VOICE_REVOLVER_VENV_DIR`.

## Phase 5 - Model Download Refactor

- [ ] Update OpenVoice download to chosen model root.
- [ ] Redirect ChatterBox VC HuggingFace downloads to chosen model root.
- [ ] Redirect ChatterBox TTS HuggingFace downloads to chosen model root.
- [ ] Redirect Demucs weights to chosen model root.
- [ ] Redirect MDX audio-separator model directory to chosen model root.
- [ ] Keep RVC pretrained/embedders/predictors available from chosen model root or installed resource path.
- [ ] Add model manifest with required files.
- [ ] Add model manifest sizes.
- [ ] Add model manifest checksums where practical.
- [ ] Installer verifies required model files before success.
- [ ] App startup verifies model root.
- [ ] App startup shows clear repair action if model root missing.

## Phase 6 - Progress Implementation

- [ ] Add weighted installer stage: prerequisites.
- [ ] Add weighted installer stage: Python install.
- [ ] Add weighted installer stage: main env install.
- [ ] Add weighted installer stage: RVC env install.
- [ ] Add weighted installer stage: MDX env install.
- [ ] Add weighted installer stage: Enhance env install.
- [ ] Add weighted installer stage: model downloads.
- [ ] Add weighted installer stage: shortcut/config/write verification.
- [ ] Parse pip subprocess output for current package line.
- [ ] Report byte progress for downloads when content length exists.
- [ ] Predownload hidden-progress model libraries with known APIs where possible.
- [ ] Show subprocess logs for libraries that hide progress.
- [ ] Write progress events to JSONL installer log.

## Phase 7 - Build System

- [ ] Choose final distribution strategy.
- [ ] First pass uses online installer because requested flow installs Python/dependencies during setup.
- [ ] Keep existing PyInstaller attempt as fallback/reference.
- [ ] Add build command: `python tools/build_installer.py`.
- [ ] Output setup exe to `dist/VoiceRevolverAI-Setup-x.y.z.exe`.
- [ ] Document installer log schema.
- [ ] Generate versioned manifest.

## Phase 8 - Test Matrix

- [ ] Run `run_dev.bat` after changes.
- [ ] Confirm startup dialog opens.
- [ ] Confirm loading dialog completes.
- [ ] Confirm main UI opens.
- [ ] Test installer dry run with custom install path.
- [ ] Test installer dry run with custom model path.
- [ ] Test installer dry run with shortcut unchecked.
- [ ] Test installer dry run with shortcut checked.
- [ ] Test installed app from Start Menu.
- [ ] Test installed app from desktop shortcut.
- [ ] Test installed app by double-clicking exe.
- [ ] Confirm visible console appears beside UI.
- [ ] Confirm logs write to configured log path.
- [ ] Confirm models download to chosen model directory only.
- [ ] Confirm app finds models after restart.
- [ ] Confirm app fails cleanly if model folder moved.
- [ ] Smoke test Vocal Changer opens and loads small audio.
- [ ] Smoke test Audio Separation runs Demucs on tiny audio.
- [ ] Smoke test Audio Separation MDX checks env/model.
- [ ] Smoke test Text to Speech loads model or shows token-required flow.
- [ ] Smoke test Voice Cloning audio-file mode runs ChatterBox path check.
- [ ] Smoke test Voice Cloning RVC model zip validation.
- [ ] Smoke test Voice Enhancement detects `venv-enhance`.
- [ ] Smoke test Track Merger merges two tiny files.
- [ ] Smoke test Audio Training validates sample and starts/cancels without orphan process.
- [ ] Test no repo cwd.
- [ ] Test no preactivated venv.
- [ ] Test no Python in PATH except installer-managed Python.
- [ ] Test custom model directory with spaces.
- [ ] Test non-admin install path.
- [ ] Test Program Files install path with UAC.

## Phase 9 - Regression Guards

- [ ] Add smoke scripts that avoid long AI runs.
- [ ] Add import validation for all four envs.
- [ ] Add path validation tests for frozen/installed mode.
- [ ] Add no-hardcoded-`F:\dev` scan.
- [ ] Add no-default-cache scan for new code.
- [ ] Run full installer from start to finish before marking complete.
- [ ] Keep install logs and test notes as documented artifact.

## Open Decisions

- [ ] Online installer vs huge offline installer.
- [ ] CUDA-only install vs CPU/GPU choice during setup.
- [ ] Scoop mandatory vs one possible Python acquisition method.
- [ ] Model root per-user `%LOCALAPPDATA%` vs shared `%ProgramData%`.
- [ ] Uninstall removes user models or leaves them.
