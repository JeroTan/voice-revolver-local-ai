"""
Audio Separation Workspace - Main Frame
Full workspace for separating and editing audio stems
"""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
import threading
import logging
from typing import Optional

from voice_revolver_ui.features.audio_separation.components import (
    InputPanel,
    TrackListPanel
)
from voice_revolver_core.domain.base import AudioStems
from voice_revolver_core.domain.file_manager import FileManager

logger = logging.getLogger(__name__)


class AudioSeparationWorkspace(ttk.Frame):
    """
    Complete workspace for audio stem separation and editing.
    
    Features:
    - Audio file input and model selection
    - Stem separation (vocals, drums, bass, other)
    - Optional vocal enhancement
    - Individual track editing with spectrum curves
    - Per-track export
    
    Layout:
    - Top: InputPanel (file selection, separation controls)
    - Bottom: TrackListPanel (scrollable track editors)
    """
    
    def __init__(self, parent, root, app_data_path, device="cpu", log_callback=None, **kwargs):
        """
        Initialize audio separation workspace.
        
        Args:
            parent: Parent tkinter widget
            root: Root tkinter window (for thread-safe UI updates)
            app_data_path: Path to app data directory
            device: Processing device ("cpu" or "cuda") from startup dialog
            log_callback: Optional callback for logging messages
            **kwargs: Additional configuration for the Frame
        """
        super().__init__(parent, **kwargs)
        
        self.root = root
        self.device = device
        self.log_callback = log_callback
        
        # State
        self.file_manager = FileManager(app_data_path)
        self.separation_thread: Optional[threading.Thread] = None
        self.stems: Optional[AudioStems] = None
        
        # Progress variables
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="")
        
        # UI setup
        self._setup_ui()
        
    def _setup_ui(self):
        """Create and layout child widgets."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Track list expands
        self.rowconfigure(3, weight=0)  # Progress bar fixed height
        
        # Input panel (top)
        self.input_panel = InputPanel(
            self,
            device=self.device,
            on_separate=self._on_separate_triggered
        )
        self.input_panel.grid(row=0, column=0, sticky=(tk.N, tk.W, tk.E), padx=5, pady=5)
        
        # Separator
        ttk.Separator(self, orient=tk.HORIZONTAL).grid(
            row=1, column=0, sticky=(tk.W, tk.E), pady=10
        )
        
        # Track list panel (middle, scrollable)
        self.track_list_panel = TrackListPanel(self)
        self.track_list_panel.grid(row=2, column=0, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5)
        
        # Progress bar (bottom - always visible in layout)
        progress_frame = ttk.Frame(self)
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode='determinate',
            variable=self.progress_var,
            maximum=100
        )
        self.progress_bar.pack(fill=tk.X, expand=True, padx=5, pady=2)
        
        self.status_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_text_var,
            foreground="green"
        )
        self.status_label.pack(pady=2)
        
    def _log(self, message: str):
        """Log message via callback if available."""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)
    
    def _on_separate_triggered(self):
        """Handle separation button click."""
        audio_path = self.input_panel.get_audio_path()
        
        if not audio_path or not audio_path.exists():
            self._log("[ERROR] Invalid audio file")
            return
        
        # Clear existing tracks
        self.track_list_panel.clear_tracks()
        
        # Show progress
        self.progress_text_var.set("Initializing...")
        self.progress_var.set(0)
        
        # Disable input controls during processing
        self.input_panel.set_enabled(False)
        
        # Start separation in background thread
        self.separation_thread = threading.Thread(
            target=self._separation_worker,
            daemon=False
        )
        self.separation_thread.start()
    
    def _separation_worker(self):
        """Background worker for audio separation."""
        try:
            # Import required components
            from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
            from voice_revolver_core.infrastructure.mdx_wrapper import MDXWrapper
            from voice_revolver_core.infrastructure.vocal_enhancer import VocalEnhancer
            
            # Get settings
            audio_path = self.input_panel.get_audio_path()
            model = self.input_panel.get_model()
            device = self.input_panel.get_device()
            improve_vocals = self.input_panel.get_improve_vocals()
            
            # Progress callback for thread-safe UI updates
            def progress_cb(percentage, message):
                self.root.after(0, self._update_progress, percentage, message)
            
            # 1. Initialize separator based on model selection
            progress_cb(5, "Loading separation model...")
            
            if model == "mdx":
                self._log("Using MDX separation (best vocal quality)")
                separator = MDXWrapper(device=device)
            else:  # demucs
                self._log("Using Demucs separation (balanced)")
                separator = DemucsWrapper(device=device)
            
            # 2. Run separation
            progress_cb(10, f"Separating audio into stems...")
            self._log(f"Processing: {audio_path.name}")
            
            output_dir = self.file_manager.get_workspace_temp_dir("audio_separation") / "separation"
            
            # Clean up old separation files with retry logic (Windows file locks)
            if output_dir.exists():
                import time
                for wav_file in output_dir.glob("*.wav"):
                    # Keep enhanced vocals cache if same file
                    if wav_file.name == "vocals_enhanced.wav":
                        continue
                    
                    # Retry deletion up to 3 times with delays
                    deleted = False
                    for attempt in range(3):
                        try:
                            wav_file.unlink()
                            deleted = True
                            break
                        except PermissionError as e:
                            if attempt < 2:
                                self._log(f"[WARNING] File locked, retrying... ({wav_file.name})")
                                time.sleep(0.5)  # Wait 500ms before retry
                            else:
                                self._log(f"[ERROR] Could not delete {wav_file.name}: {e}")
                                # Force overwrite by renaming old file
                                try:
                                    backup_name = wav_file.with_suffix('.wav.old')
                                    wav_file.rename(backup_name)
                                    self._log(f"Renamed locked file to {backup_name.name}")
                                except Exception as rename_err:
                                    self._log(f"[ERROR] Cannot delete or rename: {rename_err}")
                        except Exception as e:
                            self._log(f"[WARNING] Could not delete {wav_file.name}: {e}")
                            break
                    
                    if deleted:
                        self._log(f"Deleted old {wav_file.name}")
                
                self._log("Cleanup complete")
            
            output_dir.mkdir(exist_ok=True, parents=True)
            
            # Copy input to generic temp name to avoid filename issues
            import shutil
            temp_input = output_dir / "input_audio.wav"
            if temp_input.exists():
                try:
                    temp_input.unlink()
                except Exception:
                    pass
            
            try:
                shutil.copy2(audio_path, temp_input)
                self._log(f"Copied input to temp file: {temp_input.name}")
                audio_path_to_process = temp_input
            except Exception as e:
                self._log(f"[WARNING] Could not copy to temp file, using original: {e}")
                audio_path_to_process = audio_path
            
            stems_dict, error = separator.separate(
                audio_path=audio_path_to_process,
                output_dir=output_dir
            )
            
            # Cleanup temp input file
            if audio_path_to_process != audio_path and audio_path_to_process.exists():
                try:
                    audio_path_to_process.unlink()
                    self._log(f"Cleaned up temp input file")
                except Exception as e:
                    self._log(f"[WARNING] Could not delete temp input: {e}")
            
            if error:
                raise RuntimeError(error)
            
            # Convert dict to AudioStems
            stems = AudioStems(
                vocals=stems_dict.get('vocals'),
                drums=stems_dict.get('drums'),
                bass=stems_dict.get('bass'),
                other=stems_dict.get('other'),
            )
            
            progress_cb(60, "Audio separated successfully")
            self._log(f"[OK] Stems extracted:")
            if stems.vocals:
                self._log(f"  - Vocals: {stems.vocals.name}")
            if stems.drums:
                self._log(f"  - Drums: {stems.drums.name}")
            if stems.bass:
                self._log(f"  - Bass: {stems.bass.name}")
            if stems.other:
                self._log(f"  - Other: {stems.other.name}")
            
            # 3. Optional vocal enhancement
            if improve_vocals and stems.vocals:
                progress_cb(70, "Enhancing vocals...")
                self._log("Applying vocal enhancement (noise reduction + clarity)")
                
                enhancer = VocalEnhancer(sample_rate=22050)
                enhanced_path = output_dir / "vocals_enhanced.wav"
                
                result_path, enhance_error = enhancer.enhance_vocal(
                    input_path=stems.vocals,
                    output_path=enhanced_path,
                    noise_reduction=0.8,
                    remove_reverb=True
                )
                
                if result_path and not enhance_error:
                    # Store enhanced vocals separately (keep original for blend mode)
                    stems.vocals_enhanced = result_path
                    self._log(f"[OK] Vocals enhanced: {result_path.name}")
                else:
                    self._log(f"[WARNING] Vocal enhancement failed: {enhance_error}")
            
            # 4. Load tracks into UI
            progress_cb(90, "Loading tracks...")
            self.stems = stems
            
            # Thread-safe UI update
            self.root.after(0, self._load_tracks_complete, stems, improve_vocals)
            
            progress_cb(100, "Complete!")
            
        except Exception as e:
            error_msg = f"Separation failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.root.after(0, self._separation_failed, error_msg)
    
    def _update_progress(self, percentage: float, message: str):
        """Thread-safe progress update."""
        self.progress_var.set(percentage)
        self.progress_text_var.set(message)
    
    def _load_tracks_complete(self, stems: AudioStems, improve_vocals: bool):
        """Complete track loading (called in main thread)."""
        try:
            # Load stems into track list
            self.track_list_panel.load_tracks(stems, improve_vocals)
            
            # Update progress to complete
            self.progress_text_var.set("Ready")
            self.input_panel.set_enabled(True)
            
            self._log("[SUCCESS] Audio separation complete! Edit each track and export individually.")
            
        except Exception as e:
            logger.error(f"Failed to load tracks: {e}", exc_info=True)
            self._separation_failed(f"Failed to load tracks: {str(e)}")
    
    def _separation_failed(self, error_msg: str):
        """Handle separation failure (called in main thread)."""
        self._log(f"[ERROR] {error_msg}")
        
        # Update progress and re-enable controls
        self.progress_text_var.set("Failed")
        self.status_label.config(foreground="red")
        self.input_panel.set_enabled(True)
        
        # Show error dialog
        from tkinter import messagebox
        messagebox.showerror(
            "Separation Failed",
            f"Audio separation failed:\n\n{error_msg}"
        )
    
    def cleanup(self):
        """Cleanup resources when workspace is destroyed."""
        # Stop any running threads
        if self.separation_thread and self.separation_thread.is_alive():
            logger.warning("Separation thread still running during cleanup")
        
        # Clear tracks
        self.track_list_panel.clear_tracks()
        
        logger.info("Audio separation workspace cleaned up")
