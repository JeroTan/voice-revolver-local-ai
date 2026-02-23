"""
Voice Cloning Workspace
Main workspace for voice cloning with dual reference modes (Audio File / RVC Model)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from typing import Optional
import threading
import logging

from voice_revolver_core.infrastructure.chatterbox_vc_wrapper import ChatterBoxVCWrapper
from voice_revolver_core.infrastructure.rvc_wrapper import RVCWrapper
from voice_revolver_core.infrastructure.audio_processor import AudioProcessor
from voice_revolver_core.domain.file_manager import FileManager
from voice_revolver_core.domain.base import PitchCurve, ReverbCurve, VolumeCurve

from .components.input_panel import InputPanel
from .components.output_panel import OutputPanel

logger = logging.getLogger(__name__)


class VoiceCloningWorkspace(ttk.Frame):
    """Voice cloning workspace with audio file and RVC model support"""
    
    def __init__(
        self,
        parent,
        root,
        app_data_path: Path,
        device: str = "cpu",
        log_callback: Optional[callable] = None,
        **kwargs
    ):
        """
        Initialize voice cloning workspace.
        
        Args:
            parent: Parent widget
            root: Root window
            app_data_path: Application data directory
            device: Computation device (cpu/cuda)
            log_callback: Optional logging callback
        """
        super().__init__(parent, **kwargs)
        
        self.root = root
        self.device = device
        self.log_callback = log_callback
        self.file_manager = FileManager(app_data_path)
        
        # Infrastructure wrappers
        self.vc_wrapper = ChatterBoxVCWrapper(device=device)
        self.rvc_wrapper = RVCWrapper(device=device)
        self.audio_processor = AudioProcessor()
        
        # State variables - File workflow:
        # 1. User selects original_audio_path (source vocal)
        # 2. Processing creates processed_audio_path (temp/voice_cloning/processed.wav) - NEVER modified!
        # 3. Curve edits create edited_audio_path (temp/voice_cloning/processed_edited.wav) - overwrites each edit
        # 4. Each edit ALWAYS reads from processed_audio_path to prevent compounding adjustments
        self.processing_thread: Optional[threading.Thread] = None
        self.original_audio_path: Optional[Path] = None  # User's input file
        self.processed_audio_path: Optional[Path] = None  # Generated voice clone (immutable)
        self.edited_audio_path: Optional[Path] = None  # Latest curve-edited version
        
        # Progress tracking
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create UI components"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=2)  # Output panel gets more space
        self.rowconfigure(0, weight=1)
        
        # === Input Panel (Left) ===
        self.input_panel = InputPanel(
            self,
            on_process=self._on_process_clicked,
            on_export=self._on_export_clicked
        )
        self.input_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 2), pady=5)
        
        # === Output Panel (Right) ===
        self.output_panel = OutputPanel(
            self,
            apply_changes_callback=self._apply_curve_changes
        )
        self.output_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(2, 5), pady=5)
        
        # === Progress Bar (Bottom) ===
        progress_frame = ttk.Frame(self)
        progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=(0, 5))
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            variable=self.progress_var,
            length=400
        )
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=2)
        
        self.progress_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_text_var,
            font=("Segoe UI", 9)
        )
        self.progress_label.grid(row=1, column=0, sticky=tk.W)
    
    def _log(self, message: str):
        """Log message to UI callback"""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)
    
    def _update_progress(self, percent: float, message: str):
        """Thread-safe progress update"""
        self.progress_var.set(percent)
        self.progress_text_var.set(message)
    
    def _on_process_clicked(self):
        """Handle Start Processing button click"""
        # Validate inputs
        is_valid, error_msg = self.input_panel.validate()
        if not is_valid:
            messagebox.showerror("Validation Error", error_msg)
            return
        
        # Release any previously loaded audio files to prevent file locks
        # This allows overwriting processed.wav from previous runs
        self.output_panel.release_audio_file()
        
        # Disable UI during processing
        self.input_panel.set_enabled(False)
        self.input_panel.enable_export(False)
        
        # Start processing in background thread
        self.processing_thread = threading.Thread(target=self._process_worker, daemon=True)
        self.processing_thread.start()
    
    def _process_worker(self):
        """Background worker for voice conversion"""
        try:
            # Get inputs
            original_path = self.input_panel.get_original_audio()
            reference_path = self.input_panel.get_reference_file()
            mode = self.input_panel.get_reference_mode()
            
            self.root.after(0, self._log, "[*] Starting voice cloning process...")
            self.root.after(0, self._log, f"Original: {original_path.name}")
            self.root.after(0, self._log, f"Reference: {reference_path.name}")
            self.root.after(0, self._log, f"Mode: {'Audio File (ChatterBox VC)' if mode == 'audio' else 'RVC Model'}")
            
            # Prepare temp directory and clean up old files
            temp_dir = self.file_manager.get_workspace_temp_dir("voice_cloning")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean up old output files to prevent file locks
            for old_file in temp_dir.glob("*.wav"):
                try:
                    old_file.unlink()
                    self.root.after(0, self._log, f"Cleaned up old file: {old_file.name}")
                except Exception as e:
                    self.root.after(0, self._log, f"[WARNING] Could not delete {old_file.name}: {e}")
            
            # Save to processed.wav - this is the ORIGINAL generated file
            # It will NEVER be modified - all edits work from a copy
            output_path = temp_dir / "processed.wav"
            
            # Progress callback - handles both single and dual argument calls
            def progress_cb(percent, message=None):
                if message is None:
                    # Single argument call from chatterbox_vc_wrapper (just percent)
                    message = f"Processing... {int(percent * 100)}%"
                self.root.after(0, self._update_progress, percent * 100, message)
            
            # Process based on mode
            if mode == "audio":
                # ChatterBox VC mode
                result_path, error = self.vc_wrapper.convert_voice(
                    source_audio_path=original_path,
                    target_voice_path=reference_path,
                    output_path=output_path,
                    progress_callback=progress_cb
                )
            else:
                # RVC mode
                # First load the RVC model
                self.root.after(0, self._update_progress, 10, "Loading RVC model...")
                success, load_error = self.rvc_wrapper.load_model_from_zip(reference_path)
                
                if not success:
                    raise RuntimeError(f"Failed to load RVC model: {load_error}")
                
                # Get RVC parameters
                rvc_params = self.input_panel.get_rvc_params()
                
                self.root.after(0, self._log, f"RVC Parameters: {rvc_params}")
                
                # Convert voice
                result_path, error = self.rvc_wrapper.convert_voice(
                    source_audio_path=original_path,
                    output_path=output_path,
                    progress_callback=progress_cb,
                    **rvc_params
                )
            
            if error:
                raise RuntimeError(error)
            
            # Success
            self.processed_audio_path = result_path
            self.original_audio_path = original_path
            self.edited_audio_path = None  # Reset edited version
            
            self.root.after(0, self._process_complete, result_path)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Voice cloning failed: {error_msg}", exc_info=True)
            self.root.after(0, self._process_failed, error_msg)
    
    def _process_complete(self, result_path: Path):
        """Handle successful processing"""
        try:
            # Load into spectrum editor
            self.output_panel.load_audio(result_path)
            
            self._log(f"[+] Voice cloning complete!")
            self._log(f"Output: {result_path.name}")
            self._update_progress(100, "Processing complete!")
            
            # Enable export
            self.input_panel.enable_export(True)
            
            messagebox.showinfo("Success", "Voice cloning completed successfully!")
            
        except Exception as e:
            self._process_failed(f"Failed to load result: {e}")
        finally:
            # Re-enable UI
            self.input_panel.set_enabled(True)
    
    def _process_failed(self, error_msg: str):
        """Handle processing failure"""
        self._log(f"[!] Voice cloning failed: {error_msg}")
        self._update_progress(0, "Processing failed")
        
        messagebox.showerror("Processing Error", f"Voice cloning failed:\n\n{error_msg}")
        
        # Re-enable UI
        self.input_panel.set_enabled(True)
        self.input_panel.enable_export(False)
    
    def _apply_curve_changes(self):
        """Apply curve edits to processed audio"""
        if not self.processed_audio_path or not self.processed_audio_path.exists():
            messagebox.showwarning("No Audio", "No processed audio available to edit")
            return
        
        # Release audio file handle BEFORE starting thread to prevent file locks
        self.output_panel.release_audio_file()
        
        # Disable UI during processing
        self.input_panel.set_enabled(False)
        
        # Start in background thread
        apply_thread = threading.Thread(target=self._apply_curves_worker, daemon=True)
        apply_thread.start()
    
    def _apply_curves_worker(self):
        """Background worker for applying curve edits"""
        try:
            import shutil
            
            self.root.after(0, self._log, "Applying curve edits...")
            self.root.after(0, self._update_progress, 0, "Applying edits...")
            
            # Get curves
            pitch_curve = self.output_panel.get_pitch_curve()
            reverb_curve = self.output_panel.get_reverb_curve()
            volume_curve = self.output_panel.get_volume_curve()
            
            # Prepare output directory
            temp_dir = self.file_manager.get_workspace_temp_dir("voice_cloning")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # IMPORTANT: Always start with ORIGINAL processed file (processed.wav)
            # This prevents adjustments from compounding - each edit starts fresh from the base
            current_audio = self.processed_audio_path
            
            # Apply pitch curve
            if pitch_curve.has_edits():
                self.root.after(0, self._log, "Applying pitch curve...")
                self.root.after(0, self._update_progress, 30, "Applying pitch adjustments...")
                
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
            
            # Apply volume curve
            if volume_curve.has_edits():
                self.root.after(0, self._log, "Applying volume curve...")
                self.root.after(0, self._update_progress, 60, "Applying volume adjustments...")
                
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
            
            # Apply reverb curve
            if reverb_curve.has_edits():
                self.root.after(0, self._log, "Applying reverb curve...")
                self.root.after(0, self._update_progress, 80, "Applying reverb...")
                
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
            
            # Save final edited version (always overwrites processed_edited.wav)
            edited_path = temp_dir / "processed_edited.wav"
            if current_audio != edited_path:
                # Delete old edited version if exists
                if edited_path.exists():
                    try:
                        edited_path.unlink()
                    except Exception:
                        pass
                
                shutil.copy(str(current_audio), str(edited_path))
            
            self.edited_audio_path = edited_path
            self.root.after(0, self._apply_curves_complete, edited_path)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to apply curve edits: {error_msg}", exc_info=True)
            self.root.after(0, self._apply_curves_failed, error_msg)
    
    def _apply_curves_complete(self, edited_path: Path):
        """Handle successful curve application"""
        try:
            # Reload audio in spectrum editor (preserves curves)
            self.output_panel.reload_audio_only(edited_path)
            
            self._log(f"[+] Curve edits applied successfully")
            self._update_progress(100, "Edits applied!")
            
        except Exception as e:
            self._apply_curves_failed(f"Failed to reload audio: {e}")
        finally:
            # Re-enable UI
            self.input_panel.set_enabled(True)
    
    def _apply_curves_failed(self, error_msg: str):
        """Handle curve application failure"""
        self._log(f"[!] Failed to apply edits: {error_msg}")
        self._update_progress(0, "Edit failed")
        
        messagebox.showerror("Edit Error", f"Failed to apply curve edits:\n\n{error_msg}")
        
        # Re-enable UI
        self.input_panel.set_enabled(True)
    
    def _on_export_clicked(self):
        """Handle Export button click"""
        # Determine which audio to export based on checkbox
        use_edited = self.input_panel.get_use_edited()
        
        if use_edited and self.edited_audio_path and self.edited_audio_path.exists():
            # User wants edited version and it exists
            source_path = self.edited_audio_path
            self._log("Exporting edited version...")
        elif use_edited and (not self.edited_audio_path or not self.edited_audio_path.exists()):
            # User wants edited version but it doesn't exist
            messagebox.showwarning(
                "No Edited Version",
                "No edited version available. Apply curve changes first, or uncheck 'Use edited version'."
            )
            return
        elif self.processed_audio_path and self.processed_audio_path.exists():
            # User wants processed version (or edited doesn't exist)
            source_path = self.processed_audio_path
            self._log("Exporting processed version...")
        else:
            messagebox.showwarning("No Audio", "No audio available to export")
            return
        
        # Get output format
        output_format = self.input_panel.get_output_format()
        
        # Ask user for save location
        default_name = f"cloned_voice.{output_format}"
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
        
        # Release file handle before reading in background thread
        self.output_panel.release_audio_file()
        
        # Start export in background thread
        export_thread = threading.Thread(
            target=self._export_worker,
            args=(source_path, output_path, output_format),
            daemon=True
        )
        export_thread.start()
    
    def _export_worker(self, source_path: Path, output_path: Path, output_format: str):
        """Background worker for exporting audio"""
        try:
            self.root.after(0, self._log, f"Exporting to {output_format.upper()}...")
            self.root.after(0, self._update_progress, 0, "Exporting...")
            
            # Import here to avoid circular dependencies
            import librosa
            import soundfile as sf
            
            # Load audio
            self.root.after(0, self._update_progress, 30, "Loading audio...")
            y, sr = librosa.load(str(source_path), sr=None)
            
            # Save in requested format
            self.root.after(0, self._update_progress, 70, f"Saving as {output_format.upper()}...")
            sf.write(str(output_path), y, sr, format=output_format.upper())
            
            self.root.after(0, self._export_complete, output_path)
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Export failed: {error_msg}", exc_info=True)
            self.root.after(0, self._export_failed, error_msg)
    
    def _export_complete(self, output_path: Path):
        """Handle successful export"""
        self._log(f"[+] Export complete: {output_path}")
        self._update_progress(100, "Export complete!")
        
        messagebox.showinfo("Export Complete", f"Audio exported successfully to:\n{output_path}")
    
    def _export_failed(self, error_msg: str):
        """Handle export failure"""
        self._log(f"[!] Export failed: {error_msg}")
        self._update_progress(0, "Export failed")
        
        messagebox.showerror("Export Error", f"Failed to export audio:\n\n{error_msg}")
