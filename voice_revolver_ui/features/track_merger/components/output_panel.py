"""Output panel for Track Merger workspace - SpectrumEditor for merged preview."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import logging

from voice_revolver_ui.features.vocal_changer.spectrum_editor import SpectrumEditor

logger = logging.getLogger(__name__)


class OutputPanel(ttk.Frame):
    """Right panel with spectrum editor for merged audio visualization and curve editing."""
    
    def __init__(
        self,
        parent: ttk.Frame,
        apply_changes_callback: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize the output panel.
        
        Args:
            parent: Parent widget
            apply_changes_callback: Callback when Apply Changes is clicked
        """
        super().__init__(parent, padding=10, **kwargs)
        
        self.apply_changes_callback = apply_changes_callback
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # Spectrum editor expands
        
        # Spectrum editor (no instrumental mode or blend mode for merged audio)
        self.spectrum_editor = SpectrumEditor(
            self,
            enable_instrumental_mode=False
        )
        self.spectrum_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Set apply changes callback
        if self.apply_changes_callback:
            self.spectrum_editor.apply_changes_callback = self.apply_changes_callback
    
    # ===== Public API =====
    
    def load_audio(self, audio_path: Path):
        """Load merged audio into spectrum editor.
        
        Args:
            audio_path: Path to merged audio file
        """
        try:
            self.spectrum_editor.load_vocals(
                vocal_path=audio_path,
                initial_pitch_shift=0,
                enhanced_vocal_path=None,
                instrumental_path=None
            )
            logger.info(f"Loaded merged audio: {audio_path.name}")
        except Exception as e:
            logger.error(f"Failed to load merged audio: {e}")
            raise
    
    def reload_audio_only(self, audio_path: Path):
        """Reload audio without resetting curves.
        
        Args:
            audio_path: Path to audio file
        """
        try:
            self.spectrum_editor.reload_audio_only(audio_path)
            logger.info(f"Reloaded audio (curves preserved): {audio_path.name}")
        except Exception as e:
            logger.error(f"Failed to reload audio: {e}")
            raise
    
    def release_audio_file(self):
        """Release audio file handles to prevent file locks."""
        if hasattr(self.spectrum_editor, 'release_audio_file'):
            self.spectrum_editor.release_audio_file()
    
    def clear(self):
        """Clear the spectrum editor display."""
        # Reset curves and clear display
        if hasattr(self.spectrum_editor, 'reset_all'):
            self.spectrum_editor.reset_all()
    
    # ===== Curve Access (Direct property pattern) =====
    
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
    
    def get_curves(self):
        """Get all curves from spectrum editor.
        
        Returns:
            Dict with pitch, reverb, volume curves
        """
        return {
            'pitch': self.pitch_curve,
            'reverb': self.reverb_curve,
            'volume': self.volume_curve
        }
