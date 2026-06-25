"""
Build portable launcher and setup executable.

Outputs:
- dist/voice-revolver.exe
- dist/VoiceRevolverAI-Setup.exe
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
STAGE_ROOT = PROJECT_ROOT / "build" / "portable_installer_stage"
APP_SOURCE = STAGE_ROOT / "app_source"
DIST = PROJECT_ROOT / "dist"

RUNTIME_DIRS = [
    "assets",
    "rvc",
    "voice_revolver_core",
    "voice_revolver_ui",
]
RUNTIME_FILES = [
    "run.py",
    "requirements-main.lock.txt",
    "requirements-rvc.lock.txt",
    "requirements-mdx.lock.txt",
    "requirements-enhance.lock.txt",
]
PORTABLE_TOOL_FILES = [
    "bootstrap.py",
    "compat_patches.py",
    "installer_gui.py",
    "launcher.py",
    "path_config.py",
]


def _ignore(dir_path: str, names: list[str]) -> set[str]:
    ignored = {
        ".git",
        ".env",
        ".venv",
        ".venv-1",
        ".venv-2",
        "venv",
        "venv-rvc",
        "venv-mdx",
        "venv-enhance",
        "build",
        "dist",
        "logs",
        "processed",
        "__pycache__",
    }
    return {name for name in names if name in ignored or name.endswith(".pyc")}


def stage_source() -> None:
    if STAGE_ROOT.exists():
        shutil.rmtree(STAGE_ROOT)
    STAGE_ROOT.mkdir(parents=True, exist_ok=True)
    APP_SOURCE.mkdir(parents=True, exist_ok=True)

    for dirname in RUNTIME_DIRS:
        shutil.copytree(PROJECT_ROOT / dirname, APP_SOURCE / dirname, ignore=_ignore)

    tools_dir = APP_SOURCE / "tools" / "portable_installer"
    tools_dir.mkdir(parents=True, exist_ok=True)
    for filename in PORTABLE_TOOL_FILES:
        shutil.copy2(
            PROJECT_ROOT / "tools" / "portable_installer" / filename,
            tools_dir / filename,
        )

    for filename in RUNTIME_FILES:
        shutil.copy2(PROJECT_ROOT / filename, APP_SOURCE / filename)

    launcher = DIST / "voice-revolver.exe"
    if launcher.exists():
        payload_dist = APP_SOURCE / "dist"
        payload_dist.mkdir(parents=True, exist_ok=True)
        shutil.copy2(launcher, payload_dist / "voice-revolver.exe")


def run_pyinstaller(args: list[str]) -> None:
    command = [sys.executable, "-m", "PyInstaller", *args]
    print(" ".join(command), flush=True)
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def build_launcher() -> None:
    run_pyinstaller([
        "--clean",
        "--onefile",
        "--console",
        "--name",
        "voice-revolver",
        "--distpath",
        str(DIST),
        "--workpath",
        str(PROJECT_ROOT / "build" / "pyinstaller_launcher"),
        "--specpath",
        str(PROJECT_ROOT / "build" / "specs"),
        "--paths",
        str(PROJECT_ROOT),
        str(PROJECT_ROOT / "tools" / "portable_installer" / "launcher.py"),
    ])


def build_setup() -> None:
    data_arg = f"{APP_SOURCE};app_source"
    run_pyinstaller([
        "--clean",
        "--onefile",
        "--windowed",
        "--name",
        "VoiceRevolverAI-Setup",
        "--distpath",
        str(DIST),
        "--workpath",
        str(PROJECT_ROOT / "build" / "pyinstaller_setup"),
        "--specpath",
        str(PROJECT_ROOT / "build" / "specs"),
        "--paths",
        str(PROJECT_ROOT),
        "--add-data",
        data_arg,
        str(PROJECT_ROOT / "tools" / "portable_installer" / "installer_gui.py"),
    ])
    setup = DIST / "VoiceRevolverAI-Setup.exe"
    if setup.exists():
        shutil.copy2(setup, DIST / "VoiceRevolverAI-Setup-v1.0.0.exe")


def main() -> int:
    stage_source()
    build_launcher()
    build_setup()
    print("")
    print(f"Built launcher: {DIST / 'voice-revolver.exe'}")
    print(f"Built setup:    {DIST / 'VoiceRevolverAI-Setup.exe'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
