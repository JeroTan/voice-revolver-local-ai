"""
Installed launcher for Voice Revolver AI.

This is the target `voice-revolver.exe` entry point. It keeps a visible console
and runs the same app path as run_dev.bat: Python environment + run.py.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.portable_installer.path_config import (
    CONFIG_ENV,
    PortablePaths,
    default_app_data_root,
    read_portable_config,
    write_portable_config,
)


def _exe_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _python_for(paths, install_root: Path) -> Path:
    candidates = [
        paths.venv_root / "venv" / "Scripts" / "python.exe",
        install_root / "venv" / "Scripts" / "python.exe",
        PROJECT_ROOT / "venv" / "Scripts" / "python.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not find Voice Revolver Python environment. Checked:\n"
        + "\n".join(str(p) for p in candidates)
    )


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    validate_only = "--validate-only" in argv

    exe_dir = _exe_dir()
    config_path = Path(os.environ.get(CONFIG_ENV, exe_dir / "config" / "portable.json"))
    os.environ[CONFIG_ENV] = str(config_path)

    if config_path.exists():
        paths = read_portable_config(config_path)
    else:
        app_data = default_app_data_root()
        paths = PortablePaths(
            install_root=exe_dir,
            app_data_root=app_data,
            temp_root=app_data / "temp",
            logs_root=app_data / "logs",
            model_root=app_data / "models",
            venv_root=exe_dir / "venvs",
            config_path=config_path,
        )
        write_portable_config(paths)
    paths.ensure_dirs()
    install_root = paths.install_root if paths.install_root.exists() else exe_dir
    run_py = install_root / "run.py"
    if not run_py.exists():
        run_py = PROJECT_ROOT / "run.py"
    if not run_py.exists():
        raise FileNotFoundError(f"run.py not found: {run_py}")

    python_exe = _python_for(paths, install_root)
    env = os.environ.copy()

    print("Voice Revolver AI")
    print(f"Python: {python_exe}")
    print(f"App: {run_py}")
    print(f"Models: {paths.model_root}")
    print(f"Temp: {paths.temp_root}")
    print("")

    if validate_only:
        print("Validation OK")
        return 0

    return subprocess.call([str(python_exe), str(run_py)], cwd=str(install_root), env=env)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"[ERROR] Launcher failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
