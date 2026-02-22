"""
Input Panel Component - Audio Separation Workspace
Top section with file selection, model selection, and separation controls
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import logging

from voice_revolver_ui.components.file_selector import FileSelector

logger = logging.getLogger(__name__)


class InputPanel(ttk.Frame):
    """
    Input panel for audio separation workspace.
    
    Features:
    - File selection for audio input
    - Model selection (demucs/mdx)
    - Device selection (cpu/cuda)
    - Improve Vocals option
    - Separation trigger button
    """
    
    def __init__(
        self,
        parent,
        device: str = "cpu",
        on_separate: Optional[Callable[[], None]] = None,
        **kwargs
    ):
        """
        Initialize the input panel.
        
        Args:
            parent: Parent tkinter widget
            device: Processing device ("cpu" or "cuda") from startup dialog
            on_separate: Callback when separation is triggered
            **kwargs: Additional configuration for the Frame
        """
        super().__init__(parent, **kwargs)
        
        self.on_separate_callback = on_separate
        
        # Variables
        self.audio_file_var = tk.StringVar()
        self.model_var = tk.StringVar(value="demucs")
        self.device_var = tk.StringVar(value=device)
        self.improve_vocals_var = tk.BooleanVar(value=False)
        
        # UI setup
        self._setup_ui()
        
    def _setup_ui(self):
        """Create and layout child widgets."""
        # Configure padding
        self.configure(padding="10")
        
        # File selector row
        file_frame = ttk.Frame(self)
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.file_selector = FileSelector(
            file_frame,
            label="Audio File:",
            mode="file",
            file_types=(
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
                ("All Files", "*.*")
            ),
            on_select=self._on_file_selected,
            entry_width=50
        )
        self.file_selector.pack(fill=tk.X)
        
        # Options row
        options_frame = ttk.Frame(self)
        options_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Model selection
        ttk.Label(options_frame, text="Separation Model:").pack(side=tk.LEFT, padx=(0, 5))
        model_combo = ttk.Combobox(
            options_frame,
            textvariable=self.model_var,
            values=["demucs", "mdx"],
            state="readonly",
            width=12
        )
        model_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # Device selection
        ttk.Label(options_frame, text="Device:").pack(side=tk.LEFT, padx=(0, 5))
        device_combo = ttk.Combobox(
            options_frame,
            textvariable=self.device_var,
            values=self._get_available_devices(),
            state="readonly",
            width=10
        )
        device_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        # Improve Vocals checkbox
        improve_check = ttk.Checkbutton(
            options_frame,
            text="Improve Vocals (noise reduction + enhancement)",
            variable=self.improve_vocals_var
        )
        improve_check.pack(side=tk.LEFT, padx=(0, 15))
        
        # Separate button
        self.separate_btn = ttk.Button(
            options_frame,
            text="Separate Audio",
            command=self._on_separate_clicked,
            width=15
        )
        self.separate_btn.pack(side=tk.LEFT, padx=(0, 5))
        
    def _get_available_devices(self) -> list:
        """Get list of available compute devices."""
        devices = ["cpu"]
        try:
            import torch
            if torch.cuda.is_available():
                devices.append("cuda")
        except (ImportError, OSError):
            pass
        return devices
    
    def _on_file_selected(self, path: str):
        """Handle file selection."""
        self.audio_file_var.set(path)
        logger.info(f"Audio file selected: {Path(path).name}")
    
    def _on_separate_clicked(self):
        """Handle separation button click."""
        if not self.audio_file_var.get():
            logger.warning("No audio file selected")
            return
        
        audio_path = Path(self.audio_file_var.get())
        if not audio_path.exists():
            logger.error(f"Audio file not found: {audio_path}")
            return
        
        # Call external callback
        if self.on_separate_callback:
            self.on_separate_callback()
    
    def get_audio_path(self) -> Optional[Path]:
        """Get selected audio file path."""
        path_str = self.audio_file_var.get()
        return Path(path_str) if path_str else None
    
    def get_model(self) -> str:
        """Get selected separation model."""
        return self.model_var.get()
    
    def get_device(self) -> str:
        """Get selected device."""
        return self.device_var.get()
    
    def get_improve_vocals(self) -> bool:
        """Get improve vocals flag."""
        return self.improve_vocals_var.get()
    
    def set_enabled(self, enabled: bool):
        """Enable/disable controls during processing."""
        state = 'normal' if enabled else 'disabled'
        self.separate_btn.config(state=state)
        self.file_selector.browse_btn.config(state=state)
