"""Input panel for Voice Enhancement workspace."""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import Callable, Optional, Dict

from voice_revolver_ui.components.file_selector import FileSelector
from voice_revolver_ui.components.labeled_slider import LabeledSlider


class InputPanel(ttk.Frame):
    """Left panel with file selection, enhancement parameters, and export controls."""
    
    # Default enhancement parameters (Resemble Enhance recommended values)
    DEFAULT_PARAMS = {
        'nfe': 100,         # Number of function evaluations (quality)
        'temperature': 0.33,  # Prior temperature
        'solver': 'rk4',    # Numerical solver
        'denoise_first': False  # Pre-denoising
    }
    
    def __init__(
        self,
        parent: ttk.Frame,
        on_process: Optional[Callable] = None,
        on_export: Optional[Callable] = None
    ):
        """Initialize the input panel.
        
        Args:
            parent: Parent widget
            on_process: Callback when Start Enhancement is clicked
            on_export: Callback when Export is clicked
        """
        super().__init__(parent, padding=10)
        
        self.on_process = on_process
        self.on_export = on_export
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        
        row = 0
        
        # ===== Audio File Selection =====
        file_frame = ttk.LabelFrame(self, text="Input Audio", padding=10)
        file_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)
        row += 1
        
        self.audio_selector = FileSelector(
            file_frame,
            label="Select Audio File:",
            mode="file",
            file_types=(
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg"),
                ("All Files", "*.*")
            ),
            entry_width=35
        )
        self.audio_selector.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        # ===== Enhancement Parameters =====
        params_frame = ttk.LabelFrame(self, text="Enhancement Parameters", padding=10)
        params_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        params_frame.columnconfigure(0, weight=1)
        row += 1
        
        param_row = 0
        
        # Quality (NFE) slider
        self.nfe_slider = LabeledSlider(
            params_frame,
            label="Quality (NFE):",
            from_=1,
            to=128,
            initial_value=self.DEFAULT_PARAMS['nfe'],
            value_format="{:.0f}",
            length=250
        )
        self.nfe_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # NFE description
        nfe_desc = ttk.Label(
            params_frame,
            text="Number of function evaluations (1=fastest low quality, 128=slowest highest quality)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        nfe_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Temperature slider
        self.temp_slider = LabeledSlider(
            params_frame,
            label="Temperature:",
            from_=0.01,
            to=1.0,
            initial_value=self.DEFAULT_PARAMS['temperature'],
            value_format="{:.2f}",
            length=250
        )
        self.temp_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Temperature description
        temp_desc = ttk.Label(
            params_frame,
            text="Prior temperature (0.01=conservative/subtle, 1.0=aggressive/may add artifacts)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        temp_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Solver dropdown
        solver_frame = ttk.Frame(params_frame)
        solver_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        ttk.Label(solver_frame, text="Solver:", width=15).grid(row=0, column=0, sticky=tk.W)
        
        self.solver_var = tk.StringVar(value=self.DEFAULT_PARAMS['solver'])
        self.solver_combo = ttk.Combobox(
            solver_frame,
            textvariable=self.solver_var,
            values=['euler', 'midpoint', 'rk4'],
            state="readonly",
            width=15
        )
        self.solver_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Solver description
        solver_desc = ttk.Label(
            params_frame,
            text="Numerical solver (euler=fast, midpoint=balanced, rk4=best quality, slowest)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        solver_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Denoise first checkbox
        self.denoise_var = tk.BooleanVar(value=self.DEFAULT_PARAMS['denoise_first'])
        self.denoise_check = ttk.Checkbutton(
            params_frame,
            text="Denoise First (pre-process with noise reduction before enhancement)",
            variable=self.denoise_var
        )
        self.denoise_check.grid(row=param_row, column=0, sticky=tk.W, pady=5)
        param_row += 1
        
        # Reset to defaults button
        reset_btn = ttk.Button(
            params_frame,
            text="Reset All to Defaults",
            command=self._reset_params
        )
        reset_btn.grid(row=param_row, column=0, sticky=tk.W, pady=(10, 0))
        param_row += 1
        
        # ===== Export Settings =====
        export_frame = ttk.LabelFrame(self, text="Export Settings", padding=10)
        export_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        export_frame.columnconfigure(0, weight=1)
        row += 1
        
        # Output format
        format_container = ttk.Frame(export_frame)
        format_container.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(format_container, text="Output Format:", width=15).grid(row=0, column=0, sticky=tk.W)
        
        self.output_format_var = tk.StringVar(value="wav")
        self.format_combo = ttk.Combobox(
            format_container,
            textvariable=self.output_format_var,
            values=["wav", "mp3", "flac", "ogg"],
            state="readonly",
            width=15
        )
        self.format_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Use edited audio checkbox
        self.use_edited_var = tk.BooleanVar(value=False)
        self.use_edited_check = ttk.Checkbutton(
            export_frame,
            text="Use edited audio (with curve edits applied)",
            variable=self.use_edited_var
        )
        self.use_edited_check.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        # ===== Action Buttons =====
        buttons_frame = ttk.Frame(self)
        buttons_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        buttons_frame.columnconfigure(0, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        row += 1
        
        self.process_btn = ttk.Button(
            buttons_frame,
            text="Start Enhancement",
            command=self._on_process_clicked
        )
        self.process_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.export_btn = ttk.Button(
            buttons_frame,
            text="Export",
            command=self._on_export_clicked,
            state="disabled"
        )
        self.export_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
    
    def _reset_params(self):
        """Reset all parameters to default values."""
        self.nfe_slider.set(self.DEFAULT_PARAMS['nfe'])
        self.temp_slider.set(self.DEFAULT_PARAMS['temperature'])
        self.solver_var.set(self.DEFAULT_PARAMS['solver'])
        self.denoise_var.set(self.DEFAULT_PARAMS['denoise_first'])
    
    def _on_process_clicked(self):
        """Handle Start Enhancement button click."""
        if self.on_process:
            self.on_process()
    
    def _on_export_clicked(self):
        """Handle Export button click."""
        if self.on_export:
            self.on_export()
    
    # ===== Public API =====
    
    def get_audio_path(self) -> str:
        """Get the selected audio file path.
        
        Returns:
            Path to audio file, or empty string if none selected
        """
        return self.audio_selector.get()
    
    def get_enhancement_params(self) -> Dict[str, any]:
        """Get current enhancement parameters.
        
        Returns:
            Dictionary with keys: nfe, temperature, solver, denoise_first
        """
        return {
            'nfe': int(self.nfe_slider.get()),
            'temperature': float(self.temp_slider.get()),
            'solver': self.solver_var.get(),
            'denoise_first': self.denoise_var.get()
        }
    
    def get_output_format(self) -> str:
        """Get selected output format.
        
        Returns:
            Format string: 'wav', 'mp3', 'flac', or 'ogg'
        """
        return self.output_format_var.get()
    
    def get_use_edited(self) -> bool:
        """Get 'Use edited version' checkbox state.
        
        Returns:
            True if curve-edited version should be exported
        """
        return self.use_edited_var.get()
    
    def set_processing(self, is_processing: bool):
        """Enable/disable controls during processing.
        
        Args:
            is_processing: True to disable controls, False to enable
        """
        state = "disabled" if is_processing else "normal"
        
        # File selector
        self.audio_selector.set_enabled(not is_processing)
        
        # Parameter sliders - disable slider and entry
        self.nfe_slider.configure_slider(state=state)
        self.nfe_slider.configure_entry(state=state)
        self.nfe_slider.reset_btn.config(state=state)
        
        self.temp_slider.configure_slider(state=state)
        self.temp_slider.configure_entry(state=state)
        self.temp_slider.reset_btn.config(state=state)
        
        # Dropdowns and checkboxes
        self.solver_combo.config(state="disabled" if is_processing else "readonly")
        self.denoise_check.config(state=state)
        self.format_combo.config(state="disabled" if is_processing else "readonly")
        self.use_edited_check.config(state=state)
        self.process_btn.config(state=state)
    
    def enable_export(self, enabled: bool = True):
        """Enable/disable the Export button.
        
        Args:
            enabled: True to enable, False to disable
        """
        self.export_btn.config(state="normal" if enabled else "disabled")
