"""Voice Enhancement workspace for Voice Revolver AI."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
import threading
import shutil
import logging
from typing import Callable, Optional

from voice_revolver_core.domain.file_manager import FileManager
from voice_revolver_core.infrastructure.resemble_enhance_wrapper import (
    enhance_vocals,
    is_resemble_enhance_available,
    get_estimated_time
)
from voice_revolver_core.infrastructure.audio_processor import AudioProcessor

from .components import InputPanel, OutputPanel


logger = logging.getLogger(__name__)


class VoiceEnhancementWorkspace(ttk.Frame):
    """Workspace for enhancing audio with Resemble Enhance."""
    
    def __init__(
        self,
        parent,
        root,
        app_data_path: Path,
        device: str,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        """Initialize the Voice Enhancement workspace.
        
        Args:
            parent: Parent widget
            root: Root Tk instance (for thread-safe UI updates)
            app_data_path: Application data directory path
            device: Computing device ('cpu' or 'cuda')
            log_callback: Optional callback for logging messages
        """
        super().__init__(parent)
        
        self.root = root
        self.device = device
        self.log_callback = log_callback
        self.file_manager = FileManager(app_data_path)
        self.audio_processor = AudioProcessor()
        
        # Audio file paths
        self.input_audio_path: Optional[Path] = None
        self.original_audio_path: Optional[Path] = None  # Copy in temp (for blend mode)
        self.enhanced_audio_path: Optional[Path] = None  # Enhanced output (IMMUTABLE)
        self.edited_audio_path: Optional[Path] = None    # Curve-edited version
        
        # Progress tracking
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="Ready")
        
        # Processing state
        self.is_processing = False
        
        self._setup_ui()
        self._check_dependencies()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid layout
        self.columnconfigure(0, weight=1)  # Input panel (left)
        self.columnconfigure(1, weight=2)  # Output panel (right, wider)
        self.rowconfigure(0, weight=1)     # Content panels expand
        self.rowconfigure(1, weight=0)     # Progress bar fixed
        
        # Input panel (left)
        self.input_panel = InputPanel(
            self,
            on_process=self._on_process_clicked,
            on_export=self._on_export_clicked
        )
        self.input_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Output panel (right)
        self.output_panel = OutputPanel(
            self,
            apply_changes_callback=self._apply_blend_curve
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
    
    def _check_dependencies(self):
        """Check if Resemble Enhance is available."""
        if not is_resemble_enhance_available():
            self._log("[WARNING] venv-enhance not found. Voice enhancement will not work.")
            self._log("[INFO] See docs/venv-enhance-setup.md for installation instructions.")
            # Disable processing (will show error dialog on click)
    
    def _log(self, message: str):
        """Log a message.
        
        Args:
            message: Message to log
        """
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)
    
    def _update_progress(self, percent: float, message: str):
        """Update progress bar and message (thread-safe).
        
        Args:
            percent: Progress percentage (0-100)
            message: Progress message
        """
        self.progress_var.set(percent)
        self.progress_text_var.set(message)
    
    # ===== Processing Workflow =====
    
    def _on_process_clicked(self):
        """Handle Start Enhancement button click."""
        # Validate input
        audio_path = self.input_panel.get_audio_path()
        if not audio_path or not Path(audio_path).exists():
            messagebox.showerror(
                "No Audio File",
                "Please select an audio file to enhance."
            )
            return
        
        # Check venv-enhance availability
        if not is_resemble_enhance_available():
            messagebox.showerror(
                "Resemble Enhance Not Available",
                "venv-enhance is not installed.\n\n"
                "See docs/venv-enhance-setup.md for installation instructions."
            )
            return
        
        # Prevent multiple simultaneous processing
        if self.is_processing:
            messagebox.showwarning(
                "Processing In Progress",
                "Please wait for current processing to complete."
            )
            return
        
        self.input_audio_path = Path(audio_path)
        
        # Release previous audio files to prevent locks
        self.output_panel.release_audio_file()
        
        # Disable controls
        self.input_panel.set_processing(True)
        self.is_processing = True
        
        # Start processing in background thread
        thread = threading.Thread(target=self._process_worker, daemon=True)
        thread.start()
    
    def _process_worker(self):
        """Background worker for enhancement processing."""
        try:
            # Get temp directory
            temp_dir = self.file_manager.get_workspace_temp_dir("voice_enhancement")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Clean old temp files to prevent locks
            self.root.after(0, self._log, "[*] Cleaning temp directory...")
            for old_file in temp_dir.glob("*.wav"):
                try:
                    old_file.unlink()
                    self.root.after(0, self._log, f"[+] Deleted {old_file.name}")
                except Exception as e:
                    self.root.after(0, self._log, f"[!] Could not delete {old_file.name}: {e}")
            
            # Copy original to temp (for blend mode comparison)
            self.root.after(0, self._update_progress, 5, "Preparing input...")
            original_path = temp_dir / "original.wav"
            
            # Convert to WAV if needed (ResembleEnhance prefers WAV)
            if self.input_audio_path.suffix.lower() != '.wav':
                self.root.after(0, self._log, "[*] Converting input to WAV format...")
                import librosa
                import soundfile as sf
                y, sr = librosa.load(str(self.input_audio_path), sr=None)
                sf.write(str(original_path), y, sr, format='WAV')
            else:
                shutil.copy(str(self.input_audio_path), str(original_path))
            
            self.original_audio_path = original_path
            
            # Get enhancement parameters
            params = self.input_panel.get_enhancement_params()
            
            # Estimate processing time
            import librosa
            duration = librosa.get_duration(path=str(original_path))
            estimated_time = get_estimated_time(duration, self.device)
            
            self.root.after(
                0,
                self._log,
                f"[*] Starting enhancement (estimated time: {int(estimated_time)}s)..."
            )
            self.root.after(0, self._log, f"[*] Parameters: NFE={params['nfe']}, "
                           f"Temperature={params['temperature']}, Solver={params['solver']}, "
                           f"Denoise={params['denoise_first']}")
            
            # Progress callback
            def progress_cb(percent: float, message: str):
                # ResembleEnhance sends percent as 0-100
                self.root.after(0, self._update_progress, percent, message)
            
            # Call ResembleEnhance
            enhanced_path = temp_dir / "enhanced.wav"
            
            success = enhance_vocals(
                input_path=original_path,
                output_path=enhanced_path,
                solver=params['solver'],
                nfe=params['nfe'],
                temperature=params['temperature'],
                denoise_first=params['denoise_first'],
                progress_callback=progress_cb
            )
            
            if success and enhanced_path.exists():
                self.enhanced_audio_path = enhanced_path
                self.root.after(0, self._process_complete)
            else:
                self.root.after(
                    0,
                    self._process_failed,
                    "Enhancement failed. Check logs for details."
                )
        
        except Exception as e:
            logger.exception("Enhancement processing failed")
            self.root.after(0, self._process_failed, str(e))
    
    def _process_complete(self):
        """Handle successful enhancement completion."""
        self._log("[+] Enhancement complete!")
        self._update_progress(100, "Enhancement complete")
        
        # Load both original and enhanced into spectrum editor (blend mode)
        self.output_panel.load_audio(
            audio_path=self.original_audio_path,
            enhanced_path=self.enhanced_audio_path
        )
        
        # Enable controls
        self.input_panel.set_processing(False)
        self.input_panel.enable_export(True)
        self.is_processing = False
        
        messagebox.showinfo(
            "Enhancement Complete",
            "Voice enhancement complete!\n\n"
            "You can now:\n"
            "- Switch to 'Blend (Enhanced)' mode to compare original vs enhanced\n"
            "- Edit curves (pitch, reverb, volume)\n"
            "- Click 'Apply Changes' to preview curve edits\n"
            "- Export the result"
        )
    
    def _process_failed(self, error_message: str):
        """Handle enhancement failure.
        
        Args:
            error_message: Error description
        """
        self._log(f"[!] Enhancement failed: {error_message}")
        self._update_progress(0, "Enhancement failed")
        
        # Re-enable controls
        self.input_panel.set_processing(False)
        self.is_processing = False
        
        messagebox.showerror(
            "Enhancement Failed",
            f"Voice enhancement failed:\n\n{error_message}"
        )
    
    # ===== Apply Changes Workflow =====
    
    def _apply_blend_curve(self):
        """Apply curve edits (pitch/reverb/volume) or blend curve."""
        if not self.enhanced_audio_path or not self.enhanced_audio_path.exists():
            messagebox.showwarning(
                "No Enhanced Audio",
                "Enhanced audio not found. Please run enhancement first."
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
        """Background worker for applying curve edits (pitch/reverb/volume/blend)."""
        try:
            import shutil
            
            temp_dir = self.file_manager.get_workspace_temp_dir("voice_enhancement")
            
            self.root.after(0, self._update_progress, 10, "Applying curve edits...")
            self.root.after(0, self._log, "[*] Applying curve edits...")
            
            # Get curves
            pitch_curve = self.output_panel.pitch_curve
            reverb_curve = self.output_panel.reverb_curve
            volume_curve = self.output_panel.volume_curve
            blend_curve = self.output_panel.spectrum_editor.blend_curve
            
            # Track whether blend was applied
            blend_was_applied = False
            
            # IMPORTANT: ALWAYS start from ORIGINAL enhanced audio (non-compounding edits)
            # self.enhanced_audio_path = pristine enhanced.wav from ResembleEnhance (never changes)
            # self.edited_audio_path = result from previous Apply (if any), only used for display
            # This ensures pitch/reverb/volume edits don't compound - each apply starts fresh
            current_audio = self.enhanced_audio_path
            
            # Apply curves in correct order: BLEND FIRST, then pitch/volume/reverb
            # (Blend mixes original vs enhanced, then other effects applied to the blend)
            
            # 1. Blend curve FIRST (if in blend mode)
            if blend_curve.has_edits() and self.original_audio_path and self.original_audio_path.exists():
                self.root.after(0, self._update_progress, 20, "Applying blend curve...")
                self.root.after(0, self._log, "[*] Applying blend curve...")
                blend_output = temp_dir / "temp_blend.wav"
                success = self.audio_processor.apply_blend_curve(
                    original_path=self.original_audio_path,
                    enhanced_path=self.enhanced_audio_path,
                    output_path=blend_output,
                    blend_curve=blend_curve
                )
                if success and blend_output.exists():
                    current_audio = blend_output
                    blend_was_applied = True
                    self.root.after(0, self._log, "[+] Blend curve applied")
                else:
                    raise RuntimeError("Failed to apply blend curve")
            
            # 2. Pitch curve (applied to blended or enhanced audio)
            if pitch_curve.has_edits():
                self.root.after(0, self._update_progress, 40, "Applying pitch curve...")
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
            
            # 3. Volume curve
            if volume_curve.has_edits():
                self.root.after(0, self._update_progress, 65, "Applying volume curve...")
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
            
            # 4. Reverb curve
            if reverb_curve.has_edits():
                self.root.after(0, self._update_progress, 85, "Applying reverb curve...")
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
            
            # Save final edited version (overwrites each time)
            edited_path = temp_dir / "enhanced_edited.wav"
            shutil.copy(str(current_audio), str(edited_path))
            self.edited_audio_path = edited_path
            
            self.root.after(0, self._apply_curves_complete, blend_was_applied)
        
        except Exception as e:
            logger.exception("Apply curves failed")
            self.root.after(0, self._apply_curves_failed, str(e))
    
    def _apply_curves_complete(self, blend_was_applied: bool = False):
        """Handle successful curve application."""
        self._log("[+] Curve edits applied successfully")
        self._update_progress(100, "Curve edits applied")
        
        # Reload edited audio WITHOUT resetting curves (preserves blend mode + all curves)
        # This updates audio_data to the edited version while keeping enhanced_audio_data unchanged
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
                    "Please apply curve changes first, or uncheck 'Use edited version'."
                )
                return
            source_path = self.edited_audio_path
        else:
            if not self.enhanced_audio_path or not self.enhanced_audio_path.exists():
                messagebox.showwarning(
                    "No Enhanced Audio",
                    "No enhanced audio available. Please run enhancement first."
                )
                return
            source_path = self.enhanced_audio_path
        
        # Get output format
        output_format = self.input_panel.get_output_format()
        
        # Ask for output location
        default_filename = f"enhanced.{output_format}"
        output_path = filedialog.asksaveasfilename(
            title="Export Enhanced Audio",
            defaultextension=f".{output_format}",
            initialfile=default_filename,
            filetypes=[
                (f"{output_format.upper()} Files", f"*.{output_format}"),
                ("All Files", "*.*")
            ]
        )
        
        if not output_path:
            return  # User cancelled
        
        output_path = Path(output_path)
        
        # Disable controls
        self.input_panel.set_processing(True)
        
        # Start export in background thread
        thread = threading.Thread(
            target=self._export_worker,
            args=(source_path, output_path, output_format),
            daemon=True
        )
        thread.start()
    
    def _export_worker(self, source_path: Path, output_path: Path, output_format: str):
        """Background worker for exporting audio.
        
        Args:
            source_path: Source audio file
            output_path: Destination file path
            output_format: Output format (wav, mp3, flac, ogg)
        """
        try:
            self.root.after(0, self._update_progress, 30, "Loading audio...")
            self.root.after(0, self._log, f"[*] Exporting to {output_path}...")
            
            import librosa
            import soundfile as sf
            
            # Load audio
            y, sr = librosa.load(str(source_path), sr=None)
            
            # Save in requested format
            self.root.after(0, self._update_progress, 70, f"Saving as {output_format.upper()}...")
            sf.write(str(output_path), y, sr, format=output_format.upper())
            
            self.root.after(0, self._export_complete, output_path)
        
        except Exception as e:
            logger.exception("Export failed")
            self.root.after(0, self._export_failed, str(e))
    
    def _export_complete(self, output_path: Path):
        """Handle successful export.
        
        Args:
            output_path: Path to exported file
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
