# Portable App Checklist

## Source Of Truth

- [x] Treat `run_dev.bat` as true stable runner.
- [x] Preserve `run_dev.bat` behavior until installed app proves equal.
- [x] Build portable/installer flow as wrapper/bootstrap around stable launch path, not replacement first.
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
- [x] Replace partial packaging assumptions with tested installer/bootstrap flow.

## Hard Rules

- [ ] Do not regress stable `run_dev.bat` flow.
- [ ] Do not move stable runtime behavior until installer path abstraction is proven.
- [x] Use exact dependency versions from working local envs.
- [x] Use real progress signals only: bytes, subprocess output, stage completion, verification results.
- [x] Keep installed app console visible beside UI.
- [x] Ask user for install location.
- [x] Default install location to `%ProgramFiles%/Voice Revolver AI`.
- [x] Ask user for model/weights location.
- [x] Ask user whether to create shortcut.
- [ ] Use admin/UAC only when required by selected install path.
- [ ] Test complete installer flow before marking done.

## Phase 0 - Baseline Audit

- [ ] Record git status before edits.
- [x] Freeze `venv` into `requirements-main.lock.txt`.
- [x] Freeze `venv-rvc` into `requirements-rvc.lock.txt`.
- [x] Freeze `venv-mdx` into `requirements-mdx.lock.txt`.
- [x] Freeze `venv-enhance` into `requirements-enhance.lock.txt`.
- [x] Record Python version for every env.
- [x] Current observed env Python version: Python 3.11.9.
- [x] Current main env uses CUDA PyTorch `2.1.2+cu118`.
- [x] Current `venv-rvc` has mixed CUDA/CPU torch packages.
- [x] Current `venv-mdx` uses CUDA PyTorch `2.1.2+cu118`.
- [x] Current `venv-enhance` uses CUDA PyTorch `2.1.1+cu118`.
- [x] Record package indexes needed for each lock file.
- [ ] Record installed model files and sizes under `rvc/models`.
- [x] Record OpenVoice S3 zip source and 2026-06-24 404 status.
- [ ] Record HuggingFace ChatterBox MTL/Turbo sources.
- [ ] Record Demucs model source/cache behavior.
- [ ] Record MDX audio-separator model source/cache behavior.
- [ ] Record Resemble Enhance source/cache behavior.
- [ ] Record static-ffmpeg binary source/cache behavior.
- [ ] Create tiny audio fixtures for installer smoke tests if none exist.

## Phase 1 - Portable Path Design

- [x] Add one config source for install root.
- [x] Add one config source for app data root.
- [x] Add one config source for temp root.
- [x] Add one config source for logs root.
- [x] Add one config source for model root.
- [x] Add one config source for venv root.
- [x] Support `VOICE_REVOLVER_APP_DATA`.
- [x] Support `VOICE_REVOLVER_TEMP_DIR`.
- [x] Support `VOICE_REVOLVER_MODEL_DIR`.
- [x] Support `VOICE_REVOLVER_VENV_DIR`.
- [x] Redirect `HF_HOME` before AI imports.
- [x] Redirect `HF_HUB_CACHE` before AI imports.
- [x] Redirect `TRANSFORMERS_CACHE` before AI imports.
- [x] Redirect `TORCH_HOME` before AI imports.
- [x] Redirect `XDG_CACHE_HOME` before AI imports.
- [x] Redirect audio-separator `model_file_dir`.
- [ ] Redirect static-ffmpeg cache/path if package supports it.
- [x] Keep default app data root as `%LOCALAPPDATA%/VoiceRevolverAI`.
- [x] Keep default temp root as `%LOCALAPPDATA%/VoiceRevolverAI/temp`.
- [x] Default model root to `%LOCALAPPDATA%/VoiceRevolverAI/models` unless user chooses another path.
- [x] Make model root movable after install through config file.

## Phase 2 - Installer UX

- [x] Build installer `.exe`.
- [x] Build setup payload from runtime allowlist only.
- [x] Exclude docs, agent memory, tasklist, tests, samples, old files, and dev/build scripts from setup payload.
- [x] Installer asks install location.
- [x] Installer asks model/weights location.
- [x] Installer asks create desktop shortcut.
- [x] Installer offers run app after install.
- [ ] Installer elevates through UAC when selected path requires admin.
- [x] Installer progress shows current stage.
- [x] Installer progress shows current command/log line.
- [x] Installer progress shows current item progress.
- [x] Installer progress shows total progress.
- [x] Installer shows error details and log path when stage fails.
- [x] Final success dialog says install succeeded.
- [x] Final success dialog has `Run the app` button.
- [x] Final success dialog has `Run and close` button.
- [x] Final success dialog has `Close` button.
- [x] During install, `Close` becomes `Cancel`.
- [x] Cancel stops active subprocess tree.
- [x] Cancel cleans current-run install artifacts where safe.

