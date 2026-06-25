"""
Headless installer bootstrap for Voice Revolver AI.

Use this before the real installer UI exists, and as the installer engine later.
It can run interactively in a terminal, dry-run without mutation, or perform a
full local bootstrap.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import shutil
import stat
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Optional


def _source_root() -> Path:
    explicit = os.environ.get("VOICE_REVOLVER_SOURCE_ROOT")
    if explicit:
        return Path(explicit)
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "app_source"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _source_root()
sys.path.insert(0, str(PROJECT_ROOT))

from tools.portable_installer.path_config import (
    PortablePaths,
    default_app_data_root,
    default_install_root,
    write_portable_config,
)


LOCKS = {
    "venv": "requirements-main.lock.txt",
    "venv-rvc": "requirements-rvc.lock.txt",
    "venv-mdx": "requirements-mdx.lock.txt",
    "venv-enhance": "requirements-enhance.lock.txt",
}
BOOTSTRAP_PIP_VERSION = "24.0"
BOOTSTRAP_SETUPTOOLS_VERSION = "65.5.0"
BOOTSTRAP_PYYAML_VERSION = "6.0.3"
VALIDATION_IMPORTS = {
    "venv": ["torch", "torchaudio", "demucs.pretrained", "pydub", "pygame", "soundfile"],
    "venv-rvc": ["torch", "faiss", "librosa", "parselmouth", "pyworld", "soundfile"],
    "venv-mdx": ["torch", "audio_separator", "onnxruntime", "librosa", "soundfile"],
    "venv-enhance": ["torch", "resemble_enhance", "librosa", "soundfile"],
}
APP_DIRS = [
    "assets",
    "rvc",
    "voice_revolver_core",
    "voice_revolver_ui",
]
APP_FILES = [
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
RVC_REQUIRED_MODEL_FILES = [
    ("predictors", "rmvpe.pt"),
    ("predictors", "fcpe.pt"),
    ("embedders", "contentvec", "config.json"),
    ("embedders", "contentvec", "pytorch_model.bin"),
]
OBSOLETE_INSTALL_ITEMS = [
    ".gitignore",
    "AGENT_MEMORY.md",
    "README.md",
    "TASKLIST_PORTABLE.md",
    "build.py",
    "build_installer.py",
    "build_portable.py",
    "check_separator.py",
    "docs",
    "download_models.py",
    "installer.iss",
    "old",
    "patch_dataclass_bugs.py",
    "requirements.txt",
    "run.bat",
    "run_dev.bat",
    "run_dev.ps1",
    "runtime_hook.py",
    "sample",
    "setup_models.bat",
    "setup_venv_enhance.bat",
    "temp_reqs.txt",
    "temp_reqs2.txt",
    "test_core.py",
    "tests",
    "voice_revolver.spec",
]


class InstallationCancelled(RuntimeError):
    """Raised when installer cancellation is requested."""


@dataclass
class BootstrapOptions:
    install_root: Path
    app_data_root: Path
    model_root: Path
    venv_root: Path
    temp_root: Path
    logs_root: Path
    shortcut: bool
    dry_run: bool
    interactive: bool
    install_dependencies: bool
    download_models: bool
    install_scoop: bool
    log_path: Path
    python_exe: Optional[Path] = None
    launcher_exe: Optional[Path] = None


class ProgressLog:
    def __init__(
        self,
        path: Path,
        echo: bool = True,
        callback: Optional[Callable[[dict], None]] = None,
    ):
        self.path = path
        self.echo = echo
        self.callback = callback
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def event(self, stage: str, status: str, detail: str = "", percent: Optional[float] = None) -> None:
        payload = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "stage": stage,
            "status": status,
            "detail": detail,
            "percent": percent,
        }
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=True) + "\n")
        if self.echo:
            pct = "" if percent is None else f" [{percent:5.1f}%]"
            print(f"{stage}: {status}{pct} {detail}".rstrip(), flush=True)
        if self.callback:
            self.callback(payload)


class Bootstrapper:
    def __init__(
        self,
        options: BootstrapOptions,
        progress_callback: Optional[Callable[[dict], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ):
        self.options = options
        self.cancel_event = cancel_event or threading.Event()
        self.log = ProgressLog(options.log_path, callback=progress_callback)
        self.paths = PortablePaths(
            install_root=options.install_root,
            app_data_root=options.app_data_root,
            temp_root=options.temp_root,
            logs_root=options.logs_root,
            model_root=options.model_root,
            venv_root=options.venv_root,
            config_path=options.install_root / "config" / "portable.json",
        )
        self._process_lock = threading.Lock()
        self._current_process: Optional[subprocess.Popen] = None
        self._created_paths: list[Path] = []
        self._install_root_existed = options.install_root.exists()
        self._model_root_existed = options.model_root.exists()
        self._install_complete_marker = options.install_root / ".voice_revolver_install_complete"
        self._had_complete_marker = self._install_complete_marker.exists()

    def run(self) -> None:
        try:
            self.log.event("bootstrap", "start", "Voice Revolver AI bootstrap", 0)
            self._run_step(self._show_choices)
            self._run_step(self._prepare_directories)
            self._run_step(self._write_config)
            self._run_step(self._install_app_files)
            self._run_step(self._install_launcher)
            self._run_step(self._install_shortcut)
            self._run_step(self._ensure_python)
            self._run_step(self._install_venvs)
            self._run_step(self._install_models)
            self._run_step(self._download_models)
            self._run_step(self._validate_launcher)
            self._write_complete_marker()
            self.log.event("bootstrap", "complete", "Bootstrap flow complete", 100)
        except InstallationCancelled:
            self.log.event("bootstrap", "cancel", "Cancel requested; cleaning partial install")
            self._cleanup_partial_install()
            self.log.event("bootstrap", "cancelled", "Install canceled and cleanup finished")
            raise

    def cancel(self) -> None:
        self.cancel_event.set()
        with self._process_lock:
            process = self._current_process
        if process and process.poll() is None:
            self._terminate_process_tree(process)

    def _run_step(self, action: Callable[[], None]) -> None:
        self._check_cancel()
        action()
        self._check_cancel()

    def _check_cancel(self) -> None:
        if self.cancel_event.is_set():
            raise InstallationCancelled("Installation canceled")

    def _remember_created_path(self, path: Path) -> None:
        if not path.exists() and path not in self._created_paths:
            self._created_paths.append(path)

    def _write_complete_marker(self) -> None:
        if self.options.dry_run:
            return
        self._install_complete_marker.write_text(
            f"installed_at={time.strftime('%Y-%m-%dT%H:%M:%S')}\n",
            encoding="utf-8",
        )

    def _cleanup_partial_install(self) -> None:
        if self.options.dry_run:
            return

        if not self._install_root_existed and self.options.install_root.exists():
            self._remove_path(self.options.install_root)
        else:
            for path in sorted(self._created_paths, key=lambda p: len(p.parts), reverse=True):
                self._remove_path(path)

        if not self._model_root_existed and self.options.model_root.exists():
            self._remove_path(self.options.model_root)

    def _remove_path(self, path: Path) -> None:
        try:
            resolved = path.resolve()
            allowed_roots = [self.options.install_root.resolve(), self.options.model_root.resolve()]
            allowed_exact = {p.resolve() for p in self._created_paths}
            if not any(resolved == root or root in resolved.parents for root in allowed_roots) and resolved not in allowed_exact:
                return
            if resolved.exists():
                if resolved.is_dir():
                    shutil.rmtree(resolved)
                else:
                    resolved.unlink()
                self.log.event("cleanup", "removed", str(resolved))
        except Exception as exc:
            self.log.event("cleanup", "warning", f"{path}: {exc}")

    def _show_choices(self) -> None:
        self.log.event("choices", "install_root", str(self.options.install_root), 1)
        self.log.event("choices", "model_root", str(self.options.model_root), 2)
        self.log.event("choices", "venv_root", str(self.options.venv_root), 3)
        self.log.event("choices", "shortcut", str(self.options.shortcut), 4)
        self.log.event("choices", "dry_run", str(self.options.dry_run), 5)

    def _prepare_directories(self) -> None:
        self.log.event("directories", "prepare", "Creating install/app/model/temp folders", 8)
        if self.options.dry_run:
            return
        self._remember_created_path(self.options.install_root)
        self._remember_created_path(self.options.model_root)
        self.paths.ensure_dirs()
        self.options.install_root.mkdir(parents=True, exist_ok=True)

    def _write_config(self) -> None:
        self.log.event("config", "write", str(self.paths.config_path), 12)
        if self.options.dry_run:
            return
        self._remember_created_path(self.paths.config_path)
        write_portable_config(self.paths)

    def _install_app_files(self) -> None:
        self.log.event("app_files", "copy", f"runtime payload -> {self.options.install_root}", 18)
        if self.options.dry_run:
            return

        default_ignore = shutil.ignore_patterns(
            "__pycache__",
            "*.pyc",
        )
        rvc_ignore = shutil.ignore_patterns("models", "__pycache__", "*.pyc")

        self._remove_obsolete_install_items()

        for dirname in APP_DIRS:
            self._check_cancel()
            item = PROJECT_ROOT / dirname
            if not item.exists():
                continue
            dst = self.options.install_root / dirname
            self._remember_created_path(dst)
            ignore = rvc_ignore if dirname == "rvc" else default_ignore
            shutil.copytree(item, dst, dirs_exist_ok=True, ignore=ignore)

        tools_src = PROJECT_ROOT / "tools" / "portable_installer"
        tools_dst = self.options.install_root / "tools" / "portable_installer"
        self._remember_created_path(self.options.install_root / "tools")
        tools_dst.mkdir(parents=True, exist_ok=True)
        for filename in PORTABLE_TOOL_FILES:
            self._check_cancel()
            src = tools_src / filename
            if src.exists():
                shutil.copy2(src, tools_dst / filename)

        for filename in APP_FILES:
            self._check_cancel()
            item = PROJECT_ROOT / filename
            if not item.exists():
                continue
            dst = self.options.install_root / item.name
            self._remember_created_path(dst)
            shutil.copy2(item, dst)

    def _remove_obsolete_install_items(self) -> None:
        for name in OBSOLETE_INSTALL_ITEMS:
            path = self.options.install_root / name
            if not path.exists():
                continue
            self._remove_path(path)

    def _install_launcher(self) -> None:
        self.log.event("launcher", "install", "Installing voice-revolver launcher", 24)
        if self.options.dry_run:
            return

        target_exe = self.options.install_root / "voice-revolver.exe"
        if self.options.launcher_exe and self.options.launcher_exe.exists():
            self._remember_created_path(target_exe)
            shutil.copy2(self.options.launcher_exe, target_exe)
            return

        cmd_path = self.options.install_root / "voice-revolver.cmd"
        self._remember_created_path(cmd_path)
        cmd_path.write_text(
            "@echo off\r\n"
            "set VOICE_REVOLVER_CONFIG=%~dp0config\\portable.json\r\n"
            "\"%~dp0venvs\\venv\\Scripts\\python.exe\" \"%~dp0run.py\"\r\n"
            "pause\r\n",
            encoding="utf-8",
        )
        self.log.event("launcher", "warning", "voice-revolver.exe missing; wrote voice-revolver.cmd fallback")

    def _install_shortcut(self) -> None:
        if not self.options.shortcut:
            self.log.event("shortcut", "skip", "Shortcut disabled", 27)
            return

        self.log.event("shortcut", "create", "Desktop shortcut", 27)
        if self.options.dry_run:
            return

        target = self.options.install_root / "voice-revolver.exe"
        if not target.exists():
            target = self.options.install_root / "voice-revolver.cmd"
        desktop = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
        shortcut = desktop / "Voice Revolver AI.lnk"
        self._remember_created_path(shortcut)
        ps = (
            "$shell = New-Object -ComObject WScript.Shell; "
            f"$shortcut = $shell.CreateShortcut('{shortcut}'); "
            f"$shortcut.TargetPath = '{target}'; "
            f"$shortcut.WorkingDirectory = '{self.options.install_root}'; "
            "$shortcut.Save()"
        )
        self._run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps], "shortcut")

    def _ensure_python(self) -> None:
        self.log.event("python", "check", "Checking Python 3.11", 30)
        if self.options.dry_run:
            return

        python = self._find_python()
        if python:
            self.options.python_exe = python
            self.log.event("python", "found", str(python), 32)
            return

        if not self.options.install_scoop:
            raise RuntimeError("Python 3.11 not found and Scoop install disabled")

        self._ensure_scoop()
        self.log.event("python", "install", "Installing python311 through Scoop", 34)
        self._run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "scoop bucket add versions; scoop install python311"], "python")
        python = self._find_python()
        if not python:
            raise RuntimeError("Python 3.11 install completed but python executable not found")
        self.options.python_exe = python

    def _ensure_scoop(self) -> None:
        if shutil.which("scoop"):
            self.log.event("scoop", "found", "scoop in PATH")
            return
        self.log.event("scoop", "install", "Installing Scoop")
        self._run([
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "RemoteSigned",
            "-Command",
            "iwr -useb get.scoop.sh | iex",
        ], "scoop")

    def _find_python(self, include_managed_venv: bool = False) -> Optional[Path]:
        if self.options.python_exe and self.options.python_exe.exists():
            if include_managed_venv or not self._is_under_venv_root(self.options.python_exe):
                return self.options.python_exe

        candidates = [PROJECT_ROOT / "venv" / "Scripts" / "python.exe"]
        if include_managed_venv:
            candidates.append(self.options.install_root / "venvs" / "venv" / "Scripts" / "python.exe")

        for candidate in candidates:
            if not include_managed_venv and self._is_under_venv_root(candidate):
                continue
            if self._is_python_311(candidate):
                return candidate

        for command in (["py", "-3.11", "-c", "import sys; print(sys.executable)"], ["python", "-c", "import sys; print(sys.executable)"]):
            try:
                result = subprocess.run(command, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    candidate = Path(result.stdout.strip().splitlines()[-1])
                    if self._is_python_311(candidate):
                        return candidate
            except Exception:
                pass
        return None

    def _is_under_venv_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.options.venv_root.resolve())
            return True
        except ValueError:
            return False

    def _is_python_311(self, python: Path) -> bool:
        if not python.exists():
            return False
        try:
            result = subprocess.run([str(python), "-c", "import sys; print(sys.version_info[:2])"], capture_output=True, text=True, timeout=10)
            return "(3, 11)" in result.stdout
        except Exception:
            return False

    def _install_venvs(self) -> None:
        if not self.options.install_dependencies:
            self.log.event("venvs", "skip", "Dependency install disabled", 38)
            return
        if self.options.dry_run:
            for venv_name in LOCKS:
                self.log.event("venvs", "dry-run", f"Would create/install {venv_name}", 38)
            return

        python = self._find_python()
        if not python:
            raise RuntimeError("Python 3.11 not available for venv creation")

        for index, (venv_name, lock_name) in enumerate(LOCKS.items(), start=1):
            self._check_cancel()
            pct = 38 + index * 8
            venv_dir = self.options.venv_root / venv_name
            lock_file = self.options.install_root / lock_name
            if not lock_file.exists():
                lock_file = PROJECT_ROOT / lock_name
            lock_hash = self._file_hash(lock_file)
            marker = venv_dir / ".voice_revolver_lock.sha256"
            python_in_venv = venv_dir / "Scripts" / "python.exe"

            if python_in_venv.exists() and marker.exists() and marker.read_text(encoding="utf-8").strip() == lock_hash:
                self.log.event("venvs", "skip", f"{venv_name} already matches lock", pct)
                self._repair_lock_drift(venv_name, python_in_venv, lock_file)
                self._repair_bootstrap_packages(venv_name, python_in_venv, lock_file)
                self._apply_compat_patches(venv_name, python_in_venv)
                self._validate_imports(venv_name, python_in_venv)
                continue

            if python_in_venv.exists() and not marker.exists():
                self.log.event("venvs", "verify", f"{venv_name} exists without marker", pct)
                try:
                    self._repair_lock_drift(venv_name, python_in_venv, lock_file)
                    self._repair_bootstrap_packages(venv_name, python_in_venv, lock_file)
                    self._apply_compat_patches(venv_name, python_in_venv)
                    self._validate_imports(venv_name, python_in_venv)
                    marker.write_text(lock_hash, encoding="utf-8")
                    self.log.event("venvs", "skip", f"{venv_name} validated; marker restored", pct)
                    continue
                except Exception as exc:
                    self.log.event("venvs", "rebuild", f"{venv_name} validation failed: {exc}", pct)

            if venv_dir.exists():
                self.log.event("venvs", "clear", f"{venv_name} incomplete or lock changed", pct)
                self._remove_managed_venv(venv_dir)
                self._run([str(python), "-m", "venv", str(venv_dir)], "venvs")
            else:
                self.log.event("venvs", "create", str(venv_dir), pct)
                self._remember_created_path(venv_dir)
                self._run([str(python), "-m", "venv", str(venv_dir)], "venvs")
            self._run([str(python_in_venv), "-m", "pip", "install", "--upgrade", f"pip=={BOOTSTRAP_PIP_VERSION}"], "venvs")
            self.log.event("venvs", "install", f"{lock_name} (--no-deps exact lock)", pct + 2)
            self._run([str(python_in_venv), "-m", "pip", "install", "--no-deps", "-r", str(lock_file)], "venvs")
            self._repair_lock_drift(venv_name, python_in_venv, lock_file)
            self._repair_bootstrap_packages(venv_name, python_in_venv, lock_file)
            self._apply_compat_patches(venv_name, python_in_venv)
            self._validate_imports(venv_name, python_in_venv)
            marker.write_text(lock_hash, encoding="utf-8")

    def _install_models(self) -> None:
        self.log.event("models", "prepare", "Copying bundled RVC weights to model root", 74)
        if self.options.dry_run:
            return

        src = PROJECT_ROOT / "rvc" / "models"
        dst = self.options.model_root / "rvc"
        if src.exists():
            self._remember_created_path(dst)
            shutil.copytree(src, dst, dirs_exist_ok=True)
        self._validate_rvc_assets()

    def _validate_rvc_assets(self) -> None:
        rvc_root = self.options.model_root / "rvc"
        missing = [str(rvc_root.joinpath(*parts)) for parts in RVC_REQUIRED_MODEL_FILES if not rvc_root.joinpath(*parts).exists()]
        if missing:
            raise FileNotFoundError("Missing required RVC model assets:\n" + "\n".join(missing))
        self.log.event("models", "rvc-ok", f"Required RVC assets present in {rvc_root}")

    def _download_models(self) -> None:
        if not self.options.download_models:
            self.log.event("models", "skip-downloads", "Model downloads disabled", 80)
            return
        if self.options.dry_run:
            self.log.event("models", "dry-run", "Would download/verify model caches", 80)
            return

        python = self.options.venv_root / "venv" / "Scripts" / "python.exe"
        env = os.environ.copy()
        env["VOICE_REVOLVER_CONFIG"] = str(self.paths.config_path)
        code = (
            "import asyncio; "
            "from voice_revolver_core.infrastructure.portable_paths import load_portable_paths; "
            "from voice_revolver_core.infrastructure.model_manager import ModelManager; "
            "p=load_portable_paths(create=True); "
            "m=ModelManager(p.model_root); "
            "ok, err = asyncio.run(m.download_all_models(lambda name, prog: print(f'{name}:{prog:.3f}', flush=True))); "
            "raise SystemExit(0 if ok else (err or 'Model download failed'))"
        )
        self._run([str(python), "-c", code], "models", env=env, cwd=self.options.install_root)

    def _validate_launcher(self) -> None:
        self.log.event("launcher", "validate", "Checking launch files", 94)
        if self.options.dry_run:
            return
        run_py = self.options.install_root / "run.py"
        python = self.options.venv_root / "venv" / "Scripts" / "python.exe"
        if not run_py.exists():
            raise FileNotFoundError(run_py)
        if not python.exists():
            raise FileNotFoundError(python)
        launcher = self.options.install_root / "voice-revolver.exe"
        if launcher.exists():
            env = os.environ.copy()
            env["VOICE_REVOLVER_CONFIG"] = str(self.paths.config_path)
            self._run([str(launcher), "--validate-only"], "launcher", env=env, cwd=self.options.install_root)

    def _validate_imports(self, venv_name: str, python: Path) -> None:
        imports = VALIDATION_IMPORTS.get(venv_name, [])
        if not imports:
            return
        code = "; ".join(f"import {name}" for name in imports)
        self.log.event("validate", "imports", f"{venv_name}: {', '.join(imports)}")
        self._run([str(python), "-c", code], "validate")

    def _apply_compat_patches(self, venv_name: str, python: Path) -> None:
        if venv_name != "venv":
            return
        patch_script = self.options.install_root / "tools" / "portable_installer" / "compat_patches.py"
        if not patch_script.exists():
            patch_script = PROJECT_ROOT / "tools" / "portable_installer" / "compat_patches.py"
        self.log.event("compat", "patch", f"{venv_name}: Hydra Python 3.11 defaults")
        self._run([str(python), str(patch_script)], "compat")

    def _repair_lock_drift(self, venv_name: str, python: Path, lock_file: Path) -> None:
        code = r"""
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import sys

