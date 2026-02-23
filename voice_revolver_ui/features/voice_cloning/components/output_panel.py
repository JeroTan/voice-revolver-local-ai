"""
Output Panel - Voice Cloning Component
Right panel with spectrogram display and editing controls
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import logging

from voice_revolver_ui.features.vocal_changer.spectrum_editor import SpectrumEditor

logger = logging.getLogger(__name__)


class OutputPanel(ttk.Frame):
    """Output panel with spectrum editor for voice cloning"""
    
    def __init__(
        self,
        parent,
        apply_changes_callback: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize output panel.
        
        Args:
            parent: Parent widget
            apply_changes_callback: Callback when curves are applied
        """
        super().__init__(parent, **kwargs)
        
        self.apply_changes_callback = apply_changes_callback
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create UI components"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        
        # === Spectrum Editor ===
        # Disable instrumental mode since we're working with vocals only
        self.spectrum_editor = SpectrumEditor(
            self,
            enable_instrumental_mode=False
        )
        self.spectrum_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Set apply changes callback
        if self.apply_changes_callback:
            self.spectrum_editor.apply_changes_callback = self.apply_changes_callback
    
    def load_audio(self, audio_path: Path):
        """
        Load audio into spectrum editor.
        
        Args:
            audio_path: Path to audio file to display
        """
        try:
            # Use load_vocals with minimal parameters for voice cloning
            self.spectrum_editor.load_vocals(
                vocal_path=audio_path,
                initial_pitch_shift=0,
                enhanced_vocal_path=None,
                instrumental_path=None
            )
            logger.info(f"Loaded audio into spectrum editor: {audio_path.name}")
        except Exception as e:
            logger.error(f"Failed to load audio into spectrum editor: {e}")
            raise
    
    def reload_audio_only(self, audio_path: Path):
        """
        Reload audio without resetting curves (used after applying changes).
        
        Args:
            audio_path: Path to updated audio file
        """
        try:
            self.spectrum_editor.reload_audio_only(audio_path)
            logger.info(f"Reloaded audio in spectrum editor: {audio_path.name}")
        except Exception as e:
            logger.error(f"Failed to reload audio: {e}")
            raise
    
    def release_audio_file(self):
        """Release audio file handle (for overwriting)"""
        try:
            self.spectrum_editor.release_audio_file()
        except Exception as e:
            logger.warning(f"Failed to release audio file: {e}")
    
    def get_pitch_curve(self):
        """Get current pitch curve"""
        return self.spectrum_editor.pitch_curve
    
    def get_reverb_curve(self):
        """Get current reverb curve"""
        return self.spectrum_editor.reverb_curve
    
    def get_volume_curve(self):
        """Get current volume curve"""
        return self.spectrum_editor.volume_curve
    
    def set_enabled(self, enabled: bool):
        """
        Enable/disable spectrum editor controls.
        
        Args:
            enabled: True to enable, False to disable
        """
        # Spectrum editor handles its own state management
        # This is a placeholder for future enhancements
        pass
