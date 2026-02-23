"""
Input Panel - Voice Cloning Component
Left panel with original audio input and referencing controls
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable, Tuple
import logging

from voice_revolver_ui.components.file_selector import FileSelector
from voice_revolver_ui.components.labeled_slider import LabeledSlider

logger = logging.getLogger(__name__)


class InputPanel(ttk.Frame):
    """Input panel for voice cloning controls"""
    
    # Default RVC parameters
    DEFAULT_RVC_PARAMS = {
        'f0_method': 'rmvpe',
        'pitch_shift': 0,
        'index_rate': 0.75,
        'protection': 0.33,
        'filter_radius': 3,
        'rms_mix_rate': 0.25
    }
    
    def __init__(
        self,
        parent,
        on_process: Optional[Callable] = None,
        on_export: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize input panel.
        
        Args:
            parent: Parent widget
            on_process: Callback when Start Processing clicked
            on_export: Callback when Export clicked
        """
        super().__init__(parent, **kwargs)
        
        self.on_process_callback = on_process
        self.on_export_callback = on_export
        
        # Control variables
        self.reference_mode_var = tk.StringVar(value="audio")  # "audio" or "rvc"
        self.output_format_var = tk.StringVar(value="wav")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create UI components"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        
        row = 0
        
        # === Original Voice Section ===
        original_frame = ttk.LabelFrame(self, text="Original Voice", padding=10)
        original_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        original_frame.columnconfigure(0, weight=1)
        
        self.original_selector = FileSelector(
            original_frame,
            label="Select a File:",
            mode="file",
            file_types=(
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg"),
                ("All Files", "*.*")
            ),
            entry_width=35
        )
        self.original_selector.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        row += 1
        
        # === Referencing Section ===
        ref_frame = ttk.LabelFrame(self, text="Referencing", padding=10)
        ref_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        ref_frame.columnconfigure(0, weight=1)
        
        ref_row = 0
        
        # Reference File selector
        self.reference_selector = FileSelector(
            ref_frame,
            label="Reference File:",
            mode="file",
            file_types=(
                ("Audio Files", "*.wav *.mp3 *.flac"),
                ("All Files", "*.*")
            ),
            entry_width=35
        )
        self.reference_selector.grid(row=ref_row, column=0, sticky=(tk.W, tk.E), pady=5)
        ref_row += 1
        
        # Reference Type radio buttons
        type_label = ttk.Label(ref_frame, text="Reference Type:")
        type_label.grid(row=ref_row, column=0, sticky=tk.W, pady=(10, 5))
        ref_row += 1
        
        radio_frame = ttk.Frame(ref_frame)
        radio_frame.grid(row=ref_row, column=0, sticky=tk.W, padx=(10, 0))
        
        self.audio_radio = ttk.Radiobutton(
            radio_frame,
            text="Audio File",
            variable=self.reference_mode_var,
            value="audio",
            command=self._on_reference_mode_changed
        )
        self.audio_radio.pack(side=tk.LEFT, padx=(0, 20))
        
        self.rvc_radio = ttk.Radiobutton(
            radio_frame,
            text="RVC Model",
            variable=self.reference_mode_var,
            value="rvc",
            command=self._on_reference_mode_changed
        )
        self.rvc_radio.pack(side=tk.LEFT)
        
        ref_row += 1
        
        # RVC Parameters (shown only when RVC mode selected)
        self.rvc_params_frame = ttk.LabelFrame(ref_frame, text="RVC Parameters", padding=10)
        self.rvc_params_frame.grid(row=ref_row, column=0, sticky=(tk.W, tk.E), pady=(10, 5))
        self.rvc_params_frame.columnconfigure(0, weight=1)
        self.rvc_params_frame.grid_remove()  # Hidden by default
        ref_row += 1
        
        param_row = 0
        
        # F0 Method dropdown
        f0_frame = ttk.Frame(self.rvc_params_frame)
        f0_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        f0_frame.columnconfigure(1, weight=1)
        
        ttk.Label(f0_frame, text="F0 Method:", width=15).grid(row=0, column=0, sticky=tk.W)
        self.f0_method_var = tk.StringVar(value=self.DEFAULT_RVC_PARAMS['f0_method'])
        self.f0_method_combo = ttk.Combobox(
            f0_frame,
            textvariable=self.f0_method_var,
            values=["rmvpe", "harvest", "crepe", "pm"],
            state="readonly",
            width=12
        )
        self.f0_method_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        param_row += 1
        
        # F0 Method description
        f0_desc = ttk.Label(
            self.rvc_params_frame,
            text="Pitch extraction algorithm (rmvpe=best quality, harvest=stable, crepe=accurate)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        f0_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Pitch Shift slider
        self.pitch_shift_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Pitch Shift:",
            from_=-12,
            to=12,
            initial_value=self.DEFAULT_RVC_PARAMS['pitch_shift'],
            value_format="{:.0f}",
            length=200
        )
        self.pitch_shift_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Pitch Shift description
        pitch_desc = ttk.Label(
            self.rvc_params_frame,
            text="Shift pitch up/down in semitones (-12 to +12)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        pitch_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Index Rate slider
        self.index_rate_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Index Rate:",
            from_=0.0,
            to=1.0,
            initial_value=self.DEFAULT_RVC_PARAMS['index_rate'],
            value_format="{:.2f}",
            length=200
        )
        self.index_rate_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Index Rate description
        index_desc = ttk.Label(
            self.rvc_params_frame,
            text="Feature retrieval strength (higher=better timbre match, 0.75 recommended)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        index_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Protection slider
        self.protection_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Protection:",
            from_=0.0,
            to=0.5,
            initial_value=self.DEFAULT_RVC_PARAMS['protection'],
            value_format="{:.2f}",
            length=200
        )
        self.protection_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Protection description
        protection_desc = ttk.Label(
            self.rvc_params_frame,
            text="Protect voiceless consonants (s, t, k sounds - prevents over-smoothing)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        protection_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Filter Radius slider
        self.filter_radius_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Filter Radius:",
            from_=0,
            to=7,
            initial_value=self.DEFAULT_RVC_PARAMS['filter_radius'],
            value_format="{:.0f}",
            length=200
        )
        self.filter_radius_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Filter Radius description
        filter_desc = ttk.Label(
            self.rvc_params_frame,
            text="Median filtering for pitch curve (higher=smoother pitch, less vibrato)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        filter_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # RMS Mix Rate slider
        self.rms_mix_slider = LabeledSlider(
            self.rvc_params_frame,
            label="RMS Mix Rate:",
            from_=0.0,
            to=1.0,
            initial_value=self.DEFAULT_RVC_PARAMS['rms_mix_rate'],
            value_format="{:.2f}",
            length=200
        )
        self.rms_mix_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # RMS Mix Rate description
        rms_desc = ttk.Label(
            self.rvc_params_frame,
            text="Volume envelope mixing (0=converted only, 1=source only, 0.25=balanced)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        rms_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Button frame for Start Processing and Reset All buttons
        params_button_frame = ttk.Frame(self.rvc_params_frame)
        params_button_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=(10, 5))
        params_button_frame.columnconfigure(0, weight=1)
        params_button_frame.columnconfigure(1, weight=1)
        
        # Start Processing button (left)
        self.process_btn = ttk.Button(
            params_button_frame,
            text="Start Processing",
            command=self._on_process_clicked,
            style='Accent.TButton'
        )
        self.process_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        # Reset All button (right)
        self.reset_all_btn = ttk.Button(
            params_button_frame,
            text="Reset All to Defaults",
            command=self._reset_rvc_params
        )
        self.reset_all_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
        param_row += 1
        
        # Separator
        ttk.Separator(ref_frame, orient=tk.HORIZONTAL).grid(
            row=ref_row, column=0, sticky=(tk.W, tk.E), pady=10
        )
        ref_row += 1
        
        # Output Format
        format_frame = ttk.Frame(ref_frame)
        format_frame.grid(row=ref_row, column=0, sticky=(tk.W, tk.E), pady=5)
        format_frame.columnconfigure(1, weight=1)
        
        ttk.Label(format_frame, text="Output Format:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.format_combo = ttk.Combobox(
            format_frame,
            textvariable=self.output_format_var,
            values=["wav", "mp3", "flac", "ogg"],
            state="readonly",
            width=15
        )
        self.format_combo.grid(row=0, column=1, sticky=tk.W)
        ref_row += 1
        
        # Use edited version checkbox
        self.use_edited_var = tk.BooleanVar(value=False)  # Default: use processed version
        self.use_edited_check = ttk.Checkbutton(
            ref_frame,
            text="Use edited version",
            variable=self.use_edited_var
        )
        self.use_edited_check.grid(row=ref_row, column=0, sticky=tk.W, pady=(5, 0))
        ref_row += 1
        
        # Export Button
        self.export_btn = ttk.Button(
            ref_frame,
            text="Export",
            command=self._on_export_clicked,
            state='disabled'
        )
        self.export_btn.grid(row=ref_row, column=0, sticky=(tk.W, tk.E), pady=(15, 5))
        
        row += 1
    
    def _on_reference_mode_changed(self):
        """Handle reference mode radio button change"""
        mode = self.reference_mode_var.get()
        if mode == "rvc":
            # Show RVC parameters panel
            self.rvc_params_frame.grid()
            # Update file selector to only accept .zip files
            self.reference_selector.set_file_types((
                ("RVC Models", "*.zip"),
                ("All Files", "*.*")
            ))
        else:
            # Hide RVC parameters panel
            self.rvc_params_frame.grid_remove()
            # Update file selector to only accept audio files
            self.reference_selector.set_file_types((
                ("Audio Files", "*.wav *.mp3 *.flac"),
                ("All Files", "*.*")
            ))
    
    def _reset_rvc_params(self):
        """Reset all RVC parameters to defaults"""
        self.f0_method_var.set(self.DEFAULT_RVC_PARAMS['f0_method'])
        self.pitch_shift_slider.reset()
        self.index_rate_slider.reset()
        self.protection_slider.reset()
        self.filter_radius_slider.reset()
        self.rms_mix_slider.reset()
    
    def _on_process_clicked(self):
        """Handle Start Processing button click"""
        if self.on_process_callback:
            self.on_process_callback()
    
    def _on_export_clicked(self):
        """Handle Export button click"""
        if self.on_export_callback:
            self.on_export_callback()
    
    def get_original_audio(self) -> Optional[Path]:
        """Get original audio file path"""
        path_str = self.original_selector.get()
        if path_str:
            return Path(path_str)
        return None
    
    def get_reference_file(self) -> Optional[Path]:
        """Get reference file path (audio or RVC model)"""
        path_str = self.reference_selector.get()
        if path_str:
            return Path(path_str)
        return None
    
    def get_reference_mode(self) -> str:
        """Get reference mode ('audio' or 'rvc')"""
        return self.reference_mode_var.get()
    
    def get_output_format(self) -> str:
        """Get selected output format"""
        return self.output_format_var.get()
    
    def get_use_edited(self) -> bool:
        """Get whether to use edited version for export"""
        return self.use_edited_var.get()
    
    def get_rvc_params(self) -> dict:
        """Get RVC parameters as dictionary"""
        return {
            'f0_method': self.f0_method_var.get(),
            'f0_up_key': int(self.pitch_shift_slider.get()),
            'index_rate': float(self.index_rate_slider.get()),
            'protect': float(self.protection_slider.get()),
            'filter_radius': int(self.filter_radius_slider.get()),
            'rms_mix_rate': float(self.rms_mix_slider.get()),
            'resample_sr': 0  # Auto-detect from model
        }
    
    def validate(self) -> Tuple[bool, str]:
        """
        Validate inputs before processing.
        
        Returns:
            (is_valid, error_message)
        """
        # Check original audio
        original = self.get_original_audio()
        if not original:
            return False, "Please select an original audio file"
        
        if not original.exists():
            return False, f"Original audio file not found: {original}"
        
        # Check reference file
        reference = self.get_reference_file()
        if not reference:
            return False, "Please select a reference file (audio or RVC model)"
        
        if not reference.exists():
            return False, f"Reference file not found: {reference}"
        
        # Validate file types based on mode
        mode = self.get_reference_mode()
        if mode == "audio":
            # Check audio extension
            valid_audio_exts = {'.wav', '.mp3', '.flac', '.ogg'}
            if reference.suffix.lower() not in valid_audio_exts:
                return False, f"Reference file must be an audio file (WAV, MP3, FLAC, OGG)"
        elif mode == "rvc":
            # Check RVC model extension
            if reference.suffix.lower() != '.zip':
                return False, "RVC model file must be a .zip file"
        
        return True, ""
    
    def set_enabled(self, enabled: bool):
        """Enable/disable all controls"""
        state = 'normal' if enabled else 'disabled'
        readonly_state = 'readonly' if enabled else 'disabled'
        
        self.original_selector.set_enabled(enabled)
        self.reference_selector.set_enabled(enabled)
        
        self.audio_radio.config(state=state)
        self.rvc_radio.config(state=state)
        
        # RVC parameters
        self.f0_method_combo.config(state=readonly_state)
        self.pitch_shift_slider.slider.config(state=state)
        self.pitch_shift_slider.value_entry.config(state=state)
        self.pitch_shift_slider.reset_btn.config(state=state)
        
        self.index_rate_slider.slider.config(state=state)
        self.index_rate_slider.value_entry.config(state=state)
        self.index_rate_slider.reset_btn.config(state=state)
        
        self.protection_slider.slider.config(state=state)
        self.protection_slider.value_entry.config(state=state)
        self.protection_slider.reset_btn.config(state=state)
        
        self.filter_radius_slider.slider.config(state=state)
        self.filter_radius_slider.value_entry.config(state=state)
        self.filter_radius_slider.reset_btn.config(state=state)
        
        self.rms_mix_slider.slider.config(state=state)
        self.rms_mix_slider.value_entry.config(state=state)
        self.rms_mix_slider.reset_btn.config(state=state)
        
        self.reset_all_btn.config(state=state)
        
        self.format_combo.config(state=readonly_state)
        self.process_btn.config(state=state)
    
    def enable_export(self, enabled: bool):
        """Enable/disable export button"""
        self.export_btn.config(state='normal' if enabled else 'disabled')
