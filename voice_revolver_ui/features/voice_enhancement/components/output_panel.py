"""Output panel for Voice Enhancement workspace."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable

from voice_revolver_ui.features.vocal_changer.spectrum_editor import SpectrumEditor


class OutputPanel(ttk.Frame):
    """Right panel with spectrum editor for visualization and curve editing."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        apply_changes_callback: Optional[Callable] = None
    ):
        """Initialize the output panel.
        
        Args:
            parent: Parent widget
            apply_changes_callback: Callback when blend curve is applied (for "Apply Changes" button)
        """
        super().__init__(parent, padding=10)
        self.apply_changes_callback = apply_changes_callback
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # Spectrum editor expands
        
        # Spectrum editor (no instrumental mode needed for voice enhancement)
        self.spectrum_editor = SpectrumEditor(
            self,
            enable_instrumental_mode=False
        )
        self.spectrum_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Set apply changes callback for blend mode
        if self.apply_changes_callback:
            self.spectrum_editor.apply_changes_callback = self.apply_changes_callback
    
    # ===== Public API =====
    
    def load_audio(
        self,
        audio_path: Path,
        enhanced_path: Optional[Path] = None
    ):
        """Load audio into spectrum editor.
        
        Args:
            audio_path: Path to original audio file
            enhanced_path: Optional path to enhanced audio (enables blend mode)
        """
        self.spectrum_editor.load_vocals(
            vocal_path=audio_path,
            initial_pitch_shift=0,
            enhanced_vocal_path=enhanced_path,  # Enables blend mode for A/B comparison
            instrumental_path=None
        )
    
    def reload_audio_only(self, audio_path: Path):
        """Reload audio without losing curve edits.
        
        Args:
            audio_path: Path to audio file to reload
        """
        self.spectrum_editor.reload_audio_only(audio_path)
    
    def release_audio_file(self):
        """Release audio file handles to prevent file locks."""
        self.spectrum_editor.release_audio_file()
    
    # ===== Curve Access (Direct attribute access pattern) =====
    
    @property
    def pitch_curve(self):
        """Get pitch curve from spectrum editor."""
        return self.spectrum_editor.pitch_curve
    
    @property
    def reverb_curve(self):
        """Get reverb curve from spectrum editor."""
        return self.spectrum_editor.reverb_curve
    
    @property
    def volume_curve(self):
        """Get volume curve from spectrum editor."""
        return self.spectrum_editor.volume_curve
