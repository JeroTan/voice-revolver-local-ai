"""
Text-to-Speech Workspace
Main workspace for TTS generation using ChatterBox TTS
"""

import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Optional
import threading
import logging

from voice_revolver_core.domain.file_manager import FileManager
from voice_revolver_core.infrastructure.chatterbox_tts_wrapper import ChatterBoxTTSWrapper
from voice_revolver_ui.features.text_to_speech.components import InputPanel, OutputPanel

logger = logging.getLogger(__name__)


class TextToSpeechWorkspace(ttk.Frame):
    """Text-to-Speech workspace for generating speech from text"""
    
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
        Initialize TTS workspace.
        
        Args:
            parent: Parent widget
            root: Root window (for thread-safe updates)
            app_data_path: Application data directory
            device: Device to use (cpu/cuda)
            log_callback: Optional logging callback
        """
        super().__init__(parent, **kwargs)
        
        self.root = root
        self.device = device
        self.log_callback = log_callback
        self.file_manager = FileManager(app_data_path)
        
        # TTS state
        self.tts_wrapper = ChatterBoxTTSWrapper(device=self.device)
        self.generation_thread: Optional[threading.Thread] = None
        self.generated_audio_path: Optional[Path] = None
        
        # Progress tracking
        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="")
        
        self._setup_ui()
    
    def _log(self, message: str):
        """Log message"""
        if self.log_callback:
            self.log_callback(message)
        logger.info(message)
    
    def _setup_ui(self):
        """Create UI components"""
        # Configure grid
        self.columnconfigure(0, weight=1)  # Input panel
        self.columnconfigure(1, weight=2)  # Output panel (wider for spectrogram)
        self.rowconfigure(0, weight=1)  # Content area expands
        self.rowconfigure(1, weight=0)  # Progress bar fixed
        
        # === Input Panel (Left) ===
        self.input_panel = InputPanel(
            self,
            device=self.device,
            on_generate=self._on_generate_clicked
        )
        self.input_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 2), pady=5)
        
        # === Output Panel (Right) ===
        self.output_panel = OutputPanel(
            self,
            log_callback=self.log_callback
        )
        self.output_panel.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(2, 5), pady=5)
        
        # === Progress Bar (Bottom, full width) ===
        progress_frame = ttk.Frame(self, height=60)
        progress_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        progress_frame.grid_propagate(False)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            mode="determinate",
            variable=self.progress_var,
            length=400
        )
        self.progress_bar.pack(fill=tk.X, expand=True, padx=5, pady=(5, 2))
        
        self.status_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_text_var,
            foreground="gray"
        )
        self.status_label.pack(pady=(0, 5))
    
    def _on_generate_clicked(self):
        """Handle Generate button click"""
        # Validate inputs
        is_valid, error_msg = self.input_panel.validate()
        if not is_valid:
            self._log(f"[ERROR] {error_msg}")
            messagebox.showwarning("Validation Error", error_msg)
            return
        
        # Release any existing audio file handles to prevent file locking issues
        # (pygame.mixer keeps files locked on Windows)
        self.output_panel.spectrum_editor.release_audio_file()
        
        # Disable UI
        self.input_panel.set_enabled(False)
        self.output_panel.set_generating(True)
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_text_var.set("Initializing...")
        
        # Start generation thread
        self.generation_thread = threading.Thread(
            target=self._generation_worker,
            daemon=False
        )
        self.generation_thread.start()
    
    def _generation_worker(self):
        """Background worker for TTS generation"""
        try:
            # Get parameters
            text = self.input_panel.get_text()
            language = self.input_panel.get_language()
            use_turbo = self.input_panel.get_use_turbo()
            use_default_voice = self.input_panel.get_use_default_voice()
            device = self.input_panel.get_device()
            
            # Update device if changed
            self.tts_wrapper.set_device(device)
            
            # Reference audio (None if using default voice)
            ref_audio = None if use_default_voice else self.input_panel.get_reference_audio()
            
            # TTS parameters
            exaggeration = self.input_panel.get_exaggeration()
            cfg_weight = self.input_panel.get_cfg_weight()
            temperature = self.input_panel.get_temperature()
            
            # Output path
            output_dir = self.file_manager.get_workspace_temp_dir("text_to_speech")
            output_dir.mkdir(exist_ok=True, parents=True)
            output_path = output_dir / "generated.wav"
            
            # Progress callback
            def progress_cb(percent, message):
                self.root.after(0, self._update_progress, percent, message)
            
            # Log generation details
            self.root.after(0, self._log, f"Generating speech...")
            self.root.after(0, self._log, f"Device: {device.upper()}")
            self.root.after(0, self._log, f"Text: {text[:50]}{'...' if len(text) > 50 else ''}")
            self.root.after(0, self._log, f"Language: {language}")
            if use_turbo:
                self.root.after(0, self._log, "Mode: English TTS (better quality)")
            else:
                self.root.after(0, self._log, "Mode: Multi-language TTS")
            
            if ref_audio:
                self.root.after(0, self._log, f"Reference: {ref_audio.name}")
            else:
                self.root.after(0, self._log, "Reference: Default voice")
            
            # Generate speech
            result_path, error = self.tts_wrapper.generate(
                text=text,
                output_path=output_path,
                language=language,
                reference_audio_path=ref_audio,
                exaggeration=exaggeration,
                cfg_weight=cfg_weight,
                temperature=temperature,
                use_turbo=use_turbo,
                progress_callback=progress_cb
            )
            
            if error:
                raise RuntimeError(error)
            
            # Success
            self.root.after(0, self._generation_complete, result_path)
            
        except Exception as e:
            self.root.after(0, self._generation_failed, str(e))
    
    def _update_progress(self, percent: float, message: str):
        """Update progress bar (called from worker thread via root.after)"""
        self.progress_var.set(percent)
        self.progress_text_var.set(message)
    
    def _generation_complete(self, audio_path: Path):
        """Handle successful generation"""
        try:
            self.generated_audio_path = audio_path
            
            # Load into output panel
            self.output_panel.load_generated_audio(audio_path)
            
            # Re-enable UI
            self.input_panel.set_enabled(True)
            self.output_panel.set_generating(False)
            
            self.progress_var.set(100)
            self.progress_text_var.set("Generation complete!")
            
            self._log("[OK] Speech generation complete")
            
        except Exception as e:
            logger.error(f"Failed to load generated audio: {e}")
            self._log(f"[ERROR] Failed to load audio: {e}")
            messagebox.showerror("Load Error", f"Generation complete but failed to load audio:\n{e}")
            
            # Re-enable UI anyway
            self.input_panel.set_enabled(True)
            self.output_panel.set_generating(False)
    
    def _generation_failed(self, error_message: str):
        """Handle generation failure"""
        logger.error(f"TTS generation failed: {error_message}")
        self._log(f"[ERROR] Generation failed: {error_message}")
        
        # Re-enable UI
        self.input_panel.set_enabled(True)
        self.output_panel.set_generating(False)
        
        self.progress_var.set(0)
        self.progress_text_var.set("Generation failed")
        
        messagebox.showerror("Generation Failed", f"TTS generation failed:\n{error_message}")
    
    def cleanup(self):
        """Cleanup resources when workspace is destroyed"""
        # Stop any running generation
        if self.generation_thread and self.generation_thread.is_alive():
            logger.warning("Generation thread still running during cleanup")
        
        # Unload TTS model
        if self.tts_wrapper:
            self.tts_wrapper.unload_model()
        
        logger.info("TTS workspace cleaned up")