lock_file = Path(sys.argv[1])
mismatches = []
for raw in lock_file.read_text(encoding="utf-8").splitlines():
    line = raw.strip()
    if not line or line.startswith("#") or line.startswith("--") or "==" not in line:
        continue
    name, expected = line.split("==", 1)
    expected = expected.split(";", 1)[0].strip()
    try:
        actual = version(name)
    except PackageNotFoundError:
        actual = "<missing>"
    if actual != expected:
        mismatches.append(f"{name}=={actual} expected {expected}")
if mismatches:
    print("\n".join(mismatches[:50]))
    sys.exit(2)
"""
        result = subprocess.run(
            [str(python), "-c", code, str(lock_file)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            self.log.event("venvs", "lock-ok", f"{venv_name}: installed versions match lock")
            return
        detail = result.stdout.strip().splitlines()[0] if result.stdout.strip() else "lock version audit failed"
        self.log.event("venvs", "repair", f"{venv_name}: installing exact lock ({detail})")
        self._run([str(python), "-m", "pip", "install", "--no-deps", "-r", str(lock_file)], "venvs")

    def _repair_bootstrap_packages(self, venv_name: str, python: Path, lock_file: Path) -> None:
        if venv_name == "venv":
            self._repair_python_support_packages(python)
        self._repair_soundfile_package(venv_name, python, lock_file)

    def _repair_python_support_packages(self, python: Path) -> None:
        code = "import _distutils_hack, yaml; assert hasattr(yaml, 'Dumper')"
        result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            self.log.event("compat", "ok", "setuptools/PyYAML import check")
            return
        self.log.event("compat", "repair", "Reinstalling setuptools/PyYAML runtime files")
        self._run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "--no-cache-dir",
                f"setuptools=={BOOTSTRAP_SETUPTOOLS_VERSION}",
                f"PyYAML=={BOOTSTRAP_PYYAML_VERSION}",
            ],
            "compat",
        )

    def _repair_soundfile_package(self, venv_name: str, python: Path, lock_file: Path) -> None:
        version = self._locked_package_version(lock_file, "soundfile")
        if not version:
            return
        code = "import soundfile"
        result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            self.log.event("compat", "ok", f"{venv_name}: soundfile import check")
            return
        detail = result.stderr.strip().splitlines()[-1] if result.stderr.strip() else "soundfile import failed"
        self.log.event("compat", "repair", f"{venv_name}: reinstalling soundfile=={version} ({detail})")
        self._run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "--no-cache-dir",
                "--no-deps",
                f"soundfile=={version}",
            ],
            "compat",
        )

    def _locked_package_version(self, lock_file: Path, package: str) -> Optional[str]:
        prefix = f"{package.lower()}=="
        try:
            for line in lock_file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.lower().startswith(prefix):
                    return stripped.split("==", 1)[1]
        except FileNotFoundError:
            return None
        return None

    def _remove_managed_venv(self, venv_dir: Path) -> None:
        try:
            venv_dir.resolve().relative_to(self.options.venv_root.resolve())
        except ValueError as exc:
            raise RuntimeError(f"Refusing to remove venv outside managed root: {venv_dir}") from exc

        def onerror(func, path, exc_info):
            if isinstance(exc_info[1], FileNotFoundError):
                return
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except FileNotFoundError:
                return
            except Exception:
                raise

        try:
            shutil.rmtree(venv_dir, onerror=onerror)
            if venv_dir.exists():
                shutil.rmtree(venv_dir, ignore_errors=True)
            if venv_dir.exists():
                raise OSError(f"Path still exists after delete: {venv_dir}")
        except Exception as exc:
            raise RuntimeError(
                f"Could not remove existing venv: {venv_dir}. Close Voice Revolver and any Python processes, then retry."
            ) from exc

    def _run(
        self,
        command: list[str],
        stage: str,
        env: Optional[dict[str, str]] = None,
        cwd: Optional[Path] = None,
    ) -> None:
        self.log.event(stage, "run", " ".join(command))
        if self.options.dry_run:
            return
        self._check_cancel()
        process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        with self._process_lock:
            self._current_process = process
        try:
            output_queue: queue.Queue[Optional[str]] = queue.Queue()

            def read_output() -> None:
                assert process.stdout is not None
                for line in process.stdout:
                    output_queue.put(line)
                output_queue.put(None)

            reader = threading.Thread(target=read_output, daemon=True)
            reader.start()

            output_done = False
            while not output_done:
                if self.cancel_event.is_set():
                    self._terminate_process_tree(process)
                    raise InstallationCancelled("Installation canceled")
                try:
                    line = output_queue.get(timeout=0.1)
                except queue.Empty:
                    if process.poll() is not None and not reader.is_alive():
                        break
                    continue
                if line is None:
                    output_done = True
                    continue
                line = line.rstrip()
                if line:
                    self.log.event(stage, "output", line)

            return_code = process.wait()
            if return_code != 0:
                raise RuntimeError(f"Command failed ({return_code}): {' '.join(command)}")
        finally:
            with self._process_lock:
                if self._current_process is process:
                    self._current_process = None

    def _terminate_process_tree(self, process: subprocess.Popen) -> None:
        if process.poll() is not None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    def _file_hash(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()


def _prompt_path(label: str, default: Path) -> Path:
    raw = input(f"{label} [{default}]: ").strip().strip('"')
    return Path(raw).expanduser() if raw else default


def _prompt_bool(label: str, default: bool) -> bool:
    suffix = "Y/n" if default else "y/N"
    raw = input(f"{label} [{suffix}]: ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes", "1", "true"}


def parse_args(argv: Optional[Iterable[str]] = None) -> BootstrapOptions:
    parser = argparse.ArgumentParser(description="Voice Revolver AI portable installer bootstrap")
    parser.add_argument("--interactive", action="store_true", help="Ask install/model/shortcut prompts in terminal")
    parser.add_argument("--dry-run", action="store_true", help="Emit actions without mutating files")
    parser.add_argument("--install-root", type=Path, help="Program install folder")
    parser.add_argument("--app-data-root", type=Path, help="App data folder")
    parser.add_argument("--model-root", type=Path, help="Models/weights folder")
    parser.add_argument("--venv-root", type=Path, help="Virtual environment folder")
    parser.add_argument("--temp-root", type=Path, help="Temp folder")
    parser.add_argument("--logs-root", type=Path, help="Logs folder")
    parser.add_argument("--shortcut", dest="shortcut", action="store_true", help="Create desktop shortcut")
    parser.add_argument("--no-shortcut", dest="shortcut", action="store_false", help="Do not create desktop shortcut")
    parser.set_defaults(shortcut=False)
    parser.add_argument("--install-dependencies", action="store_true", help="Create venvs and install lock files")
    parser.add_argument("--download-models", action="store_true", help="Download model caches during bootstrap")
    parser.add_argument("--install-scoop", action="store_true", help="Allow Scoop install if Python 3.11 is missing")
    parser.add_argument("--python-exe", type=Path, help="Existing Python 3.11 executable")
    parser.add_argument("--launcher-exe", type=Path, help="Built voice-revolver.exe to copy into install root")
    parser.add_argument("--log-path", type=Path, help="Installer JSONL log path")
    args = parser.parse_args(argv)

    app_data_default = default_app_data_root()
    install_root = args.install_root or default_install_root()
    app_data_root = args.app_data_root or app_data_default
    model_root = args.model_root or app_data_root / "models"

    if args.interactive:
        install_root = _prompt_path("Where install program?", install_root)
        model_root = _prompt_path("Where store models/weights?", model_root)
        shortcut = _prompt_bool("Create desktop shortcut?", args.shortcut)
    else:
        shortcut = args.shortcut

    venv_root = args.venv_root or install_root / "venvs"
    temp_root = args.temp_root or app_data_root / "temp"
    logs_root = args.logs_root or app_data_root / "logs"
    log_path = args.log_path or logs_root / "installer-bootstrap.jsonl"

    return BootstrapOptions(
        install_root=install_root,
        app_data_root=app_data_root,
        model_root=model_root,
        venv_root=venv_root,
        temp_root=temp_root,
        logs_root=logs_root,
        shortcut=shortcut,
        dry_run=args.dry_run,
        interactive=args.interactive,
        install_dependencies=args.install_dependencies,
        download_models=args.download_models,
        install_scoop=args.install_scoop,
        log_path=log_path,
        python_exe=args.python_exe,
        launcher_exe=args.launcher_exe,
    )


def main(argv: Optional[Iterable[str]] = None) -> int:
    options = parse_args(argv)
    Bootstrapper(options).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