## Phase 3 - Bootstrap Engine

- [x] Detect Scoop.
- [x] Install Scoop if missing and user approves.
- [x] Install Python 3.11.x through Scoop.
- [x] Create main env under chosen venv root.
- [x] Create RVC env under chosen venv root.
- [x] Create MDX env under chosen venv root.
- [x] Create Enhance env under chosen venv root.
- [x] Install main lock file with exact versions.
- [x] Install RVC lock file with exact versions.
- [x] Install MDX lock file with exact versions.
- [x] Install Enhance lock file with exact versions.
- [ ] Select CUDA or CPU torch packages based on detection/user choice.
- [x] Validate imports after main env install.
- [x] Validate `demucs.pretrained` after main env install so Hydra runtime failures are caught.
- [x] Validate `soundfile` import after each env install so broken DLL payloads are caught.
- [x] Validate imports after RVC env install.
- [x] Validate imports after MDX env install.
- [x] Validate imports after Enhance env install.
- [x] Download models into chosen model root.
- [x] Prefetch Demucs `htdemucs_ft` checkpoint files during setup.
- [x] Treat OpenVoice V2 as legacy optional because upstream checkpoint URL is unavailable.
- [x] Write final app config file.
- [x] Skip existing valid Python.
- [x] Skip valid venv when lock hash matches.
- [x] Audit installed package versions against lock before skipping a venv.
- [x] Repair dependency drift by reinstalling the exact lock file.
- [ ] Skip existing model when manifest verification passes.
- [ ] Resume downloads when supported.
- [x] Capture stdout/stderr from every subprocess into installer log.
- [x] Fail with actionable message and log path.
- [x] Fail required model download errors instead of silently completing.
- [x] Repair broken `setuptools`/`PyYAML` runtime files when recreated venv content is incomplete.
- [x] Repair broken `soundfile` wheel/DLL payload by reinstalling locked `soundfile`.
- [x] Validate existing markerless venv before reinstalling.

## Phase 4 - App Launcher

- [x] Create installed app launcher `.exe`.
- [x] Launcher opens visible console.
- [x] Launcher sets config/env vars before importing app code.
- [x] Launcher starts `run.py` equivalent.
- [x] Launcher preserves current UI flow: startup dialog, loading dialog, main UI.
- [x] Launcher works without repo cwd.
- [x] Launcher resolves relative paths from installed app/configured roots.
- [x] Subprocess wrappers find isolated envs through `VOICE_REVOLVER_VENV_DIR`.

## Phase 5 - Model Download Refactor

- [x] Update OpenVoice download to chosen model root.
- [x] Redirect ChatterBox VC HuggingFace downloads to chosen model root.
- [x] Redirect ChatterBox TTS HuggingFace downloads to chosen model root.
- [x] Redirect Demucs weights to chosen model root.
- [x] Redirect MDX audio-separator model directory to chosen model root.
- [x] Keep RVC pretrained/embedders/predictors available from chosen model root or installed resource path.
- [x] Patch RVC predictor/embedder/pretrained path helpers to use selected model root.
- [x] Run RVC subprocess from installed project root with portable model/venv env vars.
- [ ] Add model manifest with required files.
- [ ] Add model manifest sizes.
- [ ] Add model manifest checksums where practical.
- [ ] Installer verifies required model files before success.
- [x] App startup verifies model root.
- [ ] App startup shows clear repair action if model root missing.

## Phase 6 - Progress Implementation

- [x] Add weighted installer stage: prerequisites.
- [x] Add weighted installer stage: Python install.
- [x] Add weighted installer stage: main env install.
- [x] Add weighted installer stage: RVC env install.
- [x] Add weighted installer stage: MDX env install.
- [x] Add weighted installer stage: Enhance env install.
- [x] Add weighted installer stage: model downloads.
- [x] Add weighted installer stage: shortcut/config/write verification.
- [x] Parse pip subprocess output for current package line.
- [ ] Report byte progress for downloads when content length exists.
- [ ] Predownload hidden-progress model libraries with known APIs where possible.
- [x] Show subprocess logs for libraries that hide progress.
- [x] Write progress events to JSONL installer log.

