"""
Voice Revolver AI - Tkinter UI
Uses threading.Thread for background processing (NOT QThread - avoids PyTorch conflicts)
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path
from datetime import datetime
import traceback

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_revolver_core.application.voice_replacement_service import VoiceReplacementService
from voice_revolver_core.application.project_service import ProjectService
from voice_revolver_core.infrastructure.compute_controller import ComputeController
from voice_revolver_core.infrastructure.model_manager import ModelManager


class VoiceRevolverApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Revolver AI - Local Voice Replacement")
        self.root.geometry("800x700")
        
        # State
        self.original_file = None
        self.reference_file = None
        self.output_file = None
        self.processing = False
        self.processing_thread = None
        
        # Build UI first (so log() method works)
        self._build_ui()
        
        # Initialize services
        self.log("Initializing Voice Revolver AI...")
        
        # Setup app data path
        self.app_data_path = self._get_app_data_path()
        self.log(f"App data path: {self.app_data_path}")
        
        self.compute_controller = ComputeController()
        self.model_manager = ModelManager(self.app_data_path / "models")
        self.project_service = ProjectService()
        
        # Detect hardware
        self.device = self._detect_device()
        self.log(f"Device detected: {self.device.upper()}")
        
        # Update device dropdown
        self.device_var.set(self.device)
        
        # Preload AI libraries
        self._preload_libraries()
        
    def _detect_device(self):
        """Detect available compute device"""
        try:
            has_gpu = self.compute_controller.has_gpu  # Property, not method
            if has_gpu:
                return "cuda"
            else:
                return "cpu"
        except Exception as e:
            self.log(f"Device detection warning: {e}")
            return "cpu"
    
    def _get_app_data_path(self):
        """Get application data directory path"""
        if sys.platform == "win32":
            base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".local" / "share"
        
        app_data = base / "VoiceRevolverAI"
        app_data.mkdir(parents=True, exist_ok=True)
        return app_data
    
    def _preload_libraries(self):
        """Preload AI libraries to avoid first-time delays"""
        def preload():
            try:
                self.log("Preloading AI libraries (this may take a moment)...")
                import torch
                import torchaudio
                self.log("✓ PyTorch loaded")
                
                try:
                    from openvoice.api import ToneColorConverter
                    self.log("✓ OpenVoice loaded")
                except Exception as e:
                    self.log(f"⚠ OpenVoice preload warning: {e}")
                
                try:
                    from demucs.pretrained import get_model
                    self.log("✓ Demucs loaded")
                except Exception as e:
                    self.log(f"⚠ Demucs preload warning: {e}")
                
                self.log(f"Ready! Using device: {self.device.upper()}")
                self.start_btn.config(state="normal")
                
            except Exception as e:
                self.log(f"❌ Preload error: {e}")
                self.log(traceback.format_exc())
        
        # Run in background thread
        thread = threading.Thread(target=preload, daemon=True)
        thread.start()
    
    def _build_ui(self):
        """Build the UI"""
        # Main container
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Voice Revolver AI", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # File Selection Section
        file_frame = ttk.LabelFrame(main_frame, text="Audio Files", padding="10")
        file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Original file
        ttk.Label(file_frame, text="Original Song:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.original_label = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.original_label.grid(row=0, column=1, sticky=tk.W, padx=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_original).grid(row=0, column=2, padx=5)
        
        # Reference file
        ttk.Label(file_frame, text="Reference Voice:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.reference_label = ttk.Label(file_frame, text="No file selected", foreground="gray")
        self.reference_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        ttk.Button(file_frame, text="Browse...", command=self._select_reference).grid(row=1, column=2, padx=5)
        
        file_frame.columnconfigure(1, weight=1)
        
        # Settings Section
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Output format
        ttk.Label(settings_frame, text="Output Format:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="wav")
        format_combo = ttk.Combobox(settings_frame, textvariable=self.format_var, 
                                     values=["wav", "mp3", "flac"], state="readonly", width=10)
        format_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Device selection
        ttk.Label(settings_frame, text="Device:").grid(row=0, column=2, sticky=tk.W, padx=(20, 0), pady=5)
        self.device_var = tk.StringVar(value="cpu")  # Default, will be updated after detection
        device_combo = ttk.Combobox(settings_frame, textvariable=self.device_var,
                                     values=["cpu", "cuda"], state="readonly", width=10)
        device_combo.grid(row=0, column=3, sticky=tk.W, padx=5)
        
        # Pitch adjustment
        ttk.Label(settings_frame, text="Pitch Shift:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.pitch_var = tk.IntVar(value=0)
        pitch_scale = ttk.Scale(settings_frame, from_=-12, to=12, variable=self.pitch_var, 
                                orient=tk.HORIZONTAL, length=150)
        pitch_scale.grid(row=1, column=1, sticky=tk.W, padx=5)
        self.pitch_label = ttk.Label(settings_frame, text="0 semitones")
        self.pitch_label.grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=5)
        pitch_scale.config(command=lambda v: self.pitch_label.config(text=f"{int(float(v))} semitones"))
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="green")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        progress_frame.columnconfigure(0, weight=1)
        
        # Log Section
        log_frame = ttk.LabelFrame(main_frame, text="Log", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, state="disabled", wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Buttons Section
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=10)
        
        self.start_btn = ttk.Button(button_frame, text="Start Processing", command=self._start_processing, 
                                     state="disabled")
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.export_btn = ttk.Button(button_frame, text="Export Result", command=self._export_result, 
                                      state="disabled")
        self.export_btn.grid(row=0, column=1, padx=5)
        
        self.cancel_btn = ttk.Button(button_frame, text="Cancel", command=self._cancel_processing, 
                                      state="disabled")
        self.cancel_btn.grid(row=0, column=2, padx=5)
        
        # Configure grid weights
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
    
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}\n"
        
        self.log_text.config(state="normal")
        self.log_text.insert(tk.END, log_message)
        self.log_text.see(tk.END)
        self.log_text.config(state="disabled")
        
        # Also print to console
        print(log_message.strip())
    
    def _select_original(self):
        """Select original audio file"""
        file_path = filedialog.askopenfilename(
            title="Select Original Song",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.original_file = file_path
            filename = Path(file_path).name
            self.original_label.config(text=filename, foreground="black")
            self.log(f"Original file: {filename}")
            self._check_ready()
    
    def _select_reference(self):
        """Select reference voice file"""
        file_path = filedialog.askopenfilename(
            title="Select Reference Voice",
            filetypes=[
                ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.reference_file = file_path
            filename = Path(file_path).name
            self.reference_label.config(text=filename, foreground="black")
            self.log(f"Reference file: {filename}")
            self._check_ready()
    
    def _check_ready(self):
        """Check if ready to start processing"""
        if self.original_file and self.reference_file and not self.processing:
            self.start_btn.config(state="normal")
    
    def _update_progress(self, percentage, stage):
        """Update progress bar and status"""
        self.progress_bar["value"] = percentage
        self.status_label.config(text=stage)
        self.root.update_idletasks()
    
    def _start_processing(self):
        """Start processing in background thread"""
        if not self.original_file or not self.reference_file:
            messagebox.showwarning("Missing Files", "Please select both audio files")
            return
        
        self.processing = True
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.export_btn.config(state="disabled")
        self.progress_bar["value"] = 0
        
        self.log("=" * 60)
        self.log("Starting voice replacement processing...")
        self.log(f"Original: {Path(self.original_file).name}")
        self.log(f"Reference: {Path(self.reference_file).name}")
        self.log(f"Device: {self.device_var.get().upper()}")
        self.log("=" * 60)
        
        # Start processing in separate thread
        self.processing_thread = threading.Thread(target=self._process, daemon=False)
        self.processing_thread.start()
    
    def _process(self):
        """Processing logic (runs in background thread)"""
        try:
            # Create service
            device = self.device_var.get()
            output_format = self.format_var.get()
            
            service = VoiceReplacementService(
                model_manager=self.model_manager,
                device=device,
                output_format=output_format
            )
            
            # Progress callback
            def progress_callback(percentage, stage):
                self.root.after(0, self._update_progress, percentage, stage)
                self.root.after(0, self.log, f"[{int(percentage)}%] {stage}")
            
            # Process
            self._update_progress(0, "Initializing...")
            result = service.process(
                original_audio_path=self.original_file,
                reference_voice_path=self.reference_file,
                progress_callback=progress_callback
            )
            
            if result.get("success"):
                self.output_file = result.get("output_path")
                self.root.after(0, self._processing_complete)
            else:
                error = result.get("error", "Unknown error")
                self.root.after(0, self._processing_failed, error)
                
        except Exception as e:
            error_msg = f"{str(e)}\n{traceback.format_exc()}"
            self.root.after(0, self._processing_failed, error_msg)
    
    def _processing_complete(self):
        """Called when processing completes successfully"""
        self.processing = False
        self.progress_bar["value"] = 100
        self.status_label.config(text="✓ Complete!", foreground="green")
        self.log("=" * 60)
        self.log("✓ Processing complete!")
        self.log(f"Output: {self.output_file}")
        self.log("=" * 60)
        
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.export_btn.config(state="normal")
        
        messagebox.showinfo("Success", "Voice replacement complete!\nClick 'Export Result' to save.")
    
    def _processing_failed(self, error):
        """Called when processing fails"""
        self.processing = False
        self.progress_bar["value"] = 0
        self.status_label.config(text="✗ Failed", foreground="red")
        self.log("=" * 60)
        self.log(f"✗ Processing failed: {error}")
        self.log("=" * 60)
        
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        
        messagebox.showerror("Processing Failed", f"Error:\n{error}")
    
    def _cancel_processing(self):
        """Cancel processing"""
        if self.processing:
            self.log("Cancelling processing...")
            self.processing = False
            self.cancel_btn.config(state="disabled")
            # Note: actual thread cancellation would require more complex implementation
    
    def _export_result(self):
        """Export the result file"""
        if not self.output_file or not os.path.exists(self.output_file):
            messagebox.showwarning("No Result", "No output file available to export")
            return
        
        # Suggest filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = f"voice_revolver_{timestamp}.{self.format_var.get()}"
        
        save_path = filedialog.asksaveasfilename(
            title="Export Result",
            defaultextension=f".{self.format_var.get()}",
            initialfile=default_name,
            filetypes=[
                ("Audio Files", f"*.{self.format_var.get()}"),
                ("All Files", "*.*")
            ]
        )
        
        if save_path:
            try:
                import shutil
                shutil.copy(self.output_file, save_path)
                self.log(f"✓ Exported to: {save_path}")
                messagebox.showinfo("Export Complete", f"File saved to:\n{save_path}")
            except Exception as e:
                self.log(f"✗ Export failed: {e}")
                messagebox.showerror("Export Failed", f"Error:\n{e}")


def main():
    """Main entry point"""
    # Check Python version
    import sys
    if sys.version_info[:2] != (3, 11):
        print(f"⚠ WARNING: Python 3.11.x required, you are using {sys.version}")
        print("   PyTorch may not work correctly with other versions!")
    
    root = tk.Tk()
    app = VoiceRevolverApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
