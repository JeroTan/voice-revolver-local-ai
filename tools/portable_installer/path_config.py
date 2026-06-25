"""Small path config helpers for installer tooling."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path


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
        os.environ["VOICE_REVOLVER_INSTALL_ROOT"] = str(self.install_root)
        os.environ["VOICE_REVOLVER_APP_DATA"] = str(self.app_data_root)
        os.environ["VOICE_REVOLVER_TEMP_DIR"] = str(self.temp_root)
        os.environ["VOICE_REVOLVER_LOG_DIR"] = str(self.logs_root)
        os.environ["VOICE_REVOLVER_MODEL_DIR"] = str(self.model_root)
        os.environ["VOICE_REVOLVER_VENV_DIR"] = str(self.venv_root)
        os.environ.setdefault("HF_HOME", str(self.model_root / "huggingface"))
        os.environ.setdefault("HF_HUB_CACHE", str(self.model_root / "huggingface" / "hub"))
        os.environ.setdefault("TRANSFORMERS_CACHE", str(self.model_root / "huggingface" / "transformers"))
        os.environ.setdefault("TORCH_HOME", str(self.model_root / "torch"))
        os.environ.setdefault("XDG_CACHE_HOME", str(self.model_root / "xdg"))
        os.environ.setdefault("VOICE_REVOLVER_MDX_MODEL_DIR", str(self.model_root / "mdx"))
        os.environ.setdefault("VOICE_REVOLVER_RVC_MODEL_DIR", str(self.model_root / "rvc"))
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


def read_portable_config(path: Path) -> PortablePaths:
    with path.open("r", encoding="utf-8-sig") as f:
        data = json.load(f)
    app_data_root = Path(data["app_data_root"])
    paths = PortablePaths(
        install_root=Path(data["install_root"]),
        app_data_root=app_data_root,
        temp_root=Path(data.get("temp_root", app_data_root / "temp")),
        logs_root=Path(data.get("logs_root", app_data_root / "logs")),
        model_root=Path(data.get("model_root", app_data_root / "models")),
        venv_root=Path(data.get("venv_root", app_data_root / "venvs")),
        config_path=path,
    )
    paths.apply_environment()
    return paths


def write_portable_config(paths: PortablePaths) -> None:
    paths.config_path.parent.mkdir(parents=True, exist_ok=True)
    with paths.config_path.open("w", encoding="utf-8") as f:
        json.dump(paths.to_json_dict(), f, indent=2)
        f.write("\n")
