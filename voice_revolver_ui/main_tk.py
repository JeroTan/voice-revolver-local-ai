"""
Voice Revolver AI - Tkinter UI
Uses threading.Thread for background processing (NOT QThread - avoids PyTorch conflicts)

Flow:
1. StartupDialog - Device selection (GPU/CPU)
2. LoadingDialog - Model download/initialization
3. MainWindow - Main application
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import sys
import os
from pathlib import Path
from datetime import datetime
import traceback
import logging
try:
    import pygame.mixer as mixer
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Warning: pygame not available, audio preview disabled")

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from voice_revolver_core.application.voice_replacement_service import VoiceReplacementService
from voice_revolver_core.application.project_service import ProjectService
from voice_revolver_core.infrastructure.compute_controller import ComputeController
from voice_revolver_core.infrastructure.model_manager import ModelManager
from voice_revolver_core.infrastructure.ffmpeg_checker import FFmpegChecker
from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
# from voice_revolver_core.infrastructure.openvoice_wrapper import OpenVoiceWrapper  # Legacy - kept for reference
from voice_revolver_core.infrastructure.chatterbox_wrapper import ChatterBoxWrapper
from voice_revolver_core.infrastructure.audio_mixer import AudioMixer
from voice_revolver_core.infrastructure.format_converter import FormatConverter
from voice_revolver_core.domain.file_manager import FileManager
from voice_revolver_core.domain.progress_tracker import ProgressTracker
from voice_revolver_core.domain.base import VoiceConversionParams


class StartupDialog:
    """Device selection dialog"""
    
    def __init__(self):
        self.selected_device = "cpu"
        self.result = None
        
        self.window = tk.Tk()
        self.window.title("Voice Revolver AI - Setup")
        self.window.geometry("500x500")
        self.window.resizable(False, False)
        
        self._build_ui()
        
        # Detect hardware after UI is built
        self.window.after(100, self._detect_hardware)
    
    def _build_ui(self):
        """Build startup UI"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Voice Revolver AI", font=("Arial", 16, "bold"))
        title.pack(pady=(0, 10))
        
        subtitle = ttk.Label(main_frame, text="Local Voice Replacement", font=("Arial", 10))
        subtitle.pack(pady=(0, 20))
        
        # System Info
        info_frame = ttk.LabelFrame(main_frame, text="System Information", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.gpu_label = ttk.Label(info_frame, text="GPU: Detecting...")
        self.gpu_label.pack(anchor=tk.W, pady=2)
        
        self.cpu_label = ttk.Label(info_frame, text="CPU: Available")
        self.cpu_label.pack(anchor=tk.W, pady=2)
        
        # Device Selection
        select_frame = ttk.LabelFrame(main_frame, text="Select Processing Device", padding="10")
        select_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.device_selection = tk.StringVar(value="cpu")
        
        self.gpu_radio = ttk.Radiobutton(select_frame, text="GPU (Detecting...)", 
                                         variable=self.device_selection, value="cuda",
                                         command=lambda: self._select_device("cuda"), state="disabled")
        self.gpu_radio.pack(anchor=tk.W, pady=5)
        
        self.cpu_radio = ttk.Radiobutton(select_frame, text="CPU", 
                                         variable=self.device_selection, value="cpu",
                                         command=lambda: self._select_device("cpu"))
        self.cpu_radio.pack(anchor=tk.W, pady=5)
        
        self.device_info = ttk.Label(select_frame, text="", foreground="gray")
        self.device_info.pack(pady=5)
        
        # Note
        note = ttk.Label(main_frame, text="Note: GPU is much faster but requires NVIDIA GPU with CUDA.", 
                        foreground="gray", font=("Arial", 9), wraplength=450)
        note.pack(pady=(10, 20))
        
        # Continue button
        self.continue_btn = ttk.Button(main_frame, text="Continue", command=self._continue, 
                                       state="disabled", width=20)
        self.continue_btn.pack(pady=10)
    
    def _detect_hardware(self):
        """Detect GPU availability"""
        try:
            import torch
            has_cuda = torch.cuda.is_available()
            
            if has_cuda:
                gpu_name = torch.cuda.get_device_name(0)
                self.gpu_label.config(text=f"GPU: {gpu_name}")
                self.gpu_radio.config(text="GPU (Recommended)", state="normal")
                self._select_device("cuda")  # Default to GPU
            else:
                self.gpu_label.config(text="GPU: Not detected")
                self.gpu_radio.config(text="GPU (May not work)", state="normal")
                self._select_device("cpu")
        except Exception as e:
            self.gpu_label.config(text="GPU: Detection failed")
            self.gpu_radio.config(text="GPU (Detection failed)", state="normal")
            self._select_device("cpu")
    
    def _select_device(self, device):
        """Handle device selection"""
        self.selected_device = device
        self.device_selection.set(device)
        
        if device == "cuda":
            self.device_info.config(text="✓ Using GPU for faster processing")
        else:
            self.device_info.config(text="✓ Using CPU (slower but works on any computer)")
        
        self.continue_btn.config(state="normal")
    
    def _continue(self):
        """Continue to loading"""
        self.result = "accepted"
        self.window.quit()
        self.window.destroy()
    
    def show(self):
        """Show dialog and wait"""
        self.window.mainloop()
        return self.result


class LoadingDialog:
    """Model loading/download dialog"""
    
    def __init__(self, device, app_data_path):
        self.device = device
        self.app_data_path = app_data_path
        self.success = False
        self.error_message = ""
        
        self.window = tk.Tk()
        self.window.title("Voice Revolver AI - Loading")
        self.window.geometry("450x250")
        self.window.resizable(False, False)
        
        # Prevent closing
        self.window.protocol("WM_DELETE_WINDOW", lambda: None)
        
        self._build_ui()
        
        # Start loading in background thread
        self.window.after(500, self._start_loading)
    
    def _build_ui(self):
        """Build loading UI"""
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title = ttk.Label(main_frame, text="Setting up Voice Revolver AI", font=("Arial", 14, "bold"))
        title.pack(pady=(0, 20))
        
        # Status
        self.status_label = ttk.Label(main_frame, text="Initializing...", font=("Arial", 10))
        self.status_label.pack(pady=5)
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(main_frame, mode="determinate", length=400)
        self.progress_bar.pack(pady=10)
        
        # Detail
        self.detail_label = ttk.Label(main_frame, text="", foreground="gray", font=("Arial", 9))
        self.detail_label.pack(pady=5)
        
        # Device info
        device_text = f"Using device: {'GPU' if self.device == 'cuda' else 'CPU'}"
        device_label = ttk.Label(main_frame, text=device_text, foreground="gray", font=("Arial", 9))
        device_label.pack(side=tk.BOTTOM)
    
    def update_progress(self, percentage, status, detail=""):
        """Update progress"""
        self.progress_bar["value"] = percentage
        self.status_label.config(text=status)
        self.detail_label.config(text=detail)
        self.window.update_idletasks()
    
    def _start_loading(self):
        """Start loading process in background thread"""
        thread = threading.Thread(target=self._load_dependencies, daemon=False)
        thread.start()
    
    def _load_dependencies(self):
        """Load dependencies (runs in background thread)"""
        try:
            # Step 1: FFmpeg
            self.window.after(0, self.update_progress, 0, "Checking FFmpeg...", "Looking for FFmpeg installation")
            
            ffmpeg_checker = FFmpegChecker(self.app_data_path)
            ffmpeg_checker.ensure_available()
            
            self.window.after(0, self.update_progress, 20, "FFmpeg ready", "Using FFmpeg for audio processing")
            
            # Step 2: Models
            self.window.after(0, self.update_progress, 30, "Checking AI models...", "Looking for cached models")
            
            model_manager = ModelManager(self.app_data_path / "models")
            cache_status = model_manager.check_cache()
            
            if not all(cache_status.values()):
                self.window.after(0, self.update_progress, 40, "Downloading OpenVoice models...", "This may take a few minutes")
                
                def download_callback(model, prog):
                    percentage = 40 + int(prog * 50)
                    self.window.after(0, self.update_progress, percentage, f"Downloading {model}...", f"Progress: {int(prog * 100)}%")
                
                model_manager.download_all_models(download_callback)
            
            self.window.after(0, self.update_progress, 90, "Loading complete!", "All dependencies ready")
            
            self.success = True
            self.window.after(1000, self._finish)
            
        except Exception as e:
            self.success = False
            self.error_message = str(e)
            self.window.after(0, self._show_error)
    
    def _show_error(self):
        """Show error and exit"""
        messagebox.showerror("Error", f"Failed to load dependencies:\n{self.error_message}")
        self.window.quit()
        self.window.destroy()
    
    def _finish(self):
        """Finish loading"""
        self.window.quit()
        self.window.destroy()
    
    def show(self):
        """Show dialog and wait"""
        self.window.mainloop()
        return self.success


class VoiceRevolverApp:
    def __init__(self, root, device, app_data_path):
        self.root = root
        self.root.title("Voice Revolver AI - Local Voice Replacement")
        self.root.geometry("900x850")  # Larger window for 5 preview players + volume control + tau control
        
        # Configuration
        self.device = device
        self.app_data_path = app_data_path
        
        # State
        self.original_file = None
        self.reference_file = None
        self.output_file = None
        self.processing = False
        
        # OpenVoice-specific params (kept for compatibility, not used with ChatterBox)
        self.style_var = tk.StringVar(value="default")
        self.tau_var = tk.DoubleVar(value=0.3)
        
        # Processed file paths for 5 previews
        self.original_audio_path = None
        self.original_vocals_path = None  # NEW: Original vocals before conversion
        self.vocals_converted_path = None
        self.final_mix_path = None
        self.instrumental_path = None
        
        # Audio preview states (5 separate players)
        self.preview_states = {
            'original': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'original_vocals': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'vocals': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'final': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'instrumental': {'loaded': False, 'playing': False, 'length': 0, 'timer': None}
        }
        self.current_track = None  # Which track is currently playing
        
        # Initialize pygame mixer for audio playback
        if PYGAME_AVAILABLE:
            try:
                mixer.init()
            except Exception as e:
                self.log(f"Warning: Could not initialize audio player: {e}")
        self.processing_thread = None
        
        # Build UI first (so log() method works)
        self._build_ui()
        self._create_log_window()  # Create separate log window
        
        # Initialize services
        self.log("Initializing Voice Revolver AI...")
        self.log(f"Device: {self.device.upper()}")
        self.log(f"App data path: {self.app_data_path}")
        
        self.compute_controller = ComputeController()
        self.model_manager = ModelManager(self.app_data_path / "models")
        self.ffmpeg_checker = FFmpegChecker(self.app_data_path)
        
        # Ensure ffmpeg is available (was configured in main(), but double-check)
        ffmpeg_success, ffmpeg_error = self.ffmpeg_checker.ensure_available()
        if not ffmpeg_success:
            self.log(f"⚠ FFmpeg warning: {ffmpeg_error}")
        
        self.file_manager = FileManager(self.app_data_path / "temp")
        self.progress_tracker = ProgressTracker()
        self.project_service = ProjectService()
        
        # Update device dropdown
        self.device_var.set(self.device)
        
        self.log("Ready to process audio!")
        self.start_btn.config(state="normal" if self.original_file and self.reference_file else "disabled")
    
    def _build_ui(self):
        """Build the UI"""
        # Menu bar
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Logs", command=self._show_log_window)
        
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
        
        # =================================================================
        # OpenVoice-Specific Controls (Disabled for ChatterBox)
        # These controls are only used with OpenVoice wrapper
        # ChatterBox VC has simpler API without style/conversion strength
        # Uncomment if switching back to OpenVoice
        # =================================================================
        
        # # Voice style (OpenVoice only)
        # ttk.Label(settings_frame, text="Voice Style:").grid(row=2, column=0, sticky=tk.W, pady=5)
        # self.style_var = tk.StringVar(value="default")
        # style_combo = ttk.Combobox(settings_frame, textvariable=self.style_var,
        #                             values=["default", "american", "british", "australian", "indian"],
        #                             state="readonly", width=15)
        # style_combo.grid(row=2, column=1, sticky=tk.W, padx=5)
        # ttk.Label(settings_frame, text="Accent variant to apply", foreground="gray").grid(
        #     row=2, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        # # Voice conversion strength / tau (OpenVoice only)
        # tau_frame = ttk.Frame(settings_frame)
        # tau_frame.grid(row=3, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=5)
        
        # ttk.Label(tau_frame, text="Conversion Strength:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        # ttk.Label(tau_frame, text="Close to original", foreground="gray", font=("Segoe UI", 8)).grid(
        #     row=0, column=1, sticky=tk.E, padx=5)
        
        # self.tau_var = tk.DoubleVar(value=0.3)
        # tau_scale = ttk.Scale(tau_frame, from_=0.0, to=1.0, variable=self.tau_var,
        #                      orient=tk.HORIZONTAL, length=150, command=self._on_tau_change)
        # tau_scale.grid(row=0, column=2, sticky=tk.W, padx=5)
        
        # ttk.Label(tau_frame, text="Close to reference", foreground="gray", font=("Segoe UI", 8)).grid(
        #     row=0, column=3, sticky=tk.W, padx=5)
        
        # # Precise tau input
        # self.tau_entry = ttk.Entry(tau_frame, width=6)
        # self.tau_entry.insert(0, "0.30")
        # self.tau_entry.grid(row=0, column=4, sticky=tk.W, padx=5)
        # self.tau_entry.bind('<Return>', self._on_tau_entry_change)
        # self.tau_entry.bind('<FocusOut>', self._on_tau_entry_change)
        
        # # Reset button
        # reset_btn = ttk.Button(tau_frame, text="↺", width=3, command=self._reset_tau)
        # reset_btn.grid(row=0, column=5, sticky=tk.W, padx=(0, 5))
        
        # =================================================================
        # End OpenVoice-Specific Controls
        # =================================================================
        
        # Use vocal only checkbox
        self.vocal_only_var = tk.BooleanVar(value=False)
        vocal_only_check = ttk.Checkbutton(settings_frame, text="Use Vocal Only", 
                                           variable=self.vocal_only_var)
        vocal_only_check.grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        ttk.Label(settings_frame, text="Use the separated vocal instead of the whole song", 
                 foreground="gray", font=("Segoe UI", 8)).grid(
            row=4, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        # Progress Section
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="10")
        progress_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=400)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="green")
        self.status_label.grid(row=1, column=0, sticky=tk.W)
        
        progress_frame.columnconfigure(0, weight=1)
        
        # Four Preview Players Section
        preview_frame = ttk.LabelFrame(main_frame, text="Preview & Export", padding="10")
        preview_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Volume control at the top
        volume_frame = ttk.Frame(preview_frame)
        volume_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(volume_frame, text="Volume:", font=("Arial", 9)).grid(row=0, column=0, padx=(0, 5))
        
        self.volume_var = tk.DoubleVar(value=0.7)  # Default 70%
        volume_slider = ttk.Scale(volume_frame, from_=0, to=1, variable=self.volume_var,
                                 orient=tk.HORIZONTAL, length=150, command=self._on_volume_change)
        volume_slider.grid(row=0, column=1, padx=5)
        
        self.volume_label = ttk.Label(volume_frame, text="70%", width=5)
        self.volume_label.grid(row=0, column=2, padx=5)
        
        self.preview_controls = {}
        preview_configs = [
            ('original', 'Original Audio', 0),
            ('original_vocals', 'Original Vocal Only', 1),
            ('vocals', 'Vocal That Reference Only', 2),
            ('final', 'Final Remix', 3),
            ('instrumental', 'Instrumental', 4)
        ]
        
        for track_id, track_name, row in preview_configs:
            # Track frame (offset row by 1 because volume control is at row 0)
            track_frame = ttk.Frame(preview_frame)
            track_frame.grid(row=row+1, column=0, sticky=(tk.W, tk.E), pady=5)
            
            # Track name label
            ttk.Label(track_frame, text=track_name, font=("Arial", 9, "bold"), width=30).grid(row=0, column=0, sticky=tk.W)
            
            # Play/Pause button
            play_btn = ttk.Button(track_frame, text="▶", width=3, 
                                  command=lambda t=track_id: self._toggle_playback(t), state="disabled")
            play_btn.grid(row=0, column=1, padx=2)
            
            # Stop button
            stop_btn = ttk.Button(track_frame, text="■", width=3,
                                  command=lambda t=track_id: self._stop_playback(t), state="disabled")
            stop_btn.grid(row=0, column=2, padx=2)
            
            # Time label
            time_label = ttk.Label(track_frame, text="00:00/00:00", width=12)
            time_label.grid(row=0, column=3, padx=5)
            
            # Timeline slider
            timeline_var = tk.DoubleVar(value=0)
            timeline = ttk.Scale(track_frame, from_=0, to=100, variable=timeline_var,
                                orient=tk.HORIZONTAL, length=200, command=lambda v, t=track_id: self._on_seek(t, v))
            timeline.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=5)
            timeline.config(state="disabled")
            
            # Export button
            export_btn = ttk.Button(track_frame, text="Export", width=8,
                                   command=lambda t=track_id: self._export_track(t), state="disabled")
            export_btn.grid(row=0, column=5, padx=2)
            
            track_frame.columnconfigure(4, weight=1)
            
            # Store controls
            self.preview_controls[track_id] = {
                'play_btn': play_btn,
                'stop_btn': stop_btn,
                'time_label': time_label,
                'timeline_var': timeline_var,
                'timeline': timeline,
                'export_btn': export_btn
            }
        
        preview_frame.columnconfigure(0, weight=1)
        
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
    
    def _create_log_window(self):
        """Create separate log window"""
        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Voice Revolver AI - Logs")
        self.log_window.geometry("700x850")
        
        # Position to the right of main window
        self.root.update_idletasks()
        main_x = self.root.winfo_x()
        main_y = self.root.winfo_y()
        main_width = self.root.winfo_width()
        self.log_window.geometry(f"+{main_x + main_width + 10}+{main_y}")
        
        # Log text widget  
        log_frame = ttk.Frame(self.log_window, padding="10")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=20, state="disabled", 
                                                   wrap=tk.WORD, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Clear button
        clear_btn = ttk.Button(log_frame, text="Clear Logs", command=self._clear_logs)
        clear_btn.pack(pady=5)
        
        # Handle window close
        self.log_window.protocol("WM_DELETE_WINDOW", self._hide_log_window)
    
    def _hide_log_window(self):
        """Hide log window instead of destroying it"""
        self.log_window.withdraw()
    
    def _show_log_window(self):
        """Show log window if hidden"""
        if hasattr(self, 'log_window'):
            self.log_window.deiconify()
            self.log_window.lift()
    
    def _clear_logs(self):
        """Clear the log window"""
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state="disabled")
    
    def log(self, message):
        """Add message to separate log window"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        
        # Write to separate log window
        if hasattr(self, 'log_text'):
            self.log_text.config(state="normal")
            self.log_text.insert(tk.END, log_message + "\n")
            self.log_text.see(tk.END)
            self.log_text.config(state="disabled")
        
        # Also print to console
        print(log_message)
    
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
            # Get settings
            device = self.device_var.get()
            output_format = self.format_var.get()
            pitch = self.pitch_var.get()
            
            self.log("Initializing processing components...")
            
            # FFmpeg is already configured globally in main(), just verify it's available
            ffmpeg_dir = self.ffmpeg_checker.get_ffmpeg_dir()
            if not ffmpeg_dir:
                raise RuntimeError("FFmpeg not available")
            
            self.log(f"FFmpeg: {ffmpeg_dir}")
            
            # Initialize infrastructure wrappers
            demucs_wrapper = DemucsWrapper(device)
            
            # ChatterBox VC - Better quality than OpenVoice
            chatterbox_wrapper = ChatterBoxWrapper(device)
            
            # OpenVoice (legacy - uncomment to use instead of ChatterBox):
            # openvoice_wrapper = OpenVoiceWrapper(
            #     self.model_manager.openvoice_path,
            #     device
            # )
            
            audio_mixer = AudioMixer(ffmpeg_dir)
            
            # Create voice replacement service
            service = VoiceReplacementService(
                demucs_wrapper,
                chatterbox_wrapper,  # Using ChatterBox instead of openvoice_wrapper
                None,  # voice_transformer (not implemented yet)
                audio_mixer,
                self.file_manager,
                self.progress_tracker
            )
            
            # Create voice params
            # NOTE: style and tau are ignored by ChatterBox (only used by OpenVoice)
            voice_params = VoiceConversionParams(
                pitch=pitch,
                style=self.style_var.get(),     # Ignored by ChatterBox
                style_strength=1.0,              # Ignored by ChatterBox
                tau=self.tau_var.get()          # Ignored by ChatterBox
            )
            
            # Progress callback - receives (percentage, stage) args
            def progress_callback(percentage, stage):
                self.root.after(0, self._update_progress, percentage, stage)
                self.root.after(0, self.log, f"[{int(percentage)}%] {stage}")
            
            # Process
            self._update_progress(0, "Starting...")
            output_path, error_code, message = service.process(
                original_audio_path=Path(self.original_file),
                reference_voice_path=Path(self.reference_file),
                voice_params=voice_params,
                output_format=output_format,
                vocal_only=self.vocal_only_var.get(),
                progress_callback=progress_callback
            )
            
            if output_path:
                self.output_file = str(output_path)
                self.root.after(0, self._processing_complete)
            else:
                error = f"{error_code}: {message}" if error_code else message
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
        
        # Load all 4 audio files for preview
        self._load_all_previews()
        
        messagebox.showinfo("Success", "Voice replacement complete!\\nUse the Preview section to play each track.")
    
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
    
    # ========== Audio Preview Methods (4-Track System) ==========
    
    def _load_all_previews(self):
        """Load all 5 audio files for preview after processing"""
        if not PYGAME_AVAILABLE:
            self.log("Audio preview not available (pygame not installed)")
            return
        
        # Determine file paths from processing output
        temp_dir = self.app_data_path / "temp" / "temp"
        
        # 1. Original audio (user input)
        self.original_audio_path = self.original_file
        
        # 2. Original vocals only (before conversion)
        original_vocals_path = temp_dir / "original_vocals.wav"
        if original_vocals_path.exists():
            self.original_vocals_path = str(original_vocals_path)
        
        # 3. Converted vocals only
        vocals_path = temp_dir / "converted_vocals.wav"
        if vocals_path.exists():
            self.vocals_converted_path = str(vocals_path)
        
        # 4. Final mix (ALWAYS load the full remix, regardless of vocal_only setting)
        final_mix_path = temp_dir / "mixed_output.wav"
        if final_mix_path.exists():
            self.final_mix_path = str(final_mix_path)
        else:
            # Fallback to output file if mixed_output doesn't exist
            self.final_mix_path = self.output_file
        
        # 5. Instrumental (need to mix stems excluding vocals)
        self._create_instrumental_track(temp_dir)
        
        # Load each track
        tracks = [
            ('original', self.original_audio_path, "Original Audio"),
            ('original_vocals', self.original_vocals_path, "Original Vocals"),
            ('vocals', self.vocals_converted_path, "Converted Vocals"),
            ('final', self.final_mix_path, "Final Mix"),
            ('instrumental', self.instrumental_path, "Instrumental")
        ]
        
        for track_id, file_path, name in tracks:
            if file_path and os.path.exists(file_path):
                self._load_single_preview(track_id, file_path, name)
            else:
                self.log(f"⚠ {name} not available for preview")
    
    def _create_instrumental_track(self, temp_dir):
        """Create instrumental-only track by mixing non-vocal stems"""
        try:
            from pydub import AudioSegment
            
            stems = ['drums', 'bass', 'other']
            instrumental = None
            
            for stem in stems:
                stem_path = temp_dir / f"original_{stem}.wav"
                if stem_path.exists():
                    stem_audio = AudioSegment.from_file(str(stem_path))
                    if instrumental is None:
                        instrumental = stem_audio
                    else:
                        instrumental = instrumental.overlay(stem_audio)
            
            if instrumental:
                instrumental_path = temp_dir / "instrumental_only.wav"
                instrumental.export(str(instrumental_path), format="wav")
                self.instrumental_path = str(instrumental_path)
                self.log("✓ Created instrumental track")
            else:
                self.log("⚠ Could not create instrumental track")
        except Exception as e:
            self.log(f"⚠ Error creating instrumental: {e}")
    
    def _load_single_preview(self, track_id, file_path, track_name):
        """Load a single audio file for preview"""
        try:
            # Load and get length using pygame.mixer.Sound
            sound = mixer.Sound(file_path)
            length = sound.get_length()
            
            # Update state
            self.preview_states[track_id]['loaded'] = True
            self.preview_states[track_id]['length'] = length
            
            # Enable controls
            controls = self.preview_controls[track_id]
            controls['play_btn'].config(state="normal")
            controls['stop_btn'].config(state="normal")
            controls['timeline'].config(state="normal", to=length)
            controls['export_btn'].config(state="normal")
            
            # Update time display
            total_min = int(length // 60)
            total_sec = int(length % 60)
            controls['time_label'].config(text=f"00:00/{total_min:02d}:{total_sec:02d}")
            
            self.log(f"✓ Loaded {track_name} for preview")
        except Exception as e:
            self.log(f"⚠ Could not load {track_name}: {e}")
    
    def _toggle_playback(self, track_id):
        """Toggle play/pause for a specific track"""
        if not self.preview_states[track_id]['loaded']:
            return
        
        # Stop any other playing track
        if self.current_track and self.current_track != track_id:
            self._stop_playback(self.current_track)
        
        controls = self.preview_controls[track_id]
        state = self.preview_states[track_id]
        
        if state['playing']:
            # Pause
            mixer.music.pause()
            state['playing'] = False
            controls['play_btn'].config(text="▶")
            if state['timer']:
                self.root.after_cancel(state['timer'])
                state['timer'] = None
        else:
            # Play
            # Get file path
            file_path = self._get_track_path(track_id)
            if not file_path:
                return
            
            # Load and play
            try:
                mixer.music.load(file_path)
                mixer.music.set_volume(self.volume_var.get())  # Apply current volume
                mixer.music.play()
                state['playing'] = True
                self.current_track = track_id
                controls['play_btn'].config(text="⏸")
                self._update_playback_time(track_id)
            except Exception as e:
                self.log(f"⚠ Playback error: {e}")
    
    def _on_volume_change(self, value):
        """Handle volume slider changes"""
        try:
            volume = float(value)
            # Update volume label
            self.volume_label.config(text=f"{int(volume * 100)}%")
            # Apply to currently playing track
            if hasattr(self, 'current_track') and self.current_track:
                if self.preview_states[self.current_track]['playing']:
                    mixer.music.set_volume(volume)
        except Exception as e:
            self.log(f"⚠ Volume change error: {e}")
    
    def _on_tau_change(self, value):
        """Handle tau slider changes - update entry field"""
        try:
            tau = float(value)
            self.tau_entry.delete(0, tk.END)
            self.tau_entry.insert(0, f"{tau:.2f}")
        except Exception as e:
            self.log(f"⚠ Tau slider error: {e}")
    
    def _on_tau_entry_change(self, event):
        """Handle tau entry field changes - update slider"""
        try:
            tau = float(self.tau_entry.get())
            # Clamp to valid range
            tau = max(0.0, min(1.0, tau))
            self.tau_var.set(tau)
            # Update entry to show clamped value
            self.tau_entry.delete(0, tk.END)
            self.tau_entry.insert(0, f"{tau:.2f}")
        except ValueError:
            # Invalid input, reset to slider value
            self.tau_entry.delete(0, tk.END)
            self.tau_entry.insert(0, f"{self.tau_var.get():.2f}")
        except Exception as e:
            self.log(f"⚠ Tau entry error: {e}")
    
    def _reset_tau(self):
        """Reset tau (conversion strength) to default value 0.3"""
        self.tau_var.set(0.3)
        self.tau_entry.delete(0, tk.END)
        self.tau_entry.insert(0, "0.30")
    
    def _stop_playback(self, track_id):
        """Stop playback and reset for a specific track"""
        if not self.preview_states[track_id]['loaded']:
            return
        
        controls = self.preview_controls[track_id]
        state = self.preview_states[track_id]
        
        mixer.music.stop()
        state['playing'] = False
        controls['play_btn'].config(text="▶")
        controls['timeline_var'].set(0)
        
        if state['timer']:
            self.root.after_cancel(state['timer'])
            state['timer'] = None
        
        # Reset time display
        length = state['length']
        total_min = int(length // 60)
        total_sec = int(length % 60)
        controls['time_label'].config(text=f"00:00/{total_min:02d}:{total_sec:02d}")
        
        if self.current_track == track_id:
            self.current_track = None
    
    def _on_seek(self, track_id, value):
        """Handle timeline slider seeking for a specific track"""
        state = self.preview_states[track_id]
        if not state['loaded'] or not state['playing']:
            return
        
        try:
            position = float(value)
            mixer.music.set_pos(position)
        except Exception as e:
            self.log(f"⚠ Seek error: {e}")
    
    def _update_playback_time(self, track_id):
        """Update time display and timeline while playing"""
        state = self.preview_states[track_id]
        if not state['playing']:
            return
        
        controls = self.preview_controls[track_id]
        
        try:
            # Track position manually
            current_pos = controls['timeline_var'].get()
            current_pos += 0.1  # Update every 100ms
            
            if current_pos >= state['length']:
                # Reached end
                self._stop_playback(track_id)
                return
            
            controls['timeline_var'].set(current_pos)
            
            # Update time label
            current_min = int(current_pos // 60)
            current_sec = int(current_pos % 60)
            total_min = int(state['length'] // 60)
            total_sec = int(state['length'] % 60)
            controls['time_label'].config(text=f"{current_min:02d}:{current_sec:02d}/{total_min:02d}:{total_sec:02d}")
            
            # Schedule next update
            state['timer'] = self.root.after(100, self._update_playback_time, track_id)
        except Exception as e:
            self.log(f"⚠ Playback update error: {e}")
    
    def _get_track_path(self, track_id):
        """Get file path for a specific track"""
        paths = {
            'original': self.original_audio_path,
            'original_vocals': self.original_vocals_path,
            'vocals': self.vocals_converted_path,
            'final': self.final_mix_path,
            'instrumental': self.instrumental_path
        }
        return paths.get(track_id)
    
    def _export_track(self, track_id):
        """Export a specific track to chosen format"""
        file_path = self._get_track_path(track_id)
        if not file_path or not os.path.exists(file_path):
            messagebox.showwarning("No File", "This track is not available for export")
            return
        
        # Track names for filename
        track_names = {
            'original': 'original',
            'original_vocals': 'original_vocals',
            'vocals': 'vocals_converted',
            'final': 'final_mix',
            'instrumental': 'instrumental'
        }
        
        # Suggest filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        track_name = track_names.get(track_id, 'audio')
        default_name = f"voice_revolver_{track_name}_{timestamp}.{self.format_var.get()}"
        
        save_path = filedialog.asksaveasfilename(
            title=f"Export {track_name.replace('_', ' ').title()}",
            defaultextension=f".{self.format_var.get()}",
            initialfile=default_name,
            filetypes=[
                ("WAV", "*.wav"),
                ("MP3", "*.mp3"),
                ("FLAC", "*.flac"),
                ("All Files", "*.*")
            ]
        )
        
        if save_path:
            try:
                # Convert if needed
                if str(file_path).endswith('.wav') and not save_path.endswith('.wav'):
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(file_path)
                    audio.export(save_path, format=save_path.split('.')[-1])
                else:
                    import shutil
                    shutil.copy(file_path, save_path)
                
                self.log(f"✓ Exported {track_name} to: {save_path}")
                messagebox.showinfo("Export Complete", f"File saved to:\\n{save_path}")
            except Exception as e:
                self.log(f"✗ Export failed: {e}")
                messagebox.showerror("Export Failed", f"Error:\\n{e}")


def main():
    """Main entry point"""
    # Check Python version
    if sys.version_info[:2] != (3, 11):
        print(f"⚠ WARNING: Python 3.11.x required, you are using {sys.version}")
        print("   PyTorch may not work correctly with other versions!")
    
    # Preload PyTorch to avoid DLL loading issues
    try:
        print("⏳ Preloading PyTorch...")
        import torch
        _ = torch.tensor([1.0])
        print(f"✓ PyTorch {torch.__version__} loaded")
    except Exception as e:
        print(f"⚠ PyTorch preload warning: {e}")
    
    # Get app data path
    if sys.platform == "win32":
        base = Path(os.environ.get('LOCALAPPDATA', Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".local" / "share"
    app_data_path = base / "VoiceRevolverAI"
    app_data_path.mkdir(parents=True, exist_ok=True)
    
    # Configure FFmpeg EARLY (before any pydub/AI imports)
    print("⏳ Configuring FFmpeg...")
    try:
        # Use static-ffmpeg to get bundled FFmpeg binaries (no external downloads needed)
        from static_ffmpeg import run
        
        ffmpeg_exe, ffprobe_exe = run.get_or_fetch_platform_executables_else_raise()
        
        # Configure pydub GLOBALLY before any imports use it
        from pydub import AudioSegment
        
        AudioSegment.converter = ffmpeg_exe
        AudioSegment.ffmpeg = ffmpeg_exe
        AudioSegment.ffprobe = ffprobe_exe
        
        # Add to PATH for subprocess calls (critical for OpenVoice)
        ffmpeg_dir = str(Path(ffmpeg_exe).parent)
        os.environ['PATH'] = ffmpeg_dir + os.pathsep + os.environ.get('PATH', '')
        os.environ['FFMPEG_BINARY'] = ffmpeg_exe
        os.environ['FFPROBE_BINARY'] = ffprobe_exe
        
        print(f"✓ FFmpeg configured: {ffmpeg_exe}")
    except Exception as e:
        print(f"⚠ FFmpeg configuration warning: {e}")
        print(f"   FFmpeg may not be available, processing will fail")
    
    # Preload AI libraries (AFTER ffmpeg is configured)
    try:
        print("⏳ Preloading AI libraries...")
        from openvoice.api import ToneColorConverter
        from demucs.pretrained import get_model
        import torchaudio
        print("✓ AI libraries loaded")
    except Exception as e:
        print(f"⚠ AI library preload warning: {e}")
    
    # Setup logging
    log_file = app_data_path / "logs" / "app.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    logger.info("Voice Revolver AI starting...")
    
    # Step 1: Startup Dialog - Device selection
    startup = StartupDialog()
    result = startup.show()
    
    if result != "accepted":
        logger.info("User cancelled startup")
        sys.exit(0)
    
    device = startup.selected_device
    logger.info(f"User selected device: {device}")
    
    # Step 2: Loading Dialog - Download models/FFmpeg
    loading = LoadingDialog(device, app_data_path)
    success = loading.show()
    
    if not success:
        logger.error("Loading failed")
        sys.exit(1)
    
    logger.info("Loading complete, showing main window...")
    
    # Step 3: Main Window
    root = tk.Tk()
    app = VoiceRevolverApp(root, device, app_data_path)
    root.mainloop()
    
    logger.info("Application closed")


if __name__ == "__main__":
    main()
