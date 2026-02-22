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
import threading

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
        self.edited_audio_path: Optional[Path] = None  # Preview with pitch/volume changes
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
        
        # Set apply changes callback for pitch/volume/reverb editing
        self.spectrum_editor.set_apply_changes_callback(self._apply_curve_changes)
        
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
        self.edited_audio_path = None  # Reset edited version
        
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
        
        # Use edited audio if available, otherwise use original
        export_source = self.edited_audio_path if self.edited_audio_path and self.edited_audio_path.exists() else self.audio_path
        has_edits = self.edited_audio_path is not None and self.edited_audio_path.exists()
        
        # Ask user for save location
        file_types = (
            ("WAV Audio", "*.wav"),
            ("MP3 Audio", "*.mp3"),
            ("FLAC Audio", "*.flac"),
            ("All Files", "*.*")
        )
        
        edited_suffix = "_edited" if has_edits else ""
        default_name = f"{self.track_name}{edited_suffix}.wav"
        
        save_path = filedialog.asksaveasfilename(
            title=f"Export {self.track_name.capitalize()} Track",
            defaultextension=".wav",
            filetypes=file_types,
            initialfile=default_name
        )
        
        if not save_path:
            return  # User cancelled
        
        save_path = Path(save_path)
        
        try:
            # Convert format if needed
            if save_path.suffix.lower() != '.wav':
                logger.info(f"Converting to {save_path.suffix}...")
                from pydub import AudioSegment
                audio = AudioSegment.from_file(str(export_source))
                
                export_params = {'format': save_path.suffix.lstrip('.')}
                if save_path.suffix.lower() == '.mp3':
                    export_params['bitrate'] = '320k'
                
                audio.export(str(save_path), **export_params)
            else:
                # Just copy the WAV file
                shutil.copy2(str(export_source), str(save_path))
            
            edits_note = " (with edits)" if has_edits else ""
            logger.info(f"[SUCCESS] Track exported{edits_note}: {save_path}")
            
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
    
    def _apply_curve_changes(self):
        """Apply pitch/volume/reverb curve edits to the track audio"""
        if not self.audio_path or not self.audio_path.exists():
            logger.warning(f"No audio available for track {self.track_number}. Load audio first.")
            return
        
        # Get curves from spectrum editor
        curves = self.spectrum_editor.get_all_curves()
        
        has_any_edits = (curves['pitch'].has_edits() or 
                        curves['reverb'].has_edits() or 
                        curves['volume'].has_edits())
        
        if not has_any_edits:
            logger.info(f"No curve edits for {self.track_name} - using original audio")
            # Reload original audio
            self.edited_audio_path = None
            self.spectrum_editor.reload_audio_only(self.audio_path)
            return
        
        # Log what we're applying
        logger.info(f"Applying curve changes to {self.track_name}...")
        if curves['pitch'].has_edits():
            logger.info(f"  • Pitch curve: {len(curves['pitch'].control_points)} points")
        if curves['reverb'].has_edits():
            logger.info(f"  • Reverb curve: {len(curves['reverb'].control_points)} points")
        if curves['volume'].has_edits():
            logger.info(f"  • Volume curve: {len(curves['volume'].control_points)} points")
        
        # Disable UI during processing
        self.spectrum_editor.set_enabled(False)
        self.export_btn.config(state='disabled')
        
        # Release audio file handle before processing
        self.spectrum_editor.release_audio_file()
        
        # Run in background thread
        threading.Thread(target=self._apply_curves_worker, args=(curves,), daemon=False).start()
    
    def _apply_curves_worker(self, curves):
        """Background worker to apply curves"""
        try:
            from voice_revolver_core.infrastructure.audio_processor import AudioProcessor
            from voice_revolver_core.domain.file_manager import FileManager
            
            # Create temp directory for processed preview
            app_data = Path.home() / ".voice_revolver"
            file_manager = FileManager(app_data)
            preview_dir = file_manager.get_workspace_temp_dir("audio_separation") / f"preview_{self.track_name}"
            preview_dir.mkdir(exist_ok=True, parents=True)
            
            # IMPORTANT: Always start with original audio (not the preview/edited version)
            # This ensures each "Apply Changes" starts fresh from the original, preventing quality degradation
            current_audio = self.audio_path
            processor = AudioProcessor()
            
            # Apply pitch curve
            if curves['pitch'].has_edits():
                logger.info(f"  → Applying pitch curve to {self.track_name}...")
                
                pitch_output = preview_dir / f"{self.track_name}_pitch.wav"
                success = processor.apply_pitch_curve(
                    current_audio,
                    pitch_output,
                    curves['pitch']
                )
                if success and pitch_output.exists():
                    current_audio = pitch_output
                    logger.info(f"    [OK] Pitch curve applied")
                else:
                    raise RuntimeError("Failed to apply pitch curve")
            
            # Apply volume curve
            if curves['volume'].has_edits():
                logger.info(f"  → Applying volume curve to {self.track_name}...")
                
                volume_output = preview_dir / f"{self.track_name}_volume.wav"
                success = processor.apply_volume_curve(
                    current_audio,
                    volume_output,
                    curves['volume']
                )
                if success and volume_output.exists():
                    current_audio = volume_output
                    logger.info(f"    [OK] Volume curve applied")
                else:
                    raise RuntimeError("Failed to apply volume curve")
            
            # Apply reverb curve
            if curves['reverb'].has_edits():
                logger.info(f"  → Applying reverb curve to {self.track_name}...")
                
                reverb_output = preview_dir / f"{self.track_name}_reverb.wav"
                success = processor.apply_reverb_curve(
                    current_audio,
                    reverb_output,
                    curves['reverb']
                )
                if success and reverb_output.exists():
                    current_audio = reverb_output
                    logger.info(f"    [OK] Reverb curve applied")
                else:
                    raise RuntimeError("Failed to apply reverb curve")
            
            # Save final preview
            final_preview = preview_dir / f"{self.track_name}_preview.wav"
            if current_audio != final_preview:
                import time
                
                # Delete old preview if exists
                if final_preview.exists():
                    try:
                        final_preview.unlink()
                    except PermissionError:
                        time.sleep(0.1)
                        try:
                            final_preview.unlink()
                        except:
                            final_preview = preview_dir / f"{self.track_name}_preview_{int(time.time())}.wav"
                
                shutil.copy(str(current_audio), str(final_preview))
            
            # Update edited audio path and reload into spectrum editor
            self.master.after(0, self._apply_curves_complete, final_preview)
            
        except Exception as e:
            logger.error(f"Failed to apply curve changes to {self.track_name}: {e}")
            self.master.after(0, self._apply_curves_failed, str(e))
    
    def _apply_curves_complete(self, preview_path: Path):
        """Handle successful curve application"""
        try:
            self.edited_audio_path = preview_path
            
            # Reload the edited audio into spectrum editor (preserves curves for further edits)
            self.spectrum_editor.reload_audio_only(preview_path)
            
            logger.info(f"[OK] Curve changes applied successfully to {self.track_name}")
            
        except Exception as e:
            logger.error(f"Failed to reload preview for {self.track_name}: {e}")
        finally:
            # Re-enable UI
            self.spectrum_editor.set_enabled(True)
            if self.export_enabled:
                self.export_btn.config(state='normal')
    
    def _apply_curves_failed(self, error_message: str):
        """Handle curve application failure"""
        logger.error(f"[ERROR] Failed to apply curves to {self.track_name}: {error_message}")
        
        from tkinter import messagebox
        messagebox.showerror(
            "Apply Changes Failed", 
            f"Failed to apply curve changes to {self.track_name}:\n{error_message}"
        )
        
        # Re-enable UI
        self.spectrum_editor.set_enabled(True)
        if self.audio_path and self.audio_path.exists() and self.export_enabled:
            self.export_btn.config(state='normal')
    
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
