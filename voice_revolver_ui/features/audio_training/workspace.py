"""Audio Training workspace - Main workspace for training RVC voice models."""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional, Callable, List
import threading
import logging
import shutil
import zipfile
import re

from voice_revolver_core.domain.file_manager import FileManager

from .components import InputPanel, OutputPanel

logger = logging.getLogger(__name__)


class AudioTrainingWorkspace(ttk.Frame):
    """Main workspace for training RVC voice models from audio samples."""
    
    def __init__(
        self,
        parent,
        root,
        app_data_path: Path,
        device: str,
        log_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """Initialize the Audio Training workspace.
        
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
        
        # Training state
        self.is_training = False
        self.training_thread: Optional[threading.Thread] = None
        self.training_cancelled = False
        self.output_zip_path: Optional[Path] = None
        
        # UI state
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_text_var = tk.StringVar(value="Ready")
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the workspace UI."""
        # Configure grid - two columns (50/50 split)
        self.columnconfigure(0, weight=1, uniform="equal", minsize=350)  # Input panel (50%)
        self.columnconfigure(1, weight=1, uniform="equal", minsize=400)  # Output panel (50%)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)  # Progress bar
        
        # Input panel (left)
        self.input_panel = InputPanel(
            self,
            on_train=self._on_train_clicked,
            on_cancel=self._on_cancel_clicked,
            initial_device=self.device
        )
        self.input_panel.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        # Output panel (right)
        self.output_panel = OutputPanel(
            self,
            on_export=self._on_export_clicked
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
        """Log a message."""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)
    
    def _update_progress(self, percent: float, message: str):
        """Update progress bar and label (thread-safe)."""
        self.progress_var.set(percent)
        self.progress_text_var.set(message)
        self.output_panel.update_progress(percent, message)
    
    def _on_train_clicked(self):
        """Handle Start Training button click."""
        if self.is_training:
            return
        
        # Get inputs from input panel
        model_name = self.input_panel.get_model_name()
        audio_files = self.input_panel.get_audio_files()
        params = self.input_panel.get_training_params()
        
        # Validate inputs
        if not model_name:
            messagebox.showwarning("Input Required", "Please enter a model name.")
            return
        
        if not audio_files:
            messagebox.showwarning("Input Required", "Please add at least one audio file.")
            return
        
        total_duration = self.input_panel.get_total_duration_minutes()
        if total_duration < 5:
            result = messagebox.askyesno(
                "Low Audio Duration",
                f"You have only {total_duration:.1f} minutes of audio.\n"
                "Recommended minimum is 10 minutes.\n\n"
                "Continue anyway?"
            )
            if not result:
                return
        
        # Start training in background thread
        self.is_training = True
        self.training_cancelled = False
        self.output_zip_path = None
        
        # Update UI state
        self.input_panel.set_training_state(True)
        self.output_panel.set_training_state(True)
        self.output_panel.reset_progress()
        
        self._log(f"Starting training for model: {model_name}")
        self._log(f"Audio files: {len(audio_files)}, Total duration: {total_duration:.1f} min")
        self._log(f"Parameters: Epochs={params['epochs']}, Batch={params['batch_size']}, "
                  f"Sample Rate={params['sample_rate']}")
        
        # Start training thread
        self.training_thread = threading.Thread(
            target=self._run_training,
            args=(model_name, audio_files, params),
            daemon=True
        )
        self.training_thread.start()
    
    def _run_training(self, model_name: str, audio_files: List[Path], params: dict):
        """Run the training pipeline in background thread."""
        try:
            # Import training wrapper
            from voice_revolver_core.infrastructure.rvc_training_wrapper import RVCTrainingWrapper
            
            def progress_callback(percent: float, message: str):
                if not self.training_cancelled:
                    self.root.after(0, self._update_progress, percent * 100, message)
            
            # Create wrapper and run training - use device from params (user selection)
            wrapper = RVCTrainingWrapper(
                model_name=model_name,
                app_data_path=self.app_data_path,
                device=params.get("device", self.device)
            )
            
            output_zip, error = wrapper.train(
                audio_files=audio_files,
                params=params,
                progress_callback=progress_callback,
                cancel_check=lambda: self.training_cancelled
            )
            
            if self.training_cancelled:
                self.root.after(0, self._on_training_cancelled)
            elif error:
                self.root.after(0, self._on_training_error, error)
            else:
                self.output_zip_path = output_zip
                self.root.after(0, self._on_training_complete, output_zip)
                
        except Exception as e:
            logger.exception("Training failed with exception")
            self.root.after(0, self._on_training_error, str(e))
    
    def _on_training_complete(self, output_zip: Path):
        """Handle training completion."""
        self.is_training = False
        self.input_panel.set_training_state(False)
        self.output_panel.set_training_state(False)
        self.output_panel.set_training_complete(output_zip)
        
        self._update_progress(100, "Training complete!")
        self._log(f"Training complete! Model saved to: {output_zip}")
        
        messagebox.showinfo(
            "Training Complete",
            f"Model trained successfully!\n\n"
            f"Output: {output_zip.name}\n\n"
            f"Click 'Export' to save to your desired location."
        )
    
    def _on_training_error(self, error: str):
        """Handle training error."""
        self.is_training = False
        self.input_panel.set_training_state(False)
        self.output_panel.set_training_state(False)
        self.output_panel.set_training_failed(error)
        
        self._update_progress(0, f"Error: {error[:50]}...")
        self._log(f"Training error: {error}")
        
        messagebox.showerror("Training Failed", f"Training failed:\n\n{error}")
    
    def _on_training_cancelled(self):
        """Handle training cancellation."""
        self.is_training = False
        self.input_panel.set_training_state(False)
        self.output_panel.set_training_state(False)
        
        self._update_progress(0, "Training cancelled")
        self._log("Training cancelled by user")
    
    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        if not self.is_training:
            return
        
        result = messagebox.askyesno(
            "Cancel Training",
            "Are you sure you want to cancel training?\n\n"
            "Progress will be lost."
        )
        
        if result:
            self.training_cancelled = True
            self._log("Cancelling training...")
    
    def _on_export_clicked(self):
        """Handle Export button click."""
        if not self.output_zip_path or not self.output_zip_path.exists():
            messagebox.showwarning("No Output", "No trained model available to export.")
            return
        
        # Ask for save location
        output_path = filedialog.asksaveasfilename(
            defaultextension=".zip",
            filetypes=[("ZIP Archive", "*.zip")],
            initialfile=self.output_zip_path.name,
            title="Save Model"
        )
        
        if not output_path:
            return
        
        try:
            # Copy to destination
            shutil.copy2(self.output_zip_path, output_path)
            self._log(f"Model exported to: {output_path}")
            
            messagebox.showinfo(
                "Export Complete",
                f"Model exported successfully!\n\n{output_path}"
            )
        except Exception as e:
            logger.exception("Export failed")
            messagebox.showerror("Export Failed", f"Failed to export model:\n\n{e}")
    
    def destroy(self):
        """Clean up resources before destroying."""
        if self.is_training:
            self.training_cancelled = True
        super().destroy()