## Phase 7 - Build System

- [ ] Choose final distribution strategy.
- [x] First pass uses online installer because requested flow installs Python/dependencies during setup.
- [ ] Keep existing PyInstaller attempt as fallback/reference.
- [x] Add build command: `python tools/build_installer.py`.
- [x] Output setup exe to `dist/VoiceRevolverAI-Setup-x.y.z.exe`.
- [ ] Document installer log schema.
- [ ] Generate versioned manifest.

## Phase 8 - Test Matrix

- [ ] Run `run_dev.bat` after changes.
- [ ] Confirm startup dialog opens.
- [ ] Confirm loading dialog completes.
- [ ] Confirm main UI opens.
- [x] Add headless/mock installer bootstrap command.
- [x] Headless test accepts fake install path.
- [x] Headless test accepts fake model path.
- [x] Headless test has interactive prompt mode.
- [x] Interactive headless test asks where to install program.
- [x] Interactive headless test shows default install path.
- [x] Interactive headless test lets tester type custom install folder.
- [x] Interactive headless test asks where to store models/weights.
- [x] Interactive headless test shows default model path.
- [x] Interactive headless test lets tester type custom model folder.
- [x] Interactive headless test asks whether to create shortcut.
- [x] Interactive headless test accepts typed yes/no shortcut answer.
- [x] Headless test accepts shortcut disabled.
- [x] Headless test checks or installs Python 3.11.x.
- [x] Headless test creates/checks main env.
- [x] Headless test creates/checks RVC env.
- [x] Headless test creates/checks MDX env.
- [x] Headless test creates/checks Enhance env.
- [x] Headless test installs/checks exact dependency locks.
- [x] Headless test downloads/checks required models.
- [x] Headless test writes config file.
- [x] Headless test validates launcher command without opening installer UI.
- [x] Headless test supports dry-run mode with no filesystem mutation except logs.
- [x] Headless test supports clean temp install root for full bootstrap simulation.
- [x] Headless test emits machine-readable progress events.
- [x] Headless test writes installer bootstrap log.
- [x] Test installer dry run with custom install path.
- [x] Test installer dry run with custom model path.
- [x] Test installer dry run with shortcut unchecked.
- [x] Test installer dry run with shortcut checked.
- [x] Test full headless bootstrap at `D:\sample` with model root `D:\sample2`.
- [x] Re-test full headless bootstrap after OpenVoice optional fix.
- [x] Re-test full headless bootstrap after Hydra/Demucs prefetch fix.
- [x] Re-test full headless bootstrap after `soundfile` DLL repair.
- [x] Simulate missing `libsndfile_x64.dll` and verify setup repairs it.
- [x] Simulate dependency drift and verify setup repairs exact lock versions.
- [x] Validate installed launcher at `D:\sample\voice-revolver.exe --validate-only`.
- [x] Validate rebuilt setup payload with `dist\VoiceRevolverAI-Setup.exe --validate-only`.
- [x] Scan staged setup payload for forbidden docs/dev files.
- [x] Validate required RVC predictor/embedder assets in chosen model root.
- [ ] Test installed app from Start Menu.
- [ ] Test installed app from desktop shortcut.
- [ ] Test installed app by double-clicking exe.
- [x] Confirm visible console appears beside UI.
- [x] Confirm logs write to configured log path.
- [x] Confirm models download to chosen model directory only.
- [ ] Confirm app finds models after restart.
- [ ] Confirm app fails cleanly if model folder moved.
- [ ] Smoke test Vocal Changer opens and loads small audio.
- [x] Smoke test Demucs wrapper `load_model()` in installed main env.
- [x] Smoke test Audio Separation runs Demucs on tiny audio.
- [x] Smoke test RVC `rmvpe.pt` loads from chosen model root.
- [x] Smoke test RVC wrapper conversion creates `converted.wav`.
- [ ] Smoke test Audio Separation MDX checks env/model.
- [ ] Smoke test Text to Speech loads model or shows token-required flow.
- [ ] Smoke test Voice Cloning audio-file mode runs ChatterBox path check.
- [ ] Smoke test Voice Cloning RVC model zip validation.
- [x] Smoke test Voice Enhancement detects `venv-enhance`.
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
