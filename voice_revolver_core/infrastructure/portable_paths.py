"""
Portable path resolution for Voice Revolver AI.

Development defaults stay compatible with run_dev.bat. Installed launchers can
override paths through a JSON config file or environment variables.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional


APP_DIR_NAME = "VoiceRevolverAI"
CONFIG_ENV = "VOICE_REVOLVER_CONFIG"


def default_app_data_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", Path.home())) / APP_DIR_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    return Path.home() / ".local" / "share" / APP_DIR_NAME


def default_install_root() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Voice Revolver AI"
    if sys.platform == "darwin":
        return Path("/Applications") / "Voice Revolver AI.app"
    return Path.home() / ".local" / "opt" / "voice-revolver-ai"


def default_config_path() -> Path:
    explicit = os.environ.get(CONFIG_ENV)
    if explicit:
        return Path(explicit)
    return default_app_data_root() / "config" / "portable.json"


@dataclass(frozen=True)
class PortablePaths:
    install_root: Path
    app_data_root: Path
    temp_root: Path
    logs_root: Path
    model_root: Path
    venv_root: Path
    config_path: Path

    def ensure_dirs(self) -> None:
        for path in (
            self.app_data_root,
            self.temp_root,
            self.logs_root,
            self.model_root,
            self.venv_root,
            self.config_path.parent,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def apply_environment(self) -> None:
        """Set process env vars before AI libraries import/cache models."""
        os.environ["VOICE_REVOLVER_INSTALL_ROOT"] = str(self.install_root)
        os.environ["VOICE_REVOLVER_APP_DATA"] = str(self.app_data_root)
        os.environ["VOICE_REVOLVER_TEMP_DIR"] = str(self.temp_root)
        os.environ["VOICE_REVOLVER_LOG_DIR"] = str(self.logs_root)
        os.environ["VOICE_REVOLVER_MODEL_DIR"] = str(self.model_root)
        os.environ["VOICE_REVOLVER_VENV_DIR"] = str(self.venv_root)

        hf_root = self.model_root / "huggingface"
        torch_root = self.model_root / "torch"
        xdg_root = self.model_root / "xdg"
        mdx_root = self.model_root / "mdx"
        rvc_root = self.model_root / "rvc"

        os.environ.setdefault("HF_HOME", str(hf_root))
        os.environ.setdefault("HF_HUB_CACHE", str(hf_root / "hub"))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_root / "transformers"))
        os.environ.setdefault("TORCH_HOME", str(torch_root))
        os.environ.setdefault("XDG_CACHE_HOME", str(xdg_root))
        os.environ.setdefault("VOICE_REVOLVER_MDX_MODEL_DIR", str(mdx_root))
        os.environ.setdefault("VOICE_REVOLVER_RVC_MODEL_DIR", str(rvc_root))
        os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

    def to_json_dict(self) -> dict[str, str]:
        return {
            "install_root": str(self.install_root),
            "app_data_root": str(self.app_data_root),
            "temp_root": str(self.temp_root),
            "logs_root": str(self.logs_root),
            "model_root": str(self.model_root),
            "venv_root": str(self.venv_root),
        }


def _read_config(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Portable config must be JSON object: {path}")
    return data


def _path_from(
    key: str,
    env_name: str,
    config: Mapping[str, Any],
    fallback: Path,
) -> Path:
    value = os.environ.get(env_name) or config.get(key)
    return Path(value).expanduser() if value else fallback


def load_portable_paths(
    config_path: Optional[Path] = None,
    create: bool = False,
) -> PortablePaths:
    config_path = Path(config_path) if config_path else default_config_path()
    config = _read_config(config_path)

    app_data_root = _path_from(
        "app_data_root",
        "VOICE_REVOLVER_APP_DATA",
        config,
        default_app_data_root(),
    )
    install_root = _path_from(
        "install_root",
        "VOICE_REVOLVER_INSTALL_ROOT",
        config,
        default_install_root(),
    )
    temp_root = _path_from(
        "temp_root",
        "VOICE_REVOLVER_TEMP_DIR",
        config,
        app_data_root / "temp",
    )
    logs_root = _path_from(
        "logs_root",
        "VOICE_REVOLVER_LOG_DIR",
        config,
        app_data_root / "logs",
    )
    model_root = _path_from(
        "model_root",
        "VOICE_REVOLVER_MODEL_DIR",
        config,
        app_data_root / "models",
    )
    venv_root = _path_from(
        "venv_root",
        "VOICE_REVOLVER_VENV_DIR",
        config,
        app_data_root / "venvs",
    )

    paths = PortablePaths(
        install_root=install_root,
        app_data_root=app_data_root,
        temp_root=temp_root,
        logs_root=logs_root,
        model_root=model_root,
        venv_root=venv_root,
        config_path=config_path,
    )
    if create:
        paths.ensure_dirs()
    paths.apply_environment()
    return paths


def write_portable_config(paths: PortablePaths) -> None:
    paths.config_path.parent.mkdir(parents=True, exist_ok=True)
    with paths.config_path.open("w", encoding="utf-8") as f:
        json.dump(paths.to_json_dict(), f, indent=2)
        f.write("\n")
