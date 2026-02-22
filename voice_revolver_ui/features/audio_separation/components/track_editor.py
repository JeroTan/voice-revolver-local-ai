"""
Track Editor Component - Audio Separation Workspace
Individual track UI with spectrum editor and controls
"""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import Optional, Dict
import logging
import shutil

from voice_revolver_ui.features.vocal_changer.spectrum_editor import SpectrumEditor

logger = logging.getLogger(__name__)


class TrackEditor(ttk.Frame):
    """
    Individual track editor component.
    
    Features:
    - Track header with play/stop/export controls
    - SpectrumEditor for visual editing
    - Track name and number display
    """
    
    def __init__(
        self,
        parent,
        track_number: int,
        track_name: str,
        **kwargs
    ):
        """
        Initialize track editor.
        
        Args:
            parent: Parent tkinter widget
            track_number: Track number (1-indexed for display)
            track_name: Track name (vocals, drums, bass, other)
            **kwargs: Additional configuration for the Frame
        """
        super().__init__(parent, **kwargs)
        
        self.track_number = track_number
        self.track_name = track_name
        self.audio_path: Optional[Path] = None
        self.export_enabled = False
        
        # Configure frame
        self.configure(relief=tk.RIDGE, borderwidth=2, padding="5")
        
        # UI setup
        self._setup_ui()
        
    def _setup_ui(self):
        """Create and layout child widgets."""
        # Header frame
        header_frame = ttk.Frame(self)
        header_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Track identification
        track_id_frame = ttk.Frame(header_frame)
        track_id_frame.pack(side=tk.LEFT)
        
        track_label = ttk.Label(
            track_id_frame,
            text=f"[{self.track_number}] {self.track_name.capitalize()}",
            font=("Segoe UI", 10, "bold")
        )
        track_label.pack(side=tk.LEFT)
        
        # Playback controls
        control_frame = ttk.Frame(header_frame)
        control_frame.pack(side=tk.RIGHT)
        
        self.play_btn = ttk.Button(
            control_frame,
            text="Play",
            width=8,
            state='disabled',
            command=self._on_play
        )
        self.play_btn.pack(side=tk.LEFT, padx=2)
        
        self.stop_btn = ttk.Button(
            control_frame,
            text="Stop",
            width=8,
            state='disabled',
            command=self._on_stop
        )
        self.stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.export_btn = ttk.Button(
            control_frame,
            text="Export",
            width=10,
            state='disabled',
            command=self._on_export
        )
        self.export_btn.pack(side=tk.LEFT, padx=2)
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # Spectrum editor
        self.spectrum_editor = SpectrumEditor(self)
        self.spectrum_editor.pack(fill=tk.BOTH, expand=True)
        
    def load_audio(self, audio_path: Path, enhanced_vocal_path: Optional[Path] = None):
        """
        Load audio into track editor.
        
        Args:
            audio_path: Path to audio file
            enhanced_vocal_path: Optional path to enhanced vocals for blend mode
        """
        if not audio_path or not audio_path.exists():
            logger.error(f"Cannot load audio, invalid path: {audio_path}")
            return
        
        self.audio_path = audio_path
        
        # Load into spectrum editor (pass enhanced vocals if available)
        self.spectrum_editor.load_vocals(
            vocal_path=audio_path,
            initial_pitch_shift=0,
            enhanced_vocal_path=enhanced_vocal_path,
            instrumental_path=None
        )
        
        # Enable controls
        self.play_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        
        logger.info(f"Loaded audio for track {self.track_number} ({self.track_name})")
    
    def _on_play(self):
        """Handle play button click."""
        # Delegate to spectrum editor's play functionality
        if hasattr(self.spectrum_editor, '_toggle_play_pause'):
            self.spectrum_editor._toggle_play_pause()
    
    def _on_stop(self):
        """Handle stop button click."""
        # Delegate to spectrum editor's stop functionality
        if hasattr(self.spectrum_editor, '_stop_audio'):
            self.spectrum_editor._stop_audio()
    
    def _on_export(self):
        """Handle export button click."""
        if not self.audio_path:
            logger.warning(f"Cannot export track {self.track_number}: no audio loaded")
            return
        
        # Ask user for save location
        file_types = (
            ("WAV Audio", "*.wav"),
            ("MP3 Audio", "*.mp3"),
            ("FLAC Audio", "*.flac"),
            ("All Files", "*.*")
        )
        
        default_name = f"{self.track_name}_edited.wav"
        
        save_path = filedialog.asksaveasfilename(
            title=f"Export {self.track_name.capitalize()} Track",
            defaultextension=".wav",
            filetypes=file_types,
            initialfile=default_name
        )
        
        if not save_path:
            return  # User cancelled
        
        save_path = Path(save_path)
        
        # Get curves from spectrum editor
        curves = self.get_curves()
        
        # Import required modules
        from voice_revolver_core.infrastructure.audio_processor import AudioProcessor
        from voice_revolver_core.domain.file_manager import FileManager
        
        try:
            # FIXED: Create temp directory for processing with proper app_data_path
            app_data = Path.home() / ".voice_revolver"
            file_manager = FileManager(app_data)
            temp_dir = file_manager.get_workspace_temp_dir("audio_separation")
            temp_file = temp_dir / f"temp_{self.track_name}.wav"
            temp_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Start with original audio
            current_file = self.audio_path
            
            # Apply curves sequentially
            processor = AudioProcessor()
            
            # Apply pitch curve
            if curves['pitch'] and curves['pitch'].has_edits():
                logger.info(f"Applying pitch curve to {self.track_name}...")
                temp_pitch = temp_dir / f"temp_{self.track_name}_pitch.wav"
                if processor.apply_pitch_curve(current_file, temp_pitch, curves['pitch']):
                    current_file = temp_pitch
                else:
                    logger.error("Failed to apply pitch curve")
            
            # Apply volume curve
            if curves['volume'] and curves['volume'].has_edits():
                logger.info(f"Applying volume curve to {self.track_name}...")
                temp_volume = temp_dir / f"temp_{self.track_name}_volume.wav"
                if processor.apply_volume_curve(current_file, temp_volume, curves['volume']):
                    current_file = temp_volume
                else:
                    logger.error("Failed to apply volume curve")
            
            # Apply reverb curve
            if curves['reverb'] and curves['reverb'].has_edits():
                logger.info(f"Applying reverb curve to {self.track_name}...")
                temp_reverb = temp_dir / f"temp_{self.track_name}_reverb.wav"
                if processor.apply_reverb_curve(current_file, temp_reverb, curves['reverb']):
                    current_file = temp_reverb
                else:
                    logger.error("Failed to apply reverb curve")
            
            # Apply noise reduction curve if present
            if curves.get('noise') and curves['noise'].has_edits():
                logger.info(f"Applying noise reduction curve to {self.track_name}...")
                temp_noise = temp_dir / f"temp_{self.track_name}_noise.wav"
                if hasattr(processor, 'apply_noise_curve') and processor.apply_noise_curve(current_file, temp_noise, curves['noise']):
                    current_file = temp_noise
                else:
                    logger.warning("Noise reduction curve not applied (may not be implemented)")
            
            # Convert format if needed
            if save_path.suffix.lower() != '.wav':
                logger.info(f"Converting to {save_path.suffix}...")
                from pydub import AudioSegment
                audio = AudioSegment.from_file(str(current_file))
                
                export_params = {'format': save_path.suffix.lstrip('.')}
                if save_path.suffix.lower() == '.mp3':
                    export_params['bitrate'] = '320k'
                
                audio.export(str(save_path), **export_params)
            else:
                # Just copy the WAV file
                shutil.copy2(str(current_file), str(save_path))
            
            logger.info(f"[SUCCESS] Track exported: {save_path}")
            
            # Show success message
            from tkinter import messagebox
            messagebox.showinfo(
                "Export Successful",
                f"{self.track_name.capitalize()} track exported to:\n{save_path}"
            )
            
        except Exception as e:
            logger.error(f"Export failed for {self.track_name}: {e}", exc_info=True)
            from tkinter import messagebox
            messagebox.showerror(
                "Export Failed",
                f"Failed to export {self.track_name} track:\n{str(e)}"
            )
    
    def get_curves(self) -> Dict:
        """
        Get all editing curves from spectrum editor.
        
        Returns:
            Dictionary with curve objects: {pitch, volume, reverb, noise}
        """
        return {
            'pitch': self.spectrum_editor.pitch_curve,
            'volume': self.spectrum_editor.volume_curve,
            'reverb': self.spectrum_editor.reverb_curve,
            'noise': self.spectrum_editor.noise_curve,
        }
    
    def enable_export(self):
        """Enable export button after edits are complete."""
        self.export_enabled = True
        self.export_btn.config(state='normal')
