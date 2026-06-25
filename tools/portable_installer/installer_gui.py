"""
Tkinter installer UI for Voice Revolver AI.

This is the future `VoiceRevolverAI-Setup.exe` entry point. It asks for install
folder, model folder, shortcut choice, then runs the shared bootstrap engine.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

def _source_root() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled = Path(sys._MEIPASS) / "app_source"
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parents[2]


PROJECT_ROOT = _source_root()
sys.path.insert(0, str(PROJECT_ROOT))

from tools.portable_installer.bootstrap import BootstrapOptions, Bootstrapper, InstallationCancelled
from tools.portable_installer.path_config import (
    default_app_data_root,
    default_install_root,
)


class InstallerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Voice Revolver AI Setup")
        self.root.geometry("720x520")
        self.root.minsize(680, 480)

        app_data = default_app_data_root()
        self.install_var = tk.StringVar(value=str(default_install_root()))
        self.model_var = tk.StringVar(value=str(app_data / "models"))
        self.shortcut_var = tk.BooleanVar(value=False)
        self.deps_var = tk.BooleanVar(value=True)
        self.models_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.detail_var = tk.StringVar(value="")
        self.progress_var = tk.DoubleVar(value=0)
        self.log_path = app_data / "logs" / "installer-bootstrap.jsonl"
        self.success = False
        self.installing = False
        self.cancel_event = threading.Event()
        self.bootstrapper: Bootstrapper | None = None

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._close_or_cancel)

    def _build_ui(self) -> None:
        outer = ttk.Frame(self.root, padding=18)
        outer.pack(fill=tk.BOTH, expand=True)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(8, weight=1)

        title = ttk.Label(outer, text="Voice Revolver AI Setup", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(outer, text="Install folder").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.install_var).grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(outer, text="Browse", command=self._browse_install).grid(row=1, column=2, pady=4)

        ttk.Label(outer, text="Models/weights folder").grid(row=2, column=0, sticky="w", pady=4)
        ttk.Entry(outer, textvariable=self.model_var).grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        ttk.Button(outer, text="Browse", command=self._browse_models).grid(row=2, column=2, pady=4)

        ttk.Checkbutton(outer, text="Create desktop shortcut", variable=self.shortcut_var).grid(row=3, column=1, sticky="w", pady=4)
        ttk.Checkbutton(outer, text="Install Python environments and dependencies", variable=self.deps_var).grid(row=4, column=1, sticky="w", pady=4)
        ttk.Checkbutton(outer, text="Download model caches during setup", variable=self.models_var).grid(row=5, column=1, sticky="w", pady=4)

        ttk.Separator(outer).grid(row=6, column=0, columnspan=3, sticky="ew", pady=12)

        ttk.Label(outer, textvariable=self.status_var, font=("Segoe UI", 10, "bold")).grid(row=7, column=0, columnspan=3, sticky="w")
        ttk.Label(outer, textvariable=self.detail_var).grid(row=8, column=0, columnspan=3, sticky="new", pady=(2, 8))
        ttk.Progressbar(outer, variable=self.progress_var, maximum=100).grid(row=9, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        self.log_text = tk.Text(outer, height=10, wrap="word")
        self.log_text.grid(row=10, column=0, columnspan=3, sticky="nsew", pady=(0, 12))
        outer.rowconfigure(10, weight=1)

        button_row = ttk.Frame(outer)
        button_row.grid(row=11, column=0, columnspan=3, sticky="e")
        self.start_btn = ttk.Button(button_row, text="Install", command=self._start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.run_btn = ttk.Button(button_row, text="Run the app", command=self._run_app, state="disabled")
        self.run_btn.pack(side=tk.LEFT, padx=4)
        self.run_close_btn = ttk.Button(button_row, text="Run and close", command=self._run_and_close, state="disabled")
        self.run_close_btn.pack(side=tk.LEFT, padx=4)
        self.close_btn = ttk.Button(button_row, text="Close", command=self._close_or_cancel)
        self.close_btn.pack(side=tk.LEFT, padx=4)

    def _browse_install(self) -> None:
        path = filedialog.askdirectory(initialdir=str(Path(self.install_var.get()).parent))
        if path:
            self.install_var.set(path)

    def _browse_models(self) -> None:
        path = filedialog.askdirectory(initialdir=str(Path(self.model_var.get()).parent))
        if path:
            self.model_var.set(path)

    def _start(self) -> None:
        self.cancel_event = threading.Event()
        self.start_btn.config(state="disabled")
        self.run_btn.config(state="disabled")
        self.run_close_btn.config(state="disabled")
        self.close_btn.config(text="Cancel", state="normal")
        self.success = False
        self.installing = True
        self.log_text.delete("1.0", tk.END)
        thread = threading.Thread(target=self._run_bootstrap, daemon=True)
        thread.start()

    def _run_bootstrap(self) -> None:
        try:
            install_root = Path(self.install_var.get()).expanduser()
            app_data = default_app_data_root()
            options = BootstrapOptions(
                install_root=install_root,
                app_data_root=app_data,
                model_root=Path(self.model_var.get()).expanduser(),
                venv_root=install_root / "venvs",
                temp_root=app_data / "temp",
                logs_root=app_data / "logs",
                shortcut=self.shortcut_var.get(),
                dry_run=False,
                interactive=False,
                install_dependencies=self.deps_var.get(),
                download_models=self.models_var.get(),
                install_scoop=True,
                log_path=self.log_path,
                python_exe=None,
                launcher_exe=PROJECT_ROOT / "dist" / "voice-revolver.exe",
            )
            self.bootstrapper = Bootstrapper(options, progress_callback=self._progress_from_thread, cancel_event=self.cancel_event)
            self.bootstrapper.run()
            self.success = True
            self.root.after(0, self._install_success)
        except InstallationCancelled:
            self.root.after(0, self._install_canceled)
        except Exception as exc:
            self.root.after(0, self._install_failed, exc)
        finally:
            self.bootstrapper = None

    def _progress_from_thread(self, event: dict) -> None:
        self.root.after(0, self._update_progress, event)

    def _update_progress(self, event: dict) -> None:
        stage = event.get("stage", "")
        status = event.get("status", "")
        detail = event.get("detail", "")
        percent = event.get("percent")
        self.status_var.set(f"{stage}: {status}")
        self.detail_var.set(detail)
        if percent is not None:
            self.progress_var.set(float(percent))
        self.log_text.insert(tk.END, f"{stage}: {status} {detail}\n")
        self.log_text.see(tk.END)

    def _install_success(self) -> None:
        self.installing = False
        self.status_var.set("Install successful")
        self.detail_var.set("Voice Revolver AI is ready.")
        self.progress_var.set(100)
        self.start_btn.config(state="normal")
        self.run_btn.config(state="normal")
        self.run_close_btn.config(state="normal")
        self.close_btn.config(text="Close", state="normal")
        messagebox.showinfo("Install successful", "Voice Revolver AI installed successfully.")

    def _install_failed(self, exc: Exception) -> None:
        self.installing = False
        self.start_btn.config(state="normal")
        self.run_btn.config(state="disabled")
        self.run_close_btn.config(state="disabled")
        self.close_btn.config(text="Close", state="normal")
        self.status_var.set("Install failed")
        self.detail_var.set(str(exc))
        messagebox.showerror("Install failed", f"{exc}\n\nLog:\n{self.log_path}")

    def _install_canceled(self) -> None:
        self.installing = False
        self.success = False
        self.start_btn.config(state="normal")
        self.run_btn.config(state="disabled")
        self.run_close_btn.config(state="disabled")
        self.close_btn.config(text="Close", state="normal")
        self.status_var.set("Install canceled")
        self.detail_var.set("Partial install cleaned where safe.")

    def _close_or_cancel(self) -> None:
        if not self.installing:
            self.root.destroy()
            return
        self.status_var.set("Canceling install")
        self.detail_var.set("Stopping active command and cleaning partial files...")
        self.close_btn.config(state="disabled")
        self.cancel_event.set()
        if self.bootstrapper:
            self.bootstrapper.cancel()

    def _run_app(self, close_after: bool = False) -> None:
        install_root = Path(self.install_var.get()).expanduser()
        exe = install_root / "voice-revolver.exe"
        fallback = install_root / "voice-revolver.cmd"
        target = exe if exe.exists() else fallback
        if not target.exists():
            messagebox.showerror("Run failed", f"Launcher not found:\n{target}")
            return
        subprocess.Popen([str(target)], cwd=str(install_root))
        if close_after:
            self.root.destroy()

    def _run_and_close(self) -> None:
        self._run_app(close_after=True)


def main() -> int:
    if "--validate-only" in sys.argv:
        required = [
            PROJECT_ROOT / "run.py",
            PROJECT_ROOT / "voice_revolver_ui",
            PROJECT_ROOT / "voice_revolver_core",
            PROJECT_ROOT / "dist" / "voice-revolver.exe",
        ]
        missing = [str(path) for path in required if not path.exists()]
        if missing:
            print("Missing setup payload:")
            print("\n".join(missing))
            return 1
        print("Setup payload validation OK")
        return 0

    root = tk.Tk()
    InstallerApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
