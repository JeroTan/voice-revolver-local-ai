"""Track Merger workspace - Main workspace for merging multiple audio tracks."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, Callable
import threading
import logging
import shutil
import math

from voice_revolver_core.domain.file_manager import FileManager
from voice_revolver_core.infrastructure.audio_processor import AudioProcessor

from .components import InputPanel, OutputPanel

logger = logging.getLogger(__name__)


class TrackMergerWorkspace(ttk.Frame):
    """Main workspace for merging multiple audio tracks into one."""
    
    def __init__(
        self,
        parent,
        root,
        app_data_path: Path,
        device: str,
        log_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """Initialize the Track Merger workspace.
        
        Args:
            parent: Parent widget
            root: Tk root window
            app_data_path: Path to application data directory
            device: Compute device (cuda/cpu)
            log_callback: Optional callback for logging messages
        """
        super().__init__(parent, **kwargs)
        
        self.root = root
        self.app_data_path = app_data_path
        self.device = device
        self.log_callback = log_callback
        
        # File management
        self.file_manager = FileManager(app_data_path)
        self.audio_processor = AudioProcessor()
        
        # Audio state
        self.merged_audio_path: Optional[Path] = None
        self.edited_audio_path: Optional[Path] = None
        
        # Processing state
        self.is_processing = False
        
        # UI state
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="Ready")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the workspace UI."""
        # Configure grid - two columns (50/50 split)
        # Use uniform="equal" to force truly equal column widths
        # minsize ensures tools panel doesn't get cut off
        self.columnconfigure(0, weight=1, uniform="equal", minsize=300)  # Input panel (50%)
        self.columnconfigure(1, weight=1, uniform="equal", minsize=400)  # Output panel (50%) - min for tools
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)  # Progress bar
        
        # Input panel (left)
        self.input_panel = InputPanel(
            self,
            on_merge=self._on_merge_clicked,
            on_export=self._on_export_clicked
        )
        self.input_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Output panel (right)
        self.output_panel = OutputPanel(
            self,
            apply_changes_callback=self._apply_curve_changes
        )
        self.output_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        # Progress bar (bottom, full width)
        progress_frame = ttk.Frame(self, padding=(0, 10, 0, 0))
        progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        progress_frame.columnconfigure(0, weight=1)
        
        # Progress label
        self.progress_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_text_var
        )
        self.progress_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.grid(row=1, column=0, sticky=(tk.W, tk.E))
    
    def _log(self, message: str):
        """Log a message to the UI.
        
        Args:
            message: Message to log
        """
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)
    
    def _update_progress(self, percent: float, message: str):
        """Update progress bar and message.
        
        Args:
            percent: Progress percentage (0-100)
            message: Status message
        """
        self.progress_var.set(percent)
        self.progress_text_var.set(message)
    
    # ===== Merge Workflow =====
    
    def _on_merge_clicked(self):
        """Handle Merge Tracks button click."""
        if self.is_processing:
            return
        
        # Get tracks
        tracks = self.input_panel.get_tracks()
        
        if len(tracks) < 2:
            messagebox.showwarning(
                "Not Enough Tracks",
                "Please add at least 2 tracks to merge."
            )
            return
        
        # Start merge
        self.is_processing = True
        self.input_panel.set_processing(True)
        
        # Release any existing audio
        self.output_panel.release_audio_file()
        
        # Start background thread
        thread = threading.Thread(target=self._merge_worker, args=(tracks,), daemon=True)
        thread.start()
    
    def _merge_worker(self, tracks: list):
        """Background worker for merging tracks.
        
        Args:
            tracks: List of track dicts with file_path and volume
        """
        try:
            from pydub import AudioSegment
            
            temp_dir = self.file_manager.get_workspace_temp_dir("track_merger")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean old temp files
            self.root.after(0, self._update_progress, 5, "Cleaning temp files...")
            for old_file in temp_dir.glob("*.wav"):
                try:
                    old_file.unlink()
                except Exception:
                    pass
            
            total_tracks = len(tracks)
            self.root.after(0, self._log, f"[*] Merging {total_tracks} tracks...")
            
            # Load and process tracks
            base_audio = None
            
            for idx, track in enumerate(tracks):
                progress = 10 + (idx / total_tracks * 70)
                self.root.after(0, self._update_progress, progress, f"Loading track {idx + 1}/{total_tracks}...")
                self.root.after(0, self._log, f"[*] Loading: {track['name']}")
                
                # Load audio
                audio = AudioSegment.from_file(str(track['file_path']))
                
                # Apply volume
                if track['volume'] != 1.0:
                    # Convert multiplier to dB
                    if track['volume'] > 0:
                        gain_db = 20 * math.log10(track['volume'])
                        audio = audio.apply_gain(gain_db)
                        self.root.after(0, self._log, f"    Volume: {int(track['volume'] * 100)}% ({gain_db:+.1f} dB)")
                    else:
                        # Muted track
                        audio = audio.apply_gain(-100)
                        self.root.after(0, self._log, f"    Volume: 0% (muted)")
                
                # First track becomes base
                if base_audio is None:
                    base_audio = audio
                else:
                    # Overlay subsequent tracks
                    # Match lengths by padding shorter one
                    if len(audio) > len(base_audio):
                        # Pad base with silence
                        silence = AudioSegment.silent(duration=len(audio) - len(base_audio))
                        base_audio = base_audio + silence
                    elif len(audio) < len(base_audio):
                        # Pad audio with silence
                        silence = AudioSegment.silent(duration=len(base_audio) - len(audio))
                        audio = audio + silence
                    
                    # Overlay (mix)
                    base_audio = base_audio.overlay(audio)
            
            self.root.after(0, self._update_progress, 85, "Saving merged audio...")
            
            # Normalize to prevent clipping
            if base_audio.max_dBFS > -1.0:
                # Reduce gain to avoid clipping
                reduction = base_audio.max_dBFS + 1.0
                base_audio = base_audio.apply_gain(-reduction)
                self.root.after(0, self._log, f"[*] Normalized by {-reduction:.1f} dB to prevent clipping")
            
            # Export merged audio
            merged_path = temp_dir / "merged.wav"
            base_audio.export(str(merged_path), format="wav")
            
            self.merged_audio_path = merged_path
            self.edited_audio_path = None  # Reset edited version
            
            self.root.after(0, self._log, f"[+] Merged audio saved: {merged_path.name}")
            self.root.after(0, self._merge_complete)
            
        except Exception as e:
            logger.exception("Merge failed")
            self.root.after(0, self._merge_failed, str(e))
    
    def _merge_complete(self):
        """Handle successful merge completion."""
        self._log("[+] Merge complete!")
        self._update_progress(100, "Merge complete")
        
        # Load merged audio into spectrum editor
        self.output_panel.load_audio(self.merged_audio_path)
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        self.input_panel.enable_export(True)
        self.is_processing = False
        
        messagebox.showinfo(
            "Merge Complete",
            f"Successfully merged {len(self.input_panel.get_tracks())} tracks!\n\n"
            "The merged audio is now loaded in the spectrum editor.\n"
            "You can edit curves or export the result."
        )
    
    def _merge_failed(self, error_message: str):
        """Handle merge failure.
        
        Args:
            error_message: Error description
        """
        self._log(f"[!] Merge failed: {error_message}")
        self._update_progress(0, "Merge failed")
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        self.is_processing = False
        
        messagebox.showerror(
            "Merge Failed",
            f"Failed to merge tracks:\n\n{error_message}"
        )
    
    # ===== Apply Curves Workflow =====
    
    def _apply_curve_changes(self):
        """Apply curve edits to merged audio."""
        if not self.merged_audio_path or not self.merged_audio_path.exists():
            messagebox.showwarning(
                "No Merged Audio",
                "Please merge tracks first."
            )
            return
        
        # Release audio before processing
        self.output_panel.release_audio_file()
        
        # Disable controls
        self.input_panel.set_processing(True)
        
        # Start in background thread
        thread = threading.Thread(target=self._apply_curves_worker, daemon=True)
        thread.start()
    
    def _apply_curves_worker(self):
        """Background worker for applying curve edits."""
        try:
            temp_dir = self.file_manager.get_workspace_temp_dir("track_merger")
            
            self.root.after(0, self._update_progress, 10, "Applying curve edits...")
            self.root.after(0, self._log, "[*] Applying curve edits...")
            
            # Get curves
            pitch_curve = self.output_panel.pitch_curve
            reverb_curve = self.output_panel.reverb_curve
            volume_curve = self.output_panel.volume_curve
            
            # ALWAYS start from original merged audio (non-compounding edits)
            current_audio = self.merged_audio_path
            
            # Apply curves sequentially: pitch → volume → reverb
            
            # 1. Pitch curve
            if pitch_curve.has_edits():
                self.root.after(0, self._update_progress, 30, "Applying pitch curve...")
                self.root.after(0, self._log, "[*] Applying pitch curve...")
                pitch_output = temp_dir / "temp_pitch.wav"
                success = self.audio_processor.apply_pitch_curve(
                    current_audio,
                    pitch_output,
                    pitch_curve
                )
                if success and pitch_output.exists():
                    current_audio = pitch_output
                    self.root.after(0, self._log, "[+] Pitch curve applied")
                else:
                    raise RuntimeError("Failed to apply pitch curve")
            
            # 2. Volume curve
            if volume_curve.has_edits():
                self.root.after(0, self._update_progress, 55, "Applying volume curve...")
                self.root.after(0, self._log, "[*] Applying volume curve...")
                volume_output = temp_dir / "temp_volume.wav"
                success = self.audio_processor.apply_volume_curve(
                    current_audio,
                    volume_output,
                    volume_curve
                )
                if success and volume_output.exists():
                    current_audio = volume_output
                    self.root.after(0, self._log, "[+] Volume curve applied")
                else:
                    raise RuntimeError("Failed to apply volume curve")
            
            # 3. Reverb curve
            if reverb_curve.has_edits():
                self.root.after(0, self._update_progress, 80, "Applying reverb curve...")
                self.root.after(0, self._log, "[*] Applying reverb curve...")
                reverb_output = temp_dir / "temp_reverb.wav"
                success = self.audio_processor.apply_reverb_curve(
                    current_audio,
                    reverb_output,
                    reverb_curve
                )
                if success and reverb_output.exists():
                    current_audio = reverb_output
                    self.root.after(0, self._log, "[+] Reverb curve applied")
                else:
                    raise RuntimeError("Failed to apply reverb curve")
            
            # Save final edited version
            edited_path = temp_dir / "merged_edited.wav"
            shutil.copy(str(current_audio), str(edited_path))
            self.edited_audio_path = edited_path
            
            self.root.after(0, self._apply_curves_complete)
            
        except Exception as e:
            logger.exception("Apply curves failed")
            self.root.after(0, self._apply_curves_failed, str(e))
    
    def _apply_curves_complete(self):
        """Handle successful curve application."""
        self._log("[+] Curve edits applied successfully")
        self._update_progress(100, "Curve edits applied")
        
        # Reload edited audio (preserves curves)
        self.output_panel.reload_audio_only(self.edited_audio_path)
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        
        messagebox.showinfo(
            "Changes Applied",
            "Curve edits applied successfully!\n\n"
            "The edited audio is now loaded in the spectrum editor.\n"
            "You can continue editing or export the result."
        )
    
    def _apply_curves_failed(self, error_message: str):
        """Handle curve application failure.
        
        Args:
            error_message: Error description
        """
        self._log(f"[!] Apply curves failed: {error_message}")
        self._update_progress(0, "Apply curves failed")
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        
        messagebox.showerror(
            "Apply Changes Failed",
            f"Failed to apply curve edits:\n\n{error_message}"
        )
    
    # ===== Export Workflow =====
    
    def _on_export_clicked(self):
        """Handle Export button click."""
        # Determine source file
        use_edited = self.input_panel.get_use_edited()
        
        if use_edited:
            if not self.edited_audio_path or not self.edited_audio_path.exists():
                messagebox.showwarning(
                    "No Edited Version",
                    "No edited version available.\n\n"
                    "Apply curve changes first, or uncheck 'Use edited audio'."
                )
                return
            source_path = self.edited_audio_path
        else:
            if not self.merged_audio_path or not self.merged_audio_path.exists():
                messagebox.showwarning(
                    "No Merged Audio",
                    "No merged audio available. Merge tracks first."
                )
                return
            source_path = self.merged_audio_path
        
        # Get output format
        output_format = self.input_panel.get_output_format()
        
        # Open save dialog
        default_name = f"merged_audio.{output_format}"
        file_path = filedialog.asksaveasfilename(
            defaultextension=f".{output_format}",
            filetypes=[
                (f"{output_format.upper()} files", f"*.{output_format}"),
                ("All files", "*.*")
            ],
            initialfile=default_name
        )
        
        if not file_path:
            return  # User cancelled
        
        output_path = Path(file_path)
        
        # Release audio before export
        self.output_panel.release_audio_file()
        
        # Disable controls
        self.input_panel.set_processing(True)
        
        # Start export in background
        thread = threading.Thread(
            target=self._export_worker,
            args=(source_path, output_path, output_format),
            daemon=True
        )
        thread.start()
    
    def _export_worker(self, source_path: Path, output_path: Path, output_format: str):
        """Background worker for exporting audio.
        
        Args:
            source_path: Source audio file path
            output_path: Destination file path
            output_format: Output format (wav, mp3, flac, ogg)
        """
        try:
            from pydub import AudioSegment
            
            self.root.after(0, self._update_progress, 20, "Loading audio...")
            
            # Load audio
            audio = AudioSegment.from_file(str(source_path))
            
            self.root.after(0, self._update_progress, 60, f"Exporting as {output_format.upper()}...")
            
            # Export with appropriate settings
            if output_format == "mp3":
                audio.export(str(output_path), format="mp3", bitrate="320k")
            elif output_format == "flac":
                audio.export(str(output_path), format="flac")
            elif output_format == "ogg":
                audio.export(str(output_path), format="ogg", codec="libvorbis")
            else:  # wav
                audio.export(str(output_path), format="wav")
            
            self.root.after(0, self._export_complete, output_path)
            
        except Exception as e:
            logger.exception("Export failed")
            self.root.after(0, self._export_failed, str(e))
    
    def _export_complete(self, output_path: Path):
        """Handle successful export.
        
        Args:
            output_path: Path where audio was saved
        """
        self._log(f"[+] Export complete: {output_path}")
        self._update_progress(100, "Export complete")
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        
        messagebox.showinfo(
            "Export Complete",
            f"Audio exported successfully to:\n\n{output_path}"
        )
    
    def _export_failed(self, error_message: str):
        """Handle export failure.
        
        Args:
            error_message: Error description
        """
        self._log(f"[!] Export failed: {error_message}")
        self._update_progress(0, "Export failed")
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        
        messagebox.showerror(
            "Export Failed",
            f"Failed to export audio:\n\n{error_message}"
        )
