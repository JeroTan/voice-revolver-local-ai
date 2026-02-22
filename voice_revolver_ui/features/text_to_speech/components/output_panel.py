"""
Output Panel - TTS Component
Spectrogram visualization and export controls
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional, Callable
import logging
import threading

from voice_revolver_ui.features.vocal_changer.spectrum_editor import SpectrumEditor

logger = logging.getLogger(__name__)


class OutputPanel(ttk.Frame):
    """Output panel for TTS results"""
    
    def __init__(
        self,
        parent,
        log_callback: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize output panel.
        
        Args:
            parent: Parent widget
            log_callback: Optional logging callback
        """
        super().__init__(parent, **kwargs)
        
        self.log_callback = log_callback
        
        self.generated_audio_path: Optional[Path] = None
        self.edited_audio_path: Optional[Path] = None  # Preview with pitch/volume changes
        
        self._setup_ui()
    
    def _log(self, message: str):
        """Log message"""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)
    
    def _setup_ui(self):
        """Create UI components"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)  # Spectrogram expands
        
        row = 0
        
        # === Spectrogram Area ===
        spec_frame = ttk.LabelFrame(self, text="Generated Audio", padding=5)
        spec_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        spec_frame.columnconfigure(0, weight=1)
        spec_frame.rowconfigure(0, weight=1)
        
        # Spectrum editor (without instrumental mode for TTS)
        self.spectrum_editor = SpectrumEditor(
            spec_frame,
            enable_instrumental_mode=False  # TTS has no instrumental track
        )
        self.spectrum_editor.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Set apply changes callback for pitch/volume/reverb editing
        self.spectrum_editor.set_apply_changes_callback(self._apply_curve_changes)
        
        row += 1
        
        # === Export Controls ===
        export_frame = ttk.LabelFrame(self, text="Export", padding=10)
        export_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        # Format dropdown
        ttk.Label(export_frame, text="Format:").pack(side=tk.LEFT, padx=5)
        self.format_var = tk.StringVar(value="WAV")
        self.format_combo = ttk.Combobox(
            export_frame,
            textvariable=self.format_var,
            values=["WAV", "MP3", "FLAC"],
            state="readonly",
            width=8
        )
        self.format_combo.pack(side=tk.LEFT, padx=5)
        
        # Use edited version checkbox
        self.use_edited_var = tk.BooleanVar(value=False)  # Default: use original
        self.use_edited_check = ttk.Checkbutton(
            export_frame,
            text="Use edited version",
            variable=self.use_edited_var
        )
        self.use_edited_check.pack(side=tk.LEFT, padx=10)
        
        # Export button
        self.export_btn = ttk.Button(
            export_frame,
            text="Export",
            command=self._on_export_clicked,
            state='disabled'
        )
        self.export_btn.pack(side=tk.LEFT, padx=5)
    
    def _on_export_clicked(self):
        """Export generated audio (original or edited version based on checkbox)"""
        # Determine which version to export based on checkbox
        use_edited = self.use_edited_var.get()
        
        if use_edited and self.edited_audio_path and self.edited_audio_path.exists():
            # User wants edited version and it exists
            export_path = self.edited_audio_path
            version_note = " (with edits)"
        elif use_edited and (not self.edited_audio_path or not self.edited_audio_path.exists()):
            # User wants edited version but it doesn't exist
            messagebox.showwarning(
                "No Edited Version", 
                "No edited version available. Apply curve changes first, or uncheck 'Use edited version'."
            )
            return
        else:
            # User wants original version
            export_path = self.generated_audio_path
            version_note = ""
        
        if not export_path or not export_path.exists():
            messagebox.showwarning("No Audio", "No audio to export")
            return
        
        # Get export format
        format_ext = self.format_var.get().lower()
        
        # Ask user for save location
        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{format_ext}",
            filetypes=[
                (f"{format_ext.upper()} Files", f"*.{format_ext}"),
                ("All Files", "*.*")
            ],
            title="Export Generated Audio"
        )
        
        if not file_path:
            return
        
        try:
            # Convert if needed
            if format_ext == "wav":
                # Direct copy
                import shutil
                shutil.copy2(export_path, file_path)
            else:
                # Convert using pydub
                from pydub import AudioSegment
                audio = AudioSegment.from_wav(str(export_path))
                audio.export(file_path, format=format_ext)
            
            self._log(f"[OK] Exported{version_note} to: {Path(file_path).name}")
            messagebox.showinfo("Export Complete", f"Audio exported successfully:\n{file_path}")
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            messagebox.showerror("Export Failed", f"Failed to export audio:\n{e}")
    
    def load_generated_audio(self, audio_path: Path):
        """Load generated audio into spectrum editor"""
        try:
            self.generated_audio_path = audio_path
            self.edited_audio_path = None  # Reset edited version
            
            # Load into spectrum editor
            self.spectrum_editor.load_vocals(
                vocal_path=audio_path,
                enhanced_vocal_path=None,
                instrumental_path=None
            )
            
            # Enable export button
            self.export_btn.config(state='normal')
            
            self._log("[OK] Generated audio loaded")
            
        except Exception as e:
            logger.error(f"Failed to load audio: {e}")
            self._log(f"[ERROR] Failed to load audio: {e}")
    
    def set_generating(self, generating: bool):
        """Update UI during generation"""
        state = 'disabled' if generating else 'normal'
        
        # Disable export during generation
        self.export_btn.config(state='disabled')
    
    def set_enabled(self, enabled: bool):
        """Enable/disable controls"""
        # Only enable export if we have generated audio
        if enabled and self.generated_audio_path:
            self.export_btn.config(state='normal')
        else:
            self.export_btn.config(state='disabled')
    
    def _apply_curve_changes(self):
        """Apply pitch/volume/reverb curve edits to generated TTS audio"""
        if not self.generated_audio_path or not self.generated_audio_path.exists():
            self._log("[WARNING] No audio available. Generate speech first.")
            return
        
        # Get curves from spectrum editor
        curves = self.spectrum_editor.get_all_curves()
        
        has_any_edits = (curves['pitch'].has_edits() or 
                        curves['reverb'].has_edits() or 
                        curves['volume'].has_edits())
        
        if not has_any_edits:
            self._log("ℹ No curve edits - using original audio")
            # Reload original audio
            self.edited_audio_path = None
            self.spectrum_editor.reload_audio_only(self.generated_audio_path)
            return
        
        # Log what we're applying
        self._log("Applying curve changes to preview...")
        if curves['pitch'].has_edits():
            self._log(f"• Pitch curve: {len(curves['pitch'].control_points)} points")
        if curves['reverb'].has_edits():
            self._log(f"• Reverb curve: {len(curves['reverb'].control_points)} points")
        if curves['volume'].has_edits():
            self._log(f"• Volume curve: {len(curves['volume'].control_points)} points")
        
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
            
            # Create temp directory for processed preview
            preview_dir = self.generated_audio_path.parent / "preview"
            preview_dir.mkdir(exist_ok=True, parents=True)
            
            # IMPORTANT: Always start with original generated audio (not the preview/edited version)
            # This ensures each "Apply Changes" starts fresh from the original, preventing quality degradation
            current_audio = self.generated_audio_path
            processor = AudioProcessor()
            
            # Apply pitch curve
            if curves['pitch'].has_edits():
                self.master.after(0, self._log, "→ Applying pitch curve...")
                
                pitch_output = preview_dir / "tts_pitch.wav"
                success = processor.apply_pitch_curve(
                    current_audio,
                    pitch_output,
                    curves['pitch']
                )
                if success and pitch_output.exists():
                    current_audio = pitch_output
                    self.master.after(0, self._log, "  [OK] Pitch curve applied")
                else:
                    raise RuntimeError("Failed to apply pitch curve")
            
            # Apply volume curve
            if curves['volume'].has_edits():
                self.master.after(0, self._log, "→ Applying volume curve...")
                
                volume_output = preview_dir / "tts_volume.wav"
                success = processor.apply_volume_curve(
                    current_audio,
                    volume_output,
                    curves['volume']
                )
                if success and volume_output.exists():
                    current_audio = volume_output
                    self.master.after(0, self._log, "  [OK] Volume curve applied")
                else:
                    raise RuntimeError("Failed to apply volume curve")
            
            # Apply reverb curve
            if curves['reverb'].has_edits():
                self.master.after(0, self._log, "→ Applying reverb curve...")
                
                reverb_output = preview_dir / "tts_reverb.wav"
                success = processor.apply_reverb_curve(
                    current_audio,
                    reverb_output,
                    curves['reverb']
                )
                if success and reverb_output.exists():
                    current_audio = reverb_output
                    self.master.after(0, self._log, "  [OK] Reverb curve applied")
                else:
                    raise RuntimeError("Failed to apply reverb curve")
            
            # Save final preview
            final_preview = preview_dir / "tts_preview.wav"
            if current_audio != final_preview:
                import shutil
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
                            final_preview = preview_dir / f"tts_preview_{int(time.time())}.wav"
                
                shutil.copy(str(current_audio), str(final_preview))
            
            # Update edited audio path and reload into spectrum editor
            self.master.after(0, self._apply_curves_complete, final_preview)
            
        except Exception as e:
            logger.error(f"Failed to apply curve changes: {e}")
            self.master.after(0, self._apply_curves_failed, str(e))
    
    def _apply_curves_complete(self, preview_path: Path):
        """Handle successful curve application"""
        try:
            self.edited_audio_path = preview_path
            
            # Reload the edited audio into spectrum editor (preserves curves for further edits)
            self.spectrum_editor.reload_audio_only(preview_path)
            
            self._log("[OK] Curve changes applied successfully")
            self._log("ℹ Edited version available - check 'Use edited version' to export it")
            
        except Exception as e:
            logger.error(f"Failed to reload preview: {e}")
            self._log(f"[ERROR] Failed to reload preview: {e}")
        finally:
            # Re-enable UI
            self.spectrum_editor.set_enabled(True)
            self.export_btn.config(state='normal')
    
    def _apply_curves_failed(self, error_message: str):
        """Handle curve application failure"""
        self._log(f"[ERROR] Failed to apply curves: {error_message}")
        messagebox.showerror("Apply Changes Failed", f"Failed to apply curve changes:\n{error_message}")
        
        # Re-enable UI
        self.spectrum_editor.set_enabled(True)
        if self.generated_audio_path and self.generated_audio_path.exists():
            self.export_btn.config(state='normal')
