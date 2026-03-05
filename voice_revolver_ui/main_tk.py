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
from typing import Tuple
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
from voice_revolver_core.infrastructure.chatterbox_vc_wrapper import ChatterBoxVCWrapper
from voice_revolver_core.infrastructure.audio_mixer import AudioMixer
from voice_revolver_core.infrastructure.format_converter import FormatConverter
from voice_revolver_core.infrastructure.resemble_enhance_wrapper import is_resemble_enhance_available, enhance_vocals
from voice_revolver_core.domain.file_manager import FileManager
from voice_revolver_core.domain.progress_tracker import ProgressTracker
from voice_revolver_core.domain.base import VoiceConversionParams, AudioStems

# UI Components
from voice_revolver_ui.features.startup_dialog import StartupDialog
from voice_revolver_ui.features.loading_dialog import LoadingDialog
from voice_revolver_ui.features.menu_bar import MenuBar
from voice_revolver_ui.features.audio_separation import AudioSeparationWorkspace
from voice_revolver_ui.features.text_to_speech import TextToSpeechWorkspace
from voice_revolver_ui.features.voice_cloning import VoiceCloningWorkspace
from voice_revolver_ui.features.voice_enhancement import VoiceEnhancementWorkspace
from voice_revolver_ui.features.track_merger import TrackMergerWorkspace
from voice_revolver_ui.features.audio_training import AudioTrainingWorkspace
from voice_revolver_ui.components.labeled_slider import LabeledSlider

logger = logging.getLogger(__name__)

# Workspace identifier for temp directory organization
CURRENT_WORKSPACE = "vocal_changer"


class VoiceRevolverApp:
    def __init__(self, root, device, app_data_path):
        self.root = root
        self.root.title("Voice Revolver AI - Local Voice Replacement")
        
        # Maximize window for Phase 2 two-column layout
        self.root.state('zoomed')  # Windows maximized
        
        # Set minimum size for two-column layout
        self.root.minsize(1200, 700)  # Wide enough for left + right columns
        
        # Configuration
        self.device = device
        self.app_data_path = app_data_path
        
        # State
        self.original_file = None
        self.reference_file = None
        self.output_file = None
        self.processing = False
        self.separation_complete = False  # Phase 2: Track if vocal separation is complete
        
        # Reference mode: 'audio' or 'model' (RVC zip)
        self.reference_mode = tk.StringVar(value="audio")
        
        # Separation model: 'demucs' (balanced) or 'mdx' (best vocals)
        self.separation_model_var = tk.StringVar(value="demucs")
        
        # Gender selection (manual) for RVC model mode
        self.original_gender_var = tk.StringVar(value="male")  # Original voice gender
        self.model_gender_var = tk.StringVar(value="male")  # Model gender (default: male, consistent with radio button order)
        
        # Pitch shift threshold controls (for adaptive shifting sensitivity)
        self.threshold_low_var = tk.DoubleVar(value=180.0)  # Hz - Low threshold (aggressive shift below this)
        self.threshold_mid_var = tk.DoubleVar(value=230.0)  # Hz - Mid threshold (moderate shift)
        self.threshold_high_var = tk.DoubleVar(value=280.0)  # Hz - High threshold (minimal shift above this)
        
        # OpenVoice-specific params (kept for compatibility, not used with ChatterBox)
        self.style_var = tk.StringVar(value="default")
        self.tau_var = tk.DoubleVar(value=0.3)
        
        # Processed file paths for 6 previews
        self.original_audio_path = None
        self.original_vocals_path = None  # NEW: Original vocals before conversion
        self.reference_denoised_path = None  # NEW: Denoised reference voice
        self.vocals_converted_path = None
        self.final_mix_path = None
        self.instrumental_path = None
        self.edited_vocals_path = None  # Path to vocals after spectrum editor edits
        
        # Audio preview states (7 separate players - added original_vocals_edited)
        self.preview_states = {
            'original': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'original_vocals': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'original_vocals_edited': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
            'reference_denoised': {'loaded': False, 'playing': False, 'length': 0, 'timer': None},
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
        self.separation_thread = None  # Phase 2: Separation background thread
        
        # Build UI first (so log() method works)
        self._build_ui()
        self._create_log_window()  # Create separate log window (hidden by default)
        self.log_window.withdraw()  # Start hidden - toggle with F12
        self.log_hidden = True
        
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
            self.log(f"[WARNING] FFmpeg warning: {ffmpeg_error}")
        
        self.file_manager = FileManager(self.app_data_path)
        self.progress_tracker = ProgressTracker()
        self.project_service = ProjectService()
        
        # Update device dropdown
        self.device_var.set(self.device)
        
        self.log("Ready to process audio!")
        self.start_btn.config(state="normal" if self.original_file and self.reference_file else "disabled")
    
    def _build_ui(self):
        """Build the UI"""
        # Menu bar
        self.menu_bar = MenuBar(self.root, on_toggle_logs=self._toggle_log_window, log_callback=self.log)
        
        # Workspace container (holds all workspaces)
        self.workspace_container = ttk.Frame(self.root)
        self.workspace_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container with responsive grid (VOCAL CHANGER WORKSPACE)
        main_frame = ttk.Frame(self.workspace_container, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.workspace_container.columnconfigure(0, weight=1)
        self.workspace_container.rowconfigure(0, weight=1)
        
        # Store reference to vocal_changer workspace
        self.vocal_changer_frame = main_frame
        
        # Phase 2: Two-column layout
        # Column 0: Controls (left, 40%)
        # Column 1: Spectrum Editor + Previews (right, 60%)
        main_frame.columnconfigure(0, weight=2, minsize=500)  # Left column
        main_frame.columnconfigure(1, weight=3, minsize=700)  # Right column
        main_frame.rowconfigure(0, weight=1)  # Main content expands
        main_frame.rowconfigure(1, weight=0)  # Progress bar (fixed height)
        
        # === LEFT COLUMN: Controls ===
        # Create left container (divided into top and bottom)
        left_container = ttk.Frame(main_frame)
        left_container.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        left_container.rowconfigure(0, weight=1)  # Top section
        left_container.rowconfigure(1, weight=1)  # Bottom section
        left_container.columnconfigure(0, weight=1)
        
        # === RIGHT COLUMN: Spectrum Editor + Previews ===
        # Create right container (divided into top and bottom)
        right_container = ttk.Frame(main_frame)
        right_container.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        right_container.rowconfigure(0, weight=2)  # Spectrum editor (60%)
        right_container.rowconfigure(1, weight=1)  # Preview players (40%)
        right_container.columnconfigure(0, weight=1)
        
        # TOP-LEFT: Original Audio & Separation
        left_top_frame = ttk.LabelFrame(left_container, text="Original Audio & Separation", padding="10")
        left_top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 5))
        
        # BOTTOM-LEFT: Reference & Processing
        left_bottom_frame = ttk.LabelFrame(left_container, text="Reference Voice & Processing", padding="10")
        left_bottom_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # TOP-RIGHT: Spectrum Editor
        right_top_frame = ttk.LabelFrame(right_container, text="Vocal Editor (Run Separation First)", padding="10")
        right_top_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S),  pady=(0, 5))
        
        # BOTTOM-RIGHT: Preview & Export
        right_bottom_frame = ttk.LabelFrame(right_container, text="Audio Preview & Export", padding="10")
        right_bottom_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(5, 0))
        
        # ===================================================================
        # LEFT-TOP: Original Audio Section
        # ===================================================================
        
        # Original file selection
        file_row = 0
        ttk.Label(left_top_frame, text="Original Song:").grid(row=file_row, column=0, sticky=tk.W, pady=5)
        self.original_label = ttk.Label(left_top_frame, text="No file selected", foreground="gray")
        self.original_label.grid(row=file_row, column=1, sticky=(tk.W, tk.E), padx=5)
        ttk.Button(left_top_frame, text="Browse...", command=self._select_original).grid(row=file_row, column=2, padx=5)
        left_top_frame.columnconfigure(1, weight=1)
        
        # Separation model selection
        file_row += 1
        ttk.Label(left_top_frame, text="Separation Model:").grid(row=file_row, column=0, sticky=tk.W, pady=5)
        separation_model_combo = ttk.Combobox(left_top_frame, textvariable=self.separation_model_var,
                                              values=["demucs", "mdx"], state="readonly", width=15)
        separation_model_combo.grid(row=file_row, column=1, sticky=tk.W, padx=5)
        
        # Separation model hint
        file_row += 1
        ttk.Label(left_top_frame, text="(Demucs=balanced, MDX=best vocal isolation)", 
                 foreground="gray", font=("Segoe UI", 8)).grid(
            row=file_row, column=0, columnspan=3, sticky=tk.W, padx=(20, 0))
        
        # Device selection
        file_row += 1
        ttk.Label(left_top_frame, text="Device:").grid(row=file_row, column=0, sticky=tk.W, pady=5)
        self.device_var = tk.StringVar(value="cpu")  # Default, will be updated
        device_combo = ttk.Combobox(left_top_frame, textvariable=self.device_var,
                                     values=["cpu", "cuda"], state="readonly", width=15)
        device_combo.grid(row=file_row, column=1, sticky=tk.W, padx=5)
        
        # Pitch adjustment
        file_row += 1
        ttk.Label(left_top_frame, text="Pitch Shift:").grid(row=file_row, column=0, sticky=tk.W, pady=5)
        self.pitch_var = tk.IntVar(value=0)
        pitch_scale = ttk.Scale(left_top_frame, from_=-12, to=12, variable=self.pitch_var, 
                                orient=tk.HORIZONTAL, length=150)
        pitch_scale.grid(row=file_row, column=1, sticky=(tk.W, tk.E), padx=5)
        self.pitch_label = ttk.Label(left_top_frame, text="0 semitones")
        self.pitch_label.grid(row=file_row, column=2, sticky=tk.W, padx=5)
        pitch_scale.config(command=lambda v: self.pitch_label.config(text=f"{int(float(v))} semitones"))
        
        # Gender alignment checkbox
        file_row += 1
        self.use_gender_alignment_var = tk.BooleanVar(value=False)
        gender_alignment_check = ttk.Checkbutton(left_top_frame, text="Use Gender Alignment", 
                                              variable=self.use_gender_alignment_var,
                                              command=self._on_gender_alignment_change)
        gender_alignment_check.grid(row=file_row, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Improve Vocals checkbox (Resemble Enhance - Phase 2.7)
        file_row += 1
        self.improve_vocals_var = tk.BooleanVar(value=False)
        self.improve_vocals_check = ttk.Checkbutton(left_top_frame, text="Improve Vocals (may take time)", 
                                              variable=self.improve_vocals_var)
        self.improve_vocals_check.grid(row=file_row, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Check if resemble-enhance is available and disable checkbox if not
        if not is_resemble_enhance_available():
            self.improve_vocals_check.config(state='disabled')
            # Create tooltip label
            tooltip_label = ttk.Label(left_top_frame, 
                                     text="(Requires venv-enhance - see docs/venv-enhance-setup.md)",
                                     foreground="gray", 
                                     font=("Segoe UI", 8))
            tooltip_label.grid(row=file_row, column=0, columnspan=3, sticky=tk.W, padx=(20, 0))
        
        # Vocal Match selection (Phase 2: Target gender to match the original vocal to)
        file_row += 1
        self.orig_gender_frame = ttk.Frame(left_top_frame)
        self.orig_gender_frame.grid(row=file_row, column=0, columnspan=3, sticky=tk.W, pady=5)
        self.orig_gender_frame.grid_remove()  # Hidden initially
        
        ttk.Label(self.orig_gender_frame, text="Vocal Match:", font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(self.orig_gender_frame, text="Male", variable=self.original_gender_var, 
                       value="male").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(self.orig_gender_frame, text="Female", variable=self.original_gender_var, 
                       value="female").pack(side=tk.LEFT, padx=5)
        ttk.Label(self.orig_gender_frame, text="(Will match audio to selected type after separation)", 
                 foreground="gray", font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=10)
        
        # Threshold controls (shown if gender alignment enabled)
        file_row += 1
        self.threshold_frame = ttk.LabelFrame(left_top_frame, text="Shift Sensitivity (Hz)", padding=5)
        self.threshold_frame.grid(row=file_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        self.threshold_frame.grid_remove()  # Hidden initially
        
        ttk.Label(self.threshold_frame, text="Lower = more shift | Higher = subtle", 
                 foreground="gray", font=("Segoe UI", 8)).grid(row=0, column=0, columnspan=4, sticky=tk.W, pady=2)
        
        # Low Threshold
        ttk.Label(self.threshold_frame, text="Low:", width=5).grid(row=1, column=0, sticky=tk.W)
        ttk.Scale(self.threshold_frame, from_=100, to=250, variable=self.threshold_low_var,
                 orient=tk.HORIZONTAL, length=80, command=self._on_threshold_low_change).grid(row=1, column=1, padx=2)
        self.threshold_low_entry = ttk.Entry(self.threshold_frame, width=5)
        self.threshold_low_entry.insert(0, "180")
        self.threshold_low_entry.grid(row=1, column=2, padx=2)
        self.threshold_low_entry.bind('<Return>', self._on_threshold_low_entry)
        ttk.Button(self.threshold_frame, text="↺", width=2, command=lambda: self._reset_threshold('low')).grid(row=1, column=3, padx=2)
        
        # Mid Threshold
        ttk.Label(self.threshold_frame, text="Mid:", width=5).grid(row=2, column=0, sticky=tk.W)
        ttk.Scale(self.threshold_frame, from_=150, to=300, variable=self.threshold_mid_var,
                 orient=tk.HORIZONTAL, length=80, command=self._on_threshold_mid_change).grid(row=2, column=1, padx=2)
        self.threshold_mid_entry = ttk.Entry(self.threshold_frame, width=5)
        self.threshold_mid_entry.insert(0, "230")
        self.threshold_mid_entry.grid(row=2, column=2, padx=2)
        self.threshold_mid_entry.bind('<Return>', self._on_threshold_mid_entry)
        ttk.Button(self.threshold_frame, text="↺", width=2, command=lambda: self._reset_threshold('mid')).grid(row=2, column=3, padx=2)
        
        # High Threshold
        ttk.Label(self.threshold_frame, text="High:", width=5).grid(row=3, column=0, sticky=tk.W)
        ttk.Scale(self.threshold_frame, from_=200, to=350, variable=self.threshold_high_var,
                 orient=tk.HORIZONTAL, length=80, command=self._on_threshold_high_change).grid(row=3, column=1, padx=2)
        self.threshold_high_entry = ttk.Entry(self.threshold_frame, width=5)
        self.threshold_high_entry.insert(0, "280")
        self.threshold_high_entry.grid(row=3, column=2, padx=2)
        self.threshold_high_entry.bind('<Return>', self._on_threshold_high_entry)
        ttk.Button(self.threshold_frame, text="↺", width=2, command=lambda: self._reset_threshold('high')).grid(row=3, column=3, padx=2)
        
        # Run Separation button (NEW - Phase 2)
        file_row += 1
        self.separation_btn = ttk.Button(left_top_frame, text="Run Separation", 
                                        command=self._run_separation, state="disabled")
        self.separation_btn.grid(row=file_row, column=0, columnspan=3, pady=10)
        
        # ===================================================================
        # LEFT-BOTTOM: Reference & Processing Section
        # ===================================================================
        
        ref_row = 0
        # Reference file selection
        ttk.Label(left_bottom_frame, text="Reference Voice:").grid(row=ref_row, column=0, sticky=tk.W, pady=5)
        self.reference_label = ttk.Label(left_bottom_frame, text="No file selected", foreground="gray")
        self.reference_label.grid(row=ref_row, column=1, sticky=(tk.W, tk.E), padx=5)
        self.reference_browse_btn = ttk.Button(left_bottom_frame, text="Browse...", command=self._select_reference, state="disabled")
        self.reference_browse_btn.grid(row=ref_row, column=2, padx=5)
        left_bottom_frame.columnconfigure(1, weight=1)
        
        # Reference mode selector
        ref_row += 1
        mode_frame = ttk.Frame(left_bottom_frame)
        mode_frame.grid(row=ref_row, column=0, columnspan=3, sticky=tk.W, pady=5)
        ttk.Label(mode_frame, text="Reference Type:", foreground="gray", font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 10))
        self.ref_audio_radio = ttk.Radiobutton(mode_frame, text="Audio File", variable=self.reference_mode, 
                       value="audio", command=self._on_reference_mode_change, state="disabled")
        self.ref_audio_radio.pack(side=tk.LEFT, padx=5)
        self.ref_model_radio = ttk.Radiobutton(mode_frame, text="RVC Model (.zip)", variable=self.reference_mode, 
                       value="model", command=self._on_reference_mode_change, state="disabled")
        self.ref_model_radio.pack(side=tk.LEFT, padx=5)
        
        # RVC Parameters (shown only when RVC model mode is selected)
        ref_row += 1
        self.rvc_params_frame = ttk.LabelFrame(left_bottom_frame, text="RVC Parameters", padding=10)
        self.rvc_params_frame.grid(row=ref_row, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 5))
        self.rvc_params_frame.columnconfigure(0, weight=1)
        self.rvc_params_frame.grid_remove()  # Hidden by default
        
        param_row = 0
        
        # F0 Method dropdown
        f0_frame = ttk.Frame(self.rvc_params_frame)
        f0_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        f0_frame.columnconfigure(1, weight=1)
        
        ttk.Label(f0_frame, text="F0 Method:", width=15).grid(row=0, column=0, sticky=tk.W)
        self.f0_method_var = tk.StringVar(value="rmvpe")
        self.f0_method_combo = ttk.Combobox(
            f0_frame,
            textvariable=self.f0_method_var,
            values=["rmvpe", "harvest", "crepe", "pm"],
            state="readonly",
            width=12
        )
        self.f0_method_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        param_row += 1
        
        # F0 Method description
        f0_desc = ttk.Label(
            self.rvc_params_frame,
            text="Pitch extraction algorithm (rmvpe=best quality, harvest=stable, crepe=accurate)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        f0_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Pitch Shift slider
        self.pitch_shift_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Pitch Shift:",
            from_=-12,
            to=12,
            initial_value=0,
            value_format="{:.0f}",
            length=200
        )
        self.pitch_shift_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Pitch Shift description
        pitch_desc = ttk.Label(
            self.rvc_params_frame,
            text="Shift pitch up/down in semitones (-12 to +12)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        pitch_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Index Rate slider
        self.index_rate_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Index Rate:",
            from_=0.0,
            to=1.0,
            initial_value=0.75,
            value_format="{:.2f}",
            length=200
        )
        self.index_rate_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Index Rate description
        index_desc = ttk.Label(
            self.rvc_params_frame,
            text="Feature retrieval strength (higher=better timbre match, 0.75 recommended)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        index_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Protection slider
        self.protection_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Protection:",
            from_=0.0,
            to=0.5,
            initial_value=0.33,
            value_format="{:.2f}",
            length=200
        )
        self.protection_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Protection description
        protection_desc = ttk.Label(
            self.rvc_params_frame,
            text="Protect voiceless consonants (s, t, k sounds - prevents over-smoothing)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        protection_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Filter Radius slider
        self.filter_radius_slider = LabeledSlider(
            self.rvc_params_frame,
            label="Filter Radius:",
            from_=0,
            to=7,
            initial_value=3,
            value_format="{:.0f}",
            length=200
        )
        self.filter_radius_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Filter Radius description
        filter_desc = ttk.Label(
            self.rvc_params_frame,
            text="Median filtering for pitch curve (higher=smoother, 3 recommended)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        filter_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # RMS Mix Rate slider
        self.rms_mix_rate_slider = LabeledSlider(
            self.rvc_params_frame,
            label="RMS Mix Rate:",
            from_=0.0,
            to=1.0,
            initial_value=0.25,
            value_format="{:.2f}",
            length=200
        )
        self.rms_mix_rate_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # RMS Mix Rate description
        rms_desc = ttk.Label(
            self.rvc_params_frame,
            text="Volume envelope mix (0=use original volume, 1=use model volume)",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        rms_desc.grid(row=param_row, column=0, sticky=tk.W, padx=(15, 0), pady=(0, 5))
        param_row += 1
        
        # Reset to Defaults button
        reset_btn = ttk.Button(
            self.rvc_params_frame,
            text="Reset All to Defaults",
            command=self._reset_rvc_params
        )
        reset_btn.grid(row=param_row, column=0, sticky=tk.W, pady=(10, 0))
        
        # Output format
        ref_row += 1
        ttk.Label(left_bottom_frame, text="Output Format:").grid(row=ref_row, column=0, sticky=tk.W, pady=5)
        self.format_var = tk.StringVar(value="wav")
        self.format_combo = ttk.Combobox(left_bottom_frame, textvariable=self.format_var, 
                                     values=["wav", "mp3", "flac"], state="disabled", width=15)
        self.format_combo.grid(row=ref_row, column=1, sticky=tk.W, padx=5)
        
        # Use vocal only checkbox
        ref_row += 1
        self.vocal_only_var = tk.BooleanVar(value=True)
        self.vocal_only_check = ttk.Checkbutton(left_bottom_frame, text="Use Original Vocal Only", 
                                           variable=self.vocal_only_var, state="disabled")
        self.vocal_only_check.grid(row=ref_row, column=0, columnspan=3, sticky=tk.W, pady=5)
        
        # Processing buttons
        ref_row += 1
        button_container = ttk.Frame(left_bottom_frame)
        button_container.grid(row=ref_row, column=0, columnspan=3, pady=15)
        
        self.start_btn = ttk.Button(button_container, text="Start Processing", command=self._start_processing, 
                                     state="disabled")
        self.start_btn.grid(row=0, column=0, padx=5)
        
        self.export_btn = ttk.Button(button_container, text="Export Result", command=self._export_result, 
                                      state="disabled")
        self.export_btn.grid(row=0, column=1, padx=5)
        
        self.cancel_btn = ttk.Button(button_container, text="Cancel", command=self._cancel_processing, 
                                      state="disabled")
        self.cancel_btn.grid(row=0, column=2, padx=5)
        
        # ===================================================================
        # RIGHT-TOP: Spectrum Editor
        # ===================================================================
        
        # Import spectrum editor
        from voice_revolver_ui.features.vocal_changer.spectrum_editor import SpectrumEditor
        
        self.spectrum_editor = SpectrumEditor(right_top_frame)
        self.spectrum_editor.pack(fill=tk.BOTH, expand=True)
        
        # Set callback for Apply Changes button
        self.spectrum_editor.set_apply_changes_callback(self._apply_curve_changes)
        
        # Initially disable spectrum editor (enable after separation)
        self.separation_complete = False
        self._enable_spectrum_editor(False)
        
        # ===================================================================
        # RIGHT-BOTTOM: Preview & Export
        # ===================================================================
        
        # Volume slider on the right side (vertical) - PACK FIRST!
        volume_container = ttk.Frame(right_bottom_frame)
        volume_container.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        ttk.Label(volume_container, text="Vol", font=("Arial", 8)).pack(pady=(0, 5))
        
        self.preview_volume_var = tk.DoubleVar(value=100)
        volume_slider = ttk.Scale(volume_container, from_=100, to=0, variable=self.preview_volume_var,
                                 orient=tk.VERTICAL, length=120, command=self._on_preview_volume_change)
        volume_slider.pack()
        
        volume_label = ttk.Label(volume_container, text="100%", font=("Arial", 8))
        volume_label.pack(pady=(5, 0))
        self.preview_volume_label = volume_label
        
        # Preview players container - PACK SECOND (fills remaining space)
        preview_container = ttk.Frame(right_bottom_frame)
        preview_container.pack(fill=tk.BOTH, expand=True)
        
        self.preview_controls = {}
        preview_configs = [
            ('original', 'Original Audio'),
            ('original_vocals', 'Original Vocals'),
            ('original_vocals_edited', 'Original Vocal (Edited)'),
            ('reference_denoised', 'Reference (Cleaned)'),
            ('vocals', 'Converted Vocals'),
            ('final', 'Final Mix'),
            ('instrumental', 'Instrumental')
        ]
        
        for idx, (track_id, track_name) in enumerate(preview_configs):
            # Track frame
            track_frame = ttk.Frame(preview_container)
            track_frame.grid(row=idx, column=0, sticky=(tk.W, tk.E), pady=3)
            
            # Track name label
            ttk.Label(track_frame, text=track_name, font=("Arial", 9), width=18).grid(row=0, column=0, sticky=tk.W)
            
            # Play/Pause button
            play_btn = ttk.Button(track_frame, text="▶", width=3, 
                                  command=lambda t=track_id: self._toggle_playback(t), state="disabled")
            play_btn.grid(row=0, column=1, padx=2)
            
            # Stop button
            stop_btn = ttk.Button(track_frame, text="■", width=3,
                                  command=lambda t=track_id: self._stop_playback(t), state="disabled")
            stop_btn.grid(row=0, column=2, padx=2)
            
            # Time label
            time_label = ttk.Label(track_frame, text="00:00/00:00", width=10)
            time_label.grid(row=0, column=3, padx=5)
            
            # Timeline slider
            timeline_var = tk.DoubleVar(value=0)
            timeline = ttk.Scale(track_frame, from_=0, to=100, variable=timeline_var,
                                orient=tk.HORIZONTAL, length=150, command=lambda v, t=track_id: self._on_seek(t, v))
            timeline.grid(row=0, column=4, sticky=(tk.W, tk.E), padx=5)
            timeline.config(state="disabled")
            
            # Export button
            export_btn = ttk.Button(track_frame, text="↓", width=3,
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
        
        preview_container.columnconfigure(0, weight=1)
        
        # ===================================================================
        # PROGRESS BAR (spans both columns)
        # ===================================================================
        
        progress_frame = ttk.Frame(main_frame)
        progress_frame.grid(row=1, column=0,  columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=800)
        self.progress_bar.pack(fill=tk.X, expand=True, padx=5, pady=2)
        
        self.status_label = ttk.Label(progress_frame, text="Ready", foreground="green")
        self.status_label.pack(pady=2)
        
        progress_frame.columnconfigure(0, weight=1)
        
        # Create Audio Separation workspace (hidden initially)
        self.audio_separation_workspace = AudioSeparationWorkspace(
            parent=self.workspace_container,
            root=self.root,
            app_data_path=self.app_data_path,
            device=self.device,
            log_callback=self.log
        )
        self.audio_separation_workspace.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.audio_separation_workspace.grid_remove()  # Hidden initially
        
        # Create Text-to-Speech workspace (hidden initially)
        self.tts_workspace = TextToSpeechWorkspace(
            parent=self.workspace_container,
            root=self.root,
            app_data_path=self.app_data_path,
            device=self.device,
            log_callback=self.log
        )
        self.tts_workspace.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.tts_workspace.grid_remove()  # Hidden initially
        
        # Create Voice Cloning workspace (hidden initially)
        self.voice_cloning_workspace = VoiceCloningWorkspace(
            parent=self.workspace_container,
            root=self.root,
            app_data_path=self.app_data_path,
            device=self.device,
            log_callback=self.log
        )
        self.voice_cloning_workspace.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.voice_cloning_workspace.grid_remove()  # Hidden initially
        
        # Create Voice Enhancement workspace (hidden initially)
        self.voice_enhancement_workspace = VoiceEnhancementWorkspace(
            parent=self.workspace_container,
            root=self.root,
            app_data_path=self.app_data_path,
            device=self.device,
            log_callback=self.log
        )
        self.voice_enhancement_workspace.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.voice_enhancement_workspace.grid_remove()  # Hidden initially
        
        # Create Track Merger workspace (hidden initially)
        self.track_merger_workspace = TrackMergerWorkspace(
            parent=self.workspace_container,
            root=self.root,
            app_data_path=self.app_data_path,
            device=self.device,
            log_callback=self.log
        )
        self.track_merger_workspace.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.track_merger_workspace.grid_remove()  # Hidden initially
        
        # Create Audio Training workspace (hidden initially)
        self.audio_training_workspace = AudioTrainingWorkspace(
            parent=self.workspace_container,
            root=self.root,
            app_data_path=self.app_data_path,
            device=self.device,
            log_callback=self.log
        )
        self.audio_training_workspace.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.audio_training_workspace.grid_remove()  # Hidden initially
        
        # Enable all workspaces in menu
        self.menu_bar.enable_workspace("vocal_changer", lambda: self._switch_workspace("vocal_changer"))
        self.menu_bar.enable_workspace("audio_separation", lambda: self._switch_workspace("audio_separation"))
        self.menu_bar.enable_workspace("text_to_speech", lambda: self._switch_workspace("text_to_speech"))
        self.menu_bar.enable_workspace("voice_cloning", lambda: self._switch_workspace("voice_cloning"))
        self.menu_bar.enable_workspace("voice_enhancement", lambda: self._switch_workspace("voice_enhancement"))
        self.menu_bar.enable_workspace("track_merger", lambda: self._switch_workspace("track_merger"))
        self.menu_bar.enable_workspace("audio_training", lambda: self._switch_workspace("audio_training"))
        
        # Set initial active workspace
        self.current_workspace = "vocal_changer"
        self.menu_bar.set_active_workspace("vocal_changer")
        
    # End of _build_ui
    
    def _switch_workspace(self, workspace_id):
        """Switch between workspaces.
        
        Args:
            workspace_id: ID of workspace to switch to ("vocal_changer", "audio_separation", or "text_to_speech")
        """
        # Stop any playing audio
        if PYGAME_AVAILABLE:
            try:
                mixer.music.stop()
            except:
                pass
        
        # Hide all workspaces
        self.vocal_changer_frame.grid_remove()
        self.audio_separation_workspace.grid_remove()
        self.tts_workspace.grid_remove()
        self.voice_cloning_workspace.grid_remove()
        self.voice_enhancement_workspace.grid_remove()
        self.track_merger_workspace.grid_remove()
        self.audio_training_workspace.grid_remove()
        
        # Show selected workspace
        if workspace_id == "audio_separation":
            self.audio_separation_workspace.grid()
            self.current_workspace = "audio_separation"
        elif workspace_id == "text_to_speech":
            self.tts_workspace.grid()
            self.current_workspace = "text_to_speech"
        elif workspace_id == "voice_cloning":
            self.voice_cloning_workspace.grid()
            self.current_workspace = "voice_cloning"
        elif workspace_id == "voice_enhancement":
            self.voice_enhancement_workspace.grid()
            self.current_workspace = "voice_enhancement"
        elif workspace_id == "track_merger":
            self.track_merger_workspace.grid()
            self.current_workspace = "track_merger"
        elif workspace_id == "audio_training":
            self.audio_training_workspace.grid()
            self.current_workspace = "audio_training"
        else:
            self.vocal_changer_frame.grid()
            self.current_workspace = "vocal_changer"
        
        # Update menu bar
        self.menu_bar.set_active_workspace(workspace_id)
        self.log(f"Switched to {workspace_id.replace('_', ' ').title()} workspace")
    
    def _enable_spectrum_editor(self, enable=True):
        """Enable or disable spectrum editor and update label"""
        if enable:
            # Find the label frame and update text
            for widget in self.spectrum_editor.master.winfo_children():
                if isinstance(widget, ttk.LabelFrame):
                    widget.config(text="Vocal Editor (Spectrum)")
            # Enable spectrum editor widgets
            self.spectrum_editor.set_enabled(True)
        else:
            # Update label
            for widget in self.spectrum_editor.master.winfo_children():
                if isinstance(widget, ttk.LabelFrame):
                    widget.config(text="Vocal Editor (Run Separation First)")
            # Disable spectrum editor widgets  
            self.spectrum_editor.set_enabled(False)
    
    def _run_separation(self):
        """Phase 2: Run vocal separation only (not full processing)"""
        if not self.original_file:
            messagebox.showwarning("No Audio", "Please select an original audio file first")
            return
        
        if self.processing:
            return
        
        # Disable separation button during processing
        self.separation_btn.config(state="disabled")
        self.processing = True
        
        # Clear previous separation if re-running
        self.separation_complete = False
        self._enable_spectrum_editor(False)
        
        self.log("="*50)
        self.log("Starting vocal separation...")
        self._update_progress(0, "Initializing...")
        
        # Run separation in background thread
        self.separation_thread = threading.Thread(target=self._separation_worker, daemon=True)
        self.separation_thread.start()
    
    def _separation_worker(self):
        """Background worker for vocal separation"""
        try:
            # Import required components
            from voice_revolver_core.infrastructure.demucs_wrapper import DemucsWrapper
            from voice_revolver_core.infrastructure.mdx_wrapper import MDXWrapper
            from voice_revolver_core.infrastructure.gender_detector import GenderDetector
            from voice_revolver_core.infrastructure.vocal_enhancer import VocalEnhancer
            
            # Progress callback for thread-safe UI updates
            def progress_cb(percentage, message):
                self.root.after(0, self._update_progress, percentage, message)
            
            # 1. Initialize stem separator based on selected model
            progress_cb(5, "Loading separation model...")
            
            separation_model = self.separation_model_var.get()
            if separation_model == "mdx":
                self.log("Using MDX separation (best vocal quality)")
                separator = MDXWrapper(device=self.device)
            else:  # demucs
                self.log("Using Demucs separation (balanced)")
                separator = DemucsWrapper(device=self.device)
            
            # 2. Run separation
            progress_cb(10, "Separating vocals from song...")
            self.log(f"Processing: {Path(self.original_file).name}")
            
            output_dir = self.file_manager.get_workspace_temp_dir(CURRENT_WORKSPACE) / "separation"
            
            # Clean up old separation files (except cached enhanced vocals from current file)
            if output_dir.exists():
                for wav_file in output_dir.glob("*.wav"):
                    # Keep enhanced vocals cache (they're cleared when new file is selected)
                    if wav_file.name == "vocals_enhanced.wav":
                        continue
                    try:
                        wav_file.unlink()
                    except Exception as e:
                        self.log(f"[WARNING] Could not delete {wav_file.name}: {e}")
                self.log("Cleaned up old separation files")
            
            output_dir.mkdir(exist_ok=True, parents=True)
            
            stems_dict, error = separator.separate(
                audio_path=Path(self.original_file),
                output_dir=output_dir
            )
            
            if error:
                raise RuntimeError(error)
            
            # Convert dict to AudioStems
            stems = AudioStems(
                vocals=stems_dict.get('vocals'),
                drums=stems_dict.get('drums'),
                bass=stems_dict.get('bass'),
                other=stems_dict.get('other'),
            )
            
            progress_cb(60, "Vocals separated successfully")
            self.log(f"[OK] Vocals extracted: {stems.vocals}")
            
            # Store separated vocals path
            self.original_vocals_path = stems.vocals
            
            # Store instrumental stems paths
            self.instrumental_path = output_dir / "instrumental.wav"
            if not self.instrumental_path.exists():
                # Combine non-vocal stems into instrumental using pydub
                try:
                    from pydub import AudioSegment
                    instrumental_stems = stems.get_instrumental()
                    if instrumental_stems:
                        # Load first stem
                        instrumental = None
                        for stem_name, stem_path in instrumental_stems.items():
                            if stem_path and stem_path.exists():
                                stem_audio = AudioSegment.from_file(str(stem_path))
                                if instrumental is None:
                                    instrumental = stem_audio
                                else:
                                    instrumental = instrumental.overlay(stem_audio)
                        
                        if instrumental:
                            instrumental.export(str(self.instrumental_path), format="wav")
                            self.log(f"[OK] Instrumental created: {self.instrumental_path}")
                except Exception as e:
                    self.log(f"[WARNING] Could not create instrumental: {e}")
            
            # 3. Auto-detect gender if gender alignment enabled (for initial curve setup)
            detected_gender = None
            initial_pitch_shift = 0.0
            
            if self.use_gender_alignment_var.get():
                progress_cb(70, "Detecting vocal gender...")
                detector = GenderDetector()
                detected_gender = detector.detect_gender(stems.vocals)
                self.log(f"[OK] Detected gender: {detected_gender}")
                
                # Calculate initial pitch shift based on target gender
                target_gender = self.original_gender_var.get()  # User's selected target
                if target_gender and detected_gender != target_gender:
                    # Male to Female: +12 semitones (up one octave)
                    # Female to Male: -12 semitones (down one octave)
                    if detected_gender == "male" and target_gender == "female":
                        initial_pitch_shift = 12.0
                        self.log(f"→ Suggested pitch shift: +12 semitones (male → female)")
                    elif detected_gender == "female" and target_gender == "male":
                        initial_pitch_shift = -12.0
                        self.log(f"→ Suggested pitch shift: -12 semitones (female → male)")
                
                # Update gender radio button on UI thread
                self.root.after(0, self.original_gender_var.set, detected_gender)
            
            # 4. Enhance vocals using Resemble Enhance if requested (Phase 2.7)
            enhanced_vocals_path = None
            cached_enhanced_path = output_dir / "vocals_enhanced.wav"
            
            if self.improve_vocals_var.get() and is_resemble_enhance_available():
                # Check if cached enhanced vocals exist
                if cached_enhanced_path.exists():
                    self.log(f"[OK] Using cached enhanced vocals: {cached_enhanced_path.name}")
                    enhanced_vocals_path = cached_enhanced_path
                else:
                    # Run enhancement
                    try:
                        progress_cb(75, "Enhancing vocals (AI-powered)...")
                        self.log("→ Starting vocal enhancement (Resemble Enhance, RK4 solver)...")
                        
                        # Create output path with source filename
                        enhanced_vocals_path = cached_enhanced_path
                        
                        # Progress tracking for enhancement
                        def enhance_progress_cb(percent, msg):
                            # Map 0-100% of enhancement to 75-85% overall progress
                            overall_percent = 75 + (percent * 0.10)
                            progress_cb(overall_percent, f"Enhancing: {msg}")
                        
                        # Run enhancement (fixed settings: RK4, 100 steps, 0.33 temp, no denoise)
                        success = enhance_vocals(
                            input_path=str(stems.vocals),
                            output_path=str(enhanced_vocals_path),
                            solver="rk4",
                            nfe=100,
                            temperature=0.33,
                            denoise_first=False,
                            progress_callback=enhance_progress_cb
                        )
                        
                        # Handle CUDA failure - ask user if they want to retry on CPU
                        if success == "cuda_failed":
                            import threading
                            user_choice = [None]  # Use list to pass by reference
                            event = threading.Event()
                            
                            def ask_user():
                                result = messagebox.askyesno(
                                    "GPU Enhancement Failed",
                                    "Vocal enhancement failed on GPU (CUDA error).\n\n"
                                    "Would you like to retry on CPU?\n"
                                    "(This will be significantly slower but should work)\n\n"
                                    "If you choose No, processing will continue\n"
                                    "without vocal enhancement (no Blend mode)."
                                )
                                user_choice[0] = result
                                event.set()
                            
                            self.root.after(0, ask_user)
                            event.wait()  # Wait for user response
                            
                            if user_choice[0]:  # User said Yes
                                self.root.after(0, self.log, "→ Retrying enhancement on CPU (this will be slower)...")
                                progress_cb(76, "Retrying enhancement on CPU...")
                                
                                from voice_revolver_core.infrastructure.resemble_enhance_wrapper import enhance_vocals_cpu
                                success = enhance_vocals_cpu(
                                    input_path=str(stems.vocals),
                                    output_path=str(enhanced_vocals_path),
                                    solver="rk4",
                                    nfe=100,
                                    temperature=0.33,
                                    denoise_first=False,
                                    progress_callback=enhance_progress_cb
                                )
                            else:  # User said No
                                self.root.after(0, self.log, "→ Skipping vocal enhancement (user declined CPU retry)")
                                success = False
                        
                        if success is True and enhanced_vocals_path.exists():
                            self.log(f"[OK] Vocal enhancement complete: {enhanced_vocals_path.name}")
                        else:
                            if success != False:  # Don't double-log if user already declined
                                self.log("[WARNING] Enhancement failed")
                            self.log("Blend mode will not be available. Continuing with original vocals.")
                            enhanced_vocals_path = None
                            
                    except Exception as e:
                        self.log(f"[WARNING] Enhancement error: {e}")
                        self.log("Blend mode will not be available. Continuing with original vocals.")
                        self.root.after(0, lambda err=str(e): messagebox.showwarning(
                            "Vocal Enhancement Failed",
                            f"Vocal enhancement encountered an error:\n{err}\n\n"
                            "Blend mode will not be available.\n"
                            "Processing will continue with original vocals."
                        ))
                        enhanced_vocals_path = None
            elif cached_enhanced_path.exists():
                # Enhancement not requested but cached version exists - use it anyway
                self.log(f"ℹ Found cached enhanced vocals: {cached_enhanced_path.name}")
                enhanced_vocals_path = cached_enhanced_path
            
            progress_cb(85, "Loading vocals into spectrum editor...")
            
            # 5. Pass both original and enhanced vocals to UI (for blend mode support)
            self.root.after(0, self._separation_complete_callback, 
                          stems.vocals,  # Always pass original vocals
                          detected_gender,
                          initial_pitch_shift,
                          enhanced_vocals_path)  # Pass enhanced if available, otherwise None
            
        except Exception as e:
            error_msg = f"Separation failed: {str(e)}"
            self.log(f"[ERROR] {error_msg}")
            self.log(traceback.format_exc())
            self.root.after(0, self._separation_failed_callback, error_msg)
    
    def _separation_complete_callback(self, vocals_path, detected_gender, initial_pitch_shift=0, enhanced_vocals_path=None):
        """UI thread callback when separation completes successfully
        
        Args:
            vocals_path: Path to original separated vocals
            detected_gender: Detected gender ("male" or "female")
            initial_pitch_shift: Initial pitch shift in semitones
            enhanced_vocals_path: Optional path to enhanced vocals (Phase 2.7)
        """
        try:
            # Load vocals into spectrum editor with both original and enhanced (if available)
            self.spectrum_editor.load_vocals(
                vocals_path,
                initial_pitch_shift=initial_pitch_shift,
                enhanced_vocal_path=enhanced_vocals_path,
                instrumental_path=self.instrumental_path if hasattr(self, 'instrumental_path') else None
            )
            
            #Set flags
            self.separation_complete = True
            self.processing = False
            
            # Clear edited vocals path (no edits yet) and disable edited vocals preview
            self.edited_vocals_path = None
            if 'original_vocals_edited' in self.preview_controls:
                self.preview_controls['original_vocals_edited']['play_btn'].config(state="disabled")
                self.preview_controls['original_vocals_edited']['stop_btn'].config(state="disabled")
            
            # Enable spectrum editor
            self._enable_spectrum_editor(True)
            
            # Enable reference selection panel
            self.reference_browse_btn.config(state="normal")
            self.ref_audio_radio.config(state="normal")
            self.ref_model_radio.config(state="normal")
            self.format_combo.config(state="readonly")
            self.vocal_only_check.config(state="normal")
            
            # Re-enable separation button (allow re-running)
            self.separation_btn.config(state="normal")
            
            # Update progress
            self._update_progress(100, "✓ Separation complete - Ready to edit")
            self.status_label.config(foreground="green")
            
            # Log completion
            if detected_gender:
                self.log(f"[OK] Separation complete! Detected: {detected_gender} vocals")
                self.log("Adjust gender if detection is incorrect")
            else:
                self.log("[OK] Separation complete!")
            
            # Log pre-populated curve settings
            if initial_pitch_shift != 0:
                self.log(f"ℹ Pitch curve pre-set to {initial_pitch_shift:+.1f} semitones (adjust as needed)")
            
            self.log("Edit vocal curves in spectrum editor, then select reference and start processing")
            
            # Check if ready to start processing
            self._check_ready()
            
        except Exception as e:
            self.log(f"Error loading vocals into editor: {e}")
            self._separation_failed_callback(str(e))
    
    def _separation_failed_callback(self, error_msg):
        """UI thread callback when separation fails"""
        self.separation_complete = False
        self.processing = False
        
        # Re-enable separation button
        self.separation_btn.config(state="normal" if self.original_file else "disabled")
        
        # Update UI
        self._update_progress(0, f"✗ Separation failed")
        self.status_label.config(foreground="red")
        
        # Show error
        messagebox.showerror("Separation Failed", error_msg)
    
    def _apply_curve_changes(self):
        """Apply pitch/volume/reverb curve edits to the separated vocals
        
        Useful when user removes all pre-populated points to reset
        """
        if not hasattr(self, 'original_vocals_path') or not self.original_vocals_path:
            self.log("[WARNING] No separated vocals available. Run separation first.")
            return
        
        # Get curves from spectrum editor
        curves = self.spectrum_editor.get_all_curves()
        
        # Note: We allow Apply Changes even with 0 points - this reloads original vocals
        
        self.log("=" * 50)
        self.log("Applying curve changes to preview...")
        
        has_any_edits = (curves['pitch'].has_edits() or 
                        curves['reverb'].has_edits() or 
                        curves['volume'].has_edits() or
                        curves['instrumental_volume'].has_edits())
        
        if not has_any_edits:
            self.log("ℹ No curve edits - reloading original vocals")
        else:
            if curves['pitch'].has_edits():
                self.log(f"• Pitch curve: {len(curves['pitch'].control_points)} points")
            if curves['reverb'].has_edits():
                self.log(f"• Reverb curve: {len(curves['reverb'].control_points)} points")
            if curves['volume'].has_edits():
                self.log(f"• Volume curve: {len(curves['volume'].control_points)} points")
            if curves['instrumental_volume'].has_edits():
                self.log(f"• Instrumental Volume curve: {len(curves['instrumental_volume'].control_points)} points (applies during final mix)")
        
        # Disable UI during processing
        self.spectrum_editor.set_enabled(False)
        self._update_progress(0, "Applying changes...")
        
        # Release audio file handle before processing (prevents permission errors)
        self.spectrum_editor.release_audio_file()
        
        # Run in background thread
        threading.Thread(target=self._apply_curves_worker, args=(curves,), daemon=False).start()
    
    def _apply_curves_worker(self, curves):
        """Background worker to apply curves (Phase 2.7: includes blend)"""
        try:
            from voice_revolver_core.infrastructure.audio_processor import AudioProcessor
            
            # Create temp directory for processed preview
            preview_dir = self.file_manager.get_workspace_temp_dir(CURRENT_WORKSPACE) / "preview"
            preview_dir.mkdir(exist_ok=True, parents=True)
            
            # Start with original vocals (always use the original, not the preview)
            current_audio = self.original_vocals_path
            processor = AudioProcessor()
            
            # Clear old preview files
            for old_file in preview_dir.glob("vocals_*.wav"):
                try:
                    old_file.unlink()
                except:
                    pass
            
            # Phase 2.7: Apply blend curve FIRST (if enhanced vocals available and blend curve has edits)
            if curves.get('blend') and curves['blend'].has_edits():
                # Check if enhanced vocals exist
                enhanced_vocals_path = None
                if hasattr(self.spectrum_editor, 'enhanced_vocal_path') and self.spectrum_editor.enhanced_vocal_path:
                    enhanced_vocals_path = self.spectrum_editor.enhanced_vocal_path
                
                if enhanced_vocals_path and enhanced_vocals_path.exists():
                    self.root.after(0, self._update_progress, 10, "Blending original and enhanced vocals...")
                    self.root.after(0, self.log, "→ Applying blend curve...")
                    
                    blend_output = preview_dir / "vocals_blend.wav"
                    success = processor.apply_blend_curve(
                        self.original_vocals_path,
                        enhanced_vocals_path,
                        blend_output,
                        curves['blend']
                    )
                    if success and blend_output.exists():
                        current_audio = blend_output
                        self.root.after(0, self.log, "  [OK] Blend curve applied (original + enhanced mixed)")
                    else:
                        raise RuntimeError("Failed to apply blend curve")
                else:
                    self.root.after(0, self.log, "  [WARNING] Enhanced vocals not available, skipping blend")
            
            # Apply pitch curve
            if curves['pitch'].has_edits():
                self.root.after(0, self._update_progress, 30, "Applying pitch curve...")
                self.root.after(0, self.log, "→ Applying pitch curve...")
                
                pitch_output = preview_dir / "vocals_pitch.wav"
                success = processor.apply_pitch_curve(
                    current_audio,
                    pitch_output,
                    curves['pitch']
                )
                if success and pitch_output.exists():
                    current_audio = pitch_output
                    self.root.after(0, self.log, "  [OK] Pitch curve applied")
                else:
                    raise RuntimeError("Failed to apply pitch curve")
            
            # Apply volume curve
            if curves['volume'].has_edits():
                self.root.after(0, self._update_progress, 60, "Applying volume curve...")
                self.root.after(0, self.log, "→ Applying volume curve...")
                
                volume_output = preview_dir / "vocals_volume.wav"
                success = processor.apply_volume_curve(
                    current_audio,
                    volume_output,
                    curves['volume']
                )
                if success and volume_output.exists():
                    current_audio = volume_output
                    self.root.after(0, self.log, "  [OK] Volume curve applied")
                else:
                    raise RuntimeError("Failed to apply volume curve")
            
            # Apply reverb curve
            if curves['reverb'].has_edits():
                self.root.after(0, self._update_progress, 90, "Applying reverb curve...")
                self.root.after(0, self.log, "→ Applying reverb curve...")
                
                reverb_output = preview_dir / "vocals_reverb.wav"
                success = processor.apply_reverb_curve(
                    current_audio,
                    reverb_output,
                    curves['reverb']
                )
                if success and reverb_output.exists():
                    current_audio = reverb_output
                    self.root.after(0, self.log, "  [OK] Reverb curve applied")
                else:
                    raise RuntimeError("Failed to apply reverb curve")
            
            # Save final preview with consistent name
            final_preview = preview_dir / "vocals_preview.wav"
            if current_audio != final_preview:
                import shutil
                import time
                
                # Delete old preview file if it exists (may be locked by spectrum editor)
                if final_preview.exists():
                    try:
                        final_preview.unlink()
                    except PermissionError:
                        # File is locked, wait a moment and try again
                        time.sleep(0.1)
                        try:
                            final_preview.unlink()
                        except:
                            # If still locked, use a different name
                            final_preview = preview_dir / f"vocals_preview_{int(time.time())}.wav"
                
                shutil.copy(str(current_audio), str(final_preview))
            
            # Process instrumental volume curve if present
            instrumental_preview = None
            if curves['instrumental_volume'].has_edits() and hasattr(self, 'instrumental_path') and self.instrumental_path:
                # Ensure instrumental_path is a Path object
                from pathlib import Path
                inst_path = Path(self.instrumental_path) if isinstance(self.instrumental_path, str) else self.instrumental_path
                
                if inst_path.exists():
                    self.root.after(0, self._update_progress, 95, "Applying instrumental volume curve...")
                    self.root.after(0, self.log, "→ Applying instrumental volume curve...")
                    
                    instrumental_preview = preview_dir / "instrumental_preview.wav"
                    success = processor.apply_volume_curve(
                        inst_path,
                        instrumental_preview,
                        curves['instrumental_volume']
                    )
                    if success and instrumental_preview.exists():
                        self.root.after(0, self.log, "  [OK] Instrumental volume curve applied")
                    else:
                        self.root.after(0, self.log, "  [WARNING] Failed to apply instrumental volume curve")
                        instrumental_preview = None
            
            # Success - reload in spectrum editor (preserving curves)
            self.root.after(0, self._curves_applied_callback, final_preview, instrumental_preview)
            
        except Exception as e:
            error_msg = f"Failed to apply curves: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self.root.after(0, self._curves_apply_failed_callback, error_msg)
    
    def _curves_applied_callback(self, processed_audio_path, instrumental_preview_path=None):
        """UI callback when curves are successfully applied"""
        try:
            # Store edited vocals path and enable preview button
            self.edited_vocals_path = processed_audio_path
            if 'original_vocals_edited' in self.preview_controls:
                self.preview_controls['original_vocals_edited']['play_btn'].config(state="normal")
                self.preview_controls['original_vocals_edited']['stop_btn'].config(state="normal")
            
            # Reload processed audio WITHOUT resetting curves
            self.spectrum_editor.reload_audio_only(processed_audio_path)
            
            # Reload processed instrumental if available
            if instrumental_preview_path and instrumental_preview_path.exists():
                self.spectrum_editor.reload_instrumental_only(instrumental_preview_path)
                self.log("  [OK] Instrumental preview updated")
            
            # Re-enable spectrum editor
            self.spectrum_editor.set_enabled(True)
            
            # Update progress
            self._update_progress(100, "✓ Changes applied to preview")
            self.status_label.config(foreground="green")
            
            self.log("[OK] Curve changes applied successfully!")
            self.log("  Preview updated - control points preserved for further editing")
            self.log("  Original vocals unchanged")
            self.log("=" * 50)
            
        except Exception as e:
            self.log(f"Error reloading preview: {e}")
            self._curves_apply_failed_callback(str(e))
    
    def _curves_apply_failed_callback(self, error_msg):
        """UI callback when curve application fails"""
        # Re-enable spectrum editor
        self.spectrum_editor.set_enabled(True)
        
        # Update UI
        self._update_progress(0, "✗ Failed to apply changes")
        self.status_label.config(foreground="red")
        
        # Show error
        self.log(f"[ERROR] {error_msg}")
        self.log("=" * 50)
        messagebox.showerror("Apply Failed", error_msg)
    
    def _create_log_window(self):
        """Create separate log window (hidden by default in Phase 2)"""
        self.log_window = tk.Toplevel(self.root)
        self.log_window.title("Voice Revolver AI - Logs")
        self.log_window.geometry("700x1050")  # Increased to match main window height
        
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
            if hasattr(self, 'log_hidden'):
                self.log_hidden = False
    
    def _toggle_log_window(self):
        """Toggle log window visibility (F12 shortcut)"""
        if hasattr(self, 'log_hidden') and self.log_hidden:
            self._show_log_window()
        else:
            self._hide_log_window()
            self.log_hidden = True
    
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
            
            # Invalidate cached enhanced vocals since we have a new audio file
            cached_enhanced = self.file_manager.get_workspace_temp_dir(CURRENT_WORKSPACE) / "separation" / "vocals_enhanced.wav"
            if cached_enhanced.exists():
                try:
                    cached_enhanced.unlink()
                    self.log("Cleared old enhanced vocals cache (new audio file)")
                except Exception as e:
                    self.log(f"[WARNING] Could not clear cache: {e}")
            
            # Phase 2: Enable separation button when original file selected
            if not self.processing:
                self.separation_btn.config(state="normal")
            
            self._check_ready()
    
    def _select_reference(self):
        """Select reference voice file or RVC model zip"""
        # Determine file type based on selected mode
        if self.reference_mode.get() == "audio":
            title = "Select Reference Voice (Audio)"
            filetypes = [
                ("Audio Files", "*.mp3 *.wav *.flac *.ogg *.m4a"),
                ("All Files", "*.*")
            ]
        else:  # model
            title = "Select RVC Model (Zip)"
            filetypes = [
                ("RVC Model", "*.zip"),
                ("All Files", "*.*")
            ]
        
        file_path = filedialog.askopenfilename(title=title, filetypes=filetypes)
        
        if file_path:
            # Validate zip file if model mode
            if self.reference_mode.get() == "model":
                is_valid, error_msg = self._validate_rvc_zip(file_path)
                if not is_valid:
                    messagebox.showerror("Invalid Model", error_msg)
                    return
            
            self.reference_file = file_path
            filename = Path(file_path).name
            self.reference_label.config(text=filename, foreground="black")
            mode_text = "Model" if self.reference_mode.get() == "model" else "Audio"
            self.log(f"Reference {mode_text}: {filename}")
            self._check_ready()
    
    def _on_gender_alignment_change(self):
        """Handle gender alignment checkbox toggle (Phase 2: Updated for new layout)"""
        enabled = self.use_gender_alignment_var.get()
        
        # Phase 2: Show/hide vocal match frame and threshold controls
        if enabled:
            self.orig_gender_frame.grid()  # Show vocal match selector
            self.threshold_frame.grid()     # Show threshold controls
        else:
            self.orig_gender_frame.grid_remove()  # Hide vocal match selector
            self.threshold_frame.grid_remove()     # Hide threshold controls
        
        status = "enabled" if enabled else "disabled"
        self.log(f"Gender alignment {status}")
    
    def _reset_rvc_params(self):
        """Reset all RVC parameters to default values"""
        self.f0_method_var.set("rmvpe")
        self.pitch_shift_slider.set(0)
        self.index_rate_slider.set(0.75)
        self.protection_slider.set(0.33)
        self.filter_radius_slider.set(3)
        self.rms_mix_rate_slider.set(0.25)
        self.log("RVC parameters reset to defaults")
    
    def _on_reference_mode_change(self):
        """Handle reference mode toggle between audio and model"""
        mode = self.reference_mode.get()
        
        # Clear current selection when switching modes
        self.reference_file = None
        self.reference_label.config(text="No file selected", foreground="gray")
        self.log(f"Reference mode changed to: {mode.upper()}")
        
        # Show/hide RVC parameters based on mode
        if mode == "model":
            self.rvc_params_frame.grid()  # Show RVC parameters
        else:
            self.rvc_params_frame.grid_remove()  # Hide RVC parameters
        
        # Show/hide gender selector based on mode AND gender alignment checkbox
        gender_enabled = self.use_gender_alignment_var.get()
        if mode == "model" and gender_enabled:
            self.model_gender_frame.grid()  # Show manual gender selector for RVC
        else:
            self.model_gender_frame.grid_remove()  # Hide gender selector
            
        self._check_ready()
    
    def _on_threshold_low_change(self, value):
        """Update low threshold entry when slider changes"""
        self.threshold_low_entry.delete(0, tk.END)
        self.threshold_low_entry.insert(0, f"{float(value):.0f}")
    
    def _on_threshold_mid_change(self, value):
        """Update mid threshold entry when slider changes"""
        self.threshold_mid_entry.delete(0, tk.END)
        self.threshold_mid_entry.insert(0, f"{float(value):.0f}")
    
    def _on_threshold_high_change(self, value):
        """Update high threshold entry when slider changes"""
        self.threshold_high_entry.delete(0, tk.END)
        self.threshold_high_entry.insert(0, f"{float(value):.0f}")
    
    def _on_threshold_low_entry(self, event=None):
        """Update low threshold slider when entry changes"""
        try:
            value = float(self.threshold_low_entry.get())
            value = max(100, min(200, value))  # Clamp to valid range
            self.threshold_low_var.set(value)
            self.threshold_low_entry.delete(0, tk.END)
            self.threshold_low_entry.insert(0, f"{value:.0f}")
        except ValueError:
            self.threshold_low_entry.delete(0, tk.END)
            self.threshold_low_entry.insert(0, f"{self.threshold_low_var.get():.0f}")
    
    def _on_threshold_mid_entry(self, event=None):
        """Update mid threshold slider when entry changes"""
        try:
            value = float(self.threshold_mid_entry.get())
            value = max(150, min(220, value))  # Clamp to valid range
            self.threshold_mid_var.set(value)
            self.threshold_mid_entry.delete(0, tk.END)
            self.threshold_mid_entry.insert(0, f"{value:.0f}")
        except ValueError:
            self.threshold_mid_entry.delete(0, tk.END)
            self.threshold_mid_entry.insert(0, f"{self.threshold_mid_var.get():.0f}")
    
    def _on_threshold_high_entry(self, event=None):
        """Update high threshold slider when entry changes"""
        try:
            value = float(self.threshold_high_entry.get())
            value = max(180, min(280, value))  # Clamp to valid range
            self.threshold_high_var.set(value)
            self.threshold_high_entry.delete(0, tk.END)
            self.threshold_high_entry.insert(0, f"{value:.0f}")
        except ValueError:
            self.threshold_high_entry.delete(0, tk.END)
            self.threshold_high_entry.insert(0, f"{self.threshold_high_var.get():.0f}")
    
    def _reset_threshold(self, threshold_type):
        """Reset threshold to default value"""
        defaults = {
            'low': 180.0,
            'mid': 230.0,
            'high': 280.0
        }
        
        if threshold_type == 'low':
            self.threshold_low_var.set(defaults['low'])
            self.threshold_low_entry.delete(0, tk.END)
            self.threshold_low_entry.insert(0, f"{defaults['low']:.0f}")
            self.log(f"Reset low threshold to {defaults['low']:.0f}Hz")
        elif threshold_type == 'mid':
            self.threshold_mid_var.set(defaults['mid'])
            self.threshold_mid_entry.delete(0, tk.END)
            self.threshold_mid_entry.insert(0, f"{defaults['mid']:.0f}")
            self.log(f"Reset mid threshold to {defaults['mid']:.0f}Hz")
        elif threshold_type == 'high':
            self.threshold_high_var.set(defaults['high'])
            self.threshold_high_entry.delete(0, tk.END)
            self.threshold_high_entry.insert(0, f"{defaults['high']:.0f}")
            self.log(f"Reset high threshold to {defaults['high']:.0f}Hz")
    
    def _validate_rvc_zip(self, zip_path: str) -> Tuple[bool, str]:
        """
        Validate RVC model zip file contains required .pth and .index files
        
        Returns:
            (is_valid, error_message)
        """
        try:
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                file_list = zip_ref.namelist()
                
                # Check for .pth file
                pth_files = [f for f in file_list if f.endswith('.pth')]
                if not pth_files:
                    return False, "Invalid RVC model: No .pth file found in zip"
                
                # Check for .index file
                index_files = [f for f in file_list if f.endswith('.index')]
                if not index_files:
                    return False, "Invalid RVC model: No .index file found in zip"
                
                self.log(f"[OK] Valid RVC model: {pth_files[0]} + {index_files[0]}")
                return True, ""
                
        except zipfile.BadZipFile:
            return False, "Invalid zip file format"
        except Exception as e:
            return False, f"Error validating zip: {str(e)}"
    
    def _check_ready(self):
        """Check if ready to start processing (Phase 2: Requires separation complete)"""
        # Phase 2: Start Processing requires:
        # 1. Reference file selected
        # 2. Separation completed
        # 3. Not currently processing
        if self.reference_file and self.separation_complete and not self.processing:
            self.start_btn.config(state="normal")
        else:
            self.start_btn.config(state="disabled")
    
    def _update_progress(self, percentage, stage):
        """Update progress bar and status"""
        self.progress_bar["value"] = percentage
        self.status_label.config(text=stage)
        self.root.update_idletasks()
    
    def _start_processing(self):
        """Start processing in background thread (Phase 2: Updated for two-stage workflow)"""
        # Phase 2: Check separation complete
        if not self.separation_complete:
            messagebox.showwarning("Separation Required", 
                                  "Please run vocal separation first!\n\nClick 'Run Separation' button.")
            return
        
        if not self.reference_file:
            messagebox.showwarning("Missing Reference", "Please select a reference voice or model")
            return
        
        # CRITICAL: Unload all audio files before processing to avoid file locks
        self._unload_all_previews()
        
        self.processing = True
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.export_btn.config(state="disabled")
        self.progress_bar["value"] = 0
        
        self.log("=" * 60)
        self.log("Starting voice conversion processing...")
        self.log(f"Original: {Path(self.original_file).name}")
        self.log(f"Reference: {Path(self.reference_file).name}")
        self.log(f"Device: {self.device_var.get().upper()}")
        
        # Phase 2: Get editing curves from spectrum editor and store as instance variable
        self.editing_curves = self.spectrum_editor.get_all_curves()
        if self.editing_curves['pitch'].has_edits():
            self.log(f"Using custom pitch curve ({len(self.editing_curves['pitch'].control_points)} points)")
        if self.editing_curves['reverb'].has_edits():
            self.log(f"Using custom reverb curve ({len(self.editing_curves['reverb'].control_points)} points)")
        if self.editing_curves['volume'].has_edits():
            self.log(f"Using custom volume curve ({len(self.editing_curves['volume'].control_points)} points)")
        if self.editing_curves['instrumental_volume'].has_edits():
            self.log(f"Using custom instrumental volume curve ({len(self.editing_curves['instrumental_volume'].control_points)} points)")
        
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
            separation_model = self.separation_model_var.get()
            
            self.log("Initializing processing components...")
            
            # FFmpeg is already configured globally in main(), just verify it's available
            ffmpeg_dir = self.ffmpeg_checker.get_ffmpeg_dir()
            if not ffmpeg_dir:
                raise RuntimeError("FFmpeg not available")
            
            self.log(f"FFmpeg: {ffmpeg_dir}")
            
            # Initialize stem separator based on user selection
            if separation_model == "mdx":
                try:
                    from voice_revolver_core.infrastructure.mdx_wrapper import MDXWrapper
                    stem_separator = MDXWrapper(device)
                    self.log("Using MDX for stem separation (best vocal isolation)")
                except Exception as e:
                    self.log(f"[!] MDX failed to load: {str(e)}")
                    self.log("[!] Falling back to Demucs...")
                    stem_separator = DemucsWrapper(device)
                    self.log("Using Demucs for stem separation (balanced quality)")
            else:
                stem_separator = DemucsWrapper(device)
                self.log("Using Demucs for stem separation (balanced quality)")
            
            # ChatterBox VC - Better quality than OpenVoice
            chatterbox_wrapper = ChatterBoxVCWrapper(device)
            
            # OpenVoice (legacy - uncomment to use instead of ChatterBox):
            # openvoice_wrapper = OpenVoiceWrapper(
            #     self.model_manager.openvoice_path,
            #     device
            # )
            
            audio_mixer = AudioMixer(ffmpeg_dir)
            
            # Create voice replacement service
            service = VoiceReplacementService(
                stem_separator,  # Can be either DemucsWrapper or MDXWrapper
                chatterbox_wrapper,  # Using ChatterBox instead of openvoice_wrapper
                None,  # voice_transformer (not implemented yet)
                audio_mixer,
                self.file_manager,
                self.progress_tracker
            )
            
            # Get editing curves from instance variable (set in _start_processing)
            editing_curves = self.editing_curves if hasattr(self, 'editing_curves') else None
            
            # Get RVC parameters (will be used only when reference_mode == "model")
            rvc_params = {
                'f0_method': self.f0_method_var.get(),
                'rvc_pitch_shift': int(self.pitch_shift_slider.get()),
                'index_rate': self.index_rate_slider.get(),
                'filter_radius': int(self.filter_radius_slider.get()),
                'rms_mix_rate': self.rms_mix_rate_slider.get(),
                'protect': self.protection_slider.get()
            }
            
            # Create voice params
            # NOTE: style and tau are ignored by ChatterBox (only used by OpenVoice)
            voice_params = VoiceConversionParams(
                pitch=pitch,
                style="default",                  # Ignored by ChatterBox
                style_strength=1.0,               # Ignored by ChatterBox
                tau=0.3,                          # Ignored by ChatterBox
                auto_detect_gender=self.use_gender_alignment_var.get(),  # Use gender alignment
                detected_original_gender=None,    # Will be populated during processing
                detected_reference_gender=None,   # Will be populated during processing
                model_gender=self.model_gender_var.get(),  # Manual model gender for RVC
                original_gender=self.original_gender_var.get(),  # Manual original gender for RVC
                threshold_low=self.threshold_low_var.get(),  # Pitch shift sensitivity - low
                threshold_mid=self.threshold_mid_var.get(),  # Pitch shift sensitivity - mid
                threshold_high=self.threshold_high_var.get(),  # Pitch shift sensitivity - high
                separation_model=separation_model,  # "demucs" (balanced) or "mdx" (best vocals)
                editing_curves=editing_curves,  # Phase 2: User editing curves from spectrum editor
                **rvc_params  # RVC-specific parameters
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
                output_dir=self.file_manager.get_workspace_temp_dir(CURRENT_WORKSPACE),
                vocal_only=self.vocal_only_var.get(),
                reference_mode=self.reference_mode.get(),  # Pass dual-reference mode
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
        self.log("[OK] Processing complete!")
        self.log(f"Output: {self.output_file}")
        self.log("=" * 60)
        
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")
        self.export_btn.config(state="normal")
        
        # Load all 6 audio files for preview
        self._load_all_previews()
        
        messagebox.showinfo("Success", "Voice replacement complete!\\nUse the Preview section to play each track.")
    
    def _processing_failed(self, error):
        """Called when processing fails"""
        self.processing = False
        self.progress_bar["value"] = 0
        self.status_label.config(text="✗ Failed", foreground="red")
        self.log("=" * 60)
        self.log(f"[ERROR] Processing failed: {error}")
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
                self.log(f"[OK] Exported to: {save_path}")
                messagebox.showinfo("Export Complete", f"File saved to:\n{save_path}")
            except Exception as e:
                self.log(f"[ERROR] Export failed: {e}")
                messagebox.showerror("Export Failed", f"Error:\n{e}")
    
    # ========== Audio Preview Methods (6-Track System) ==========
    
    def _unload_all_previews(self):
        """Unload all audio files to release file locks before new processing"""
        if not PYGAME_AVAILABLE:
            return
        
        try:
            # Stop any playing audio
            if self.current_track:
                mixer.music.stop()
                self.current_track = None
            
            # Unload the mixer music
            mixer.music.unload()
            
            # Reset all preview states
            for track_id in self.preview_states:
                state = self.preview_states[track_id]
                state['loaded'] = False
                state['playing'] = False
                state['length'] = 0
                if state['timer']:
                    self.root.after_cancel(state['timer'])
                    state['timer'] = None
                
                # Disable controls
                if track_id in self.preview_controls:
                    controls = self.preview_controls[track_id]
                    controls['play_btn'].config(state="disabled", text="▶")
                    controls['stop_btn'].config(state="disabled")
                    controls['timeline'].config(state="disabled")
                    controls['export_btn'].config(state="disabled")
                    controls['timeline_var'].set(0)
                    controls['time_label'].config(text="00:00/00:00")
            
            # Clear file paths
            self.original_audio_path = None
            self.original_vocals_path = None
            self.reference_denoised_path = None
            self.vocals_converted_path = None
            self.final_mix_path = None
            self.instrumental_path = None
            
            self.log("Unloaded all preview files")
        except Exception as e:
            self.log(f"Warning: Error unloading previews: {e}")
    
    def _load_all_previews(self):
        """Load all audio files for preview after processing (5-6 tracks depending on mode)"""
        if not PYGAME_AVAILABLE:
            self.log("Audio preview not available (pygame not installed)")
            return
        
        # Determine file paths from processing output
        temp_dir = self.file_manager.get_workspace_temp_dir(CURRENT_WORKSPACE)
        
        # 1. Original audio (user input)
        self.original_audio_path = self.original_file
        
        # 2. Original vocals only (before conversion)
        original_vocals_path = temp_dir / "original_vocals.wav"
        if original_vocals_path.exists():
            self.original_vocals_path = str(original_vocals_path)
        
        # 3. Reference voice (denoised) - ONLY for audio mode (skip for RVC model)
        reference_denoised_path = temp_dir / "reference_denoised.wav"
        if self.reference_mode.get() == "audio":
            self.log(f"Looking for reference_denoised at: {reference_denoised_path}")
            if reference_denoised_path.exists():
                self.reference_denoised_path = str(reference_denoised_path)
                self.log(f"[OK] Found reference_denoised.wav")
            else:
                self.log(f"[ERROR] reference_denoised.wav not found")
        else:
            # Model mode - skip reference denoising
            self.log("Model mode: Skipping reference_denoised preview (not applicable for RVC)")
            self.reference_denoised_path = None
        
        # 4. Converted vocals only
        vocals_path = temp_dir / "converted_vocals.wav"
        if vocals_path.exists():
            self.vocals_converted_path = str(vocals_path)
        
        # 5. Final mix (ALWAYS load the full remix, regardless of vocal_only setting)
        final_mix_path = temp_dir / "mixed_output.wav"
        if final_mix_path.exists():
            self.final_mix_path = str(final_mix_path)
        else:
            # Fallback to output file if mixed_output doesn't exist
            self.final_mix_path = self.output_file
        
        # 6. Instrumental (need to mix stems excluding vocals)
        self._create_instrumental_track(temp_dir)
        
        # Build track list (conditionally include reference_denoised)
        tracks = [
            ('original', self.original_audio_path, "Original Audio"),
            ('original_vocals', self.original_vocals_path, "Original Vocals"),
        ]
        
        # Add reference_denoised only in audio mode
        if self.reference_mode.get() == "audio":
            tracks.append(('reference_denoised', self.reference_denoised_path, "Reference Voice (Cleaned)"))
        
        # Continue with remaining tracks
        tracks.extend([
            ('vocals', self.vocals_converted_path, "Converted Vocals"),
            ('final', self.final_mix_path, "Final Mix"),
            ('instrumental', self.instrumental_path, "Instrumental")
        ])
        
        for track_id, file_path, name in tracks:
            self.log(f"Checking {name}: path={file_path}, exists={os.path.exists(file_path) if file_path else False}")
            if file_path and os.path.exists(file_path):
                self._load_single_preview(track_id, file_path, name)
            else:
                self.log(f"[WARNING] {name} not available for preview")
    
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
                self.instrumental_path = instrumental_path  # Keep as Path object
                self.log("[OK] Created instrumental track")
            else:
                self.log("[WARNING] Could not create instrumental track")
        except Exception as e:
            self.log(f"[WARNING] Error creating instrumental: {e}")
    
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
            
            self.log(f"[OK] Loaded {track_name} for preview")
        except Exception as e:
            self.log(f"[WARNING] Could not load {track_name}: {e}")
    
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
                mixer.music.set_volume(self.preview_volume_var.get() / 100.0)  # Apply current volume (0-100 -> 0.0-1.0)
                mixer.music.play()
                state['playing'] = True
                self.current_track = track_id
                controls['play_btn'].config(text="⏸")
                self._update_playback_time(track_id)
            except Exception as e:
                self.log(f"[WARNING] Playback error: {e}")
    
    def _on_tau_change(self, value):
        """Handle tau slider changes - update entry field"""
        try:
            tau = float(value)
            self.tau_entry.delete(0, tk.END)
            self.tau_entry.insert(0, f"{tau:.2f}")
        except Exception as e:
            self.log(f"[WARNING] Tau slider error: {e}")
    
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
            self.log(f"[WARNING] Tau entry error: {e}")
    
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
            self.log(f"[WARNING] Seek error: {e}")
    
    def _on_preview_volume_change(self, value):
        """Handle preview section volume slider changes"""
        volume = float(value) / 100.0
        mixer.music.set_volume(volume)
        self.preview_volume_label.config(text=f"{int(float(value))}%")
    
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
            self.log(f"[WARNING] Playback update error: {e}")
    
    def _get_track_path(self, track_id):
        """Get file path for a specific track"""
        paths = {
            'original': self.original_audio_path,
            'original_vocals': self.original_vocals_path,
            'original_vocals_edited': self.edited_vocals_path,
            'reference_denoised': self.reference_denoised_path,
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
            'original_vocals_edited': 'original_vocals_edited',
            'reference_denoised': 'reference_denoised',
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
                
                self.log(f"[OK] Exported {track_name} to: {save_path}")
                messagebox.showinfo("Export Complete", f"File saved to:\\n{save_path}")
            except Exception as e:
                self.log(f"[ERROR] Export failed: {e}")
                messagebox.showerror("Export Failed", f"Error:\\n{e}")


def main():
    """Main entry point"""
    # Check Python version
    if sys.version_info[:2] != (3, 11):
        print(f"[WARNING] WARNING: Python 3.11.x required, you are using {sys.version}")
        print("   PyTorch may not work correctly with other versions!")
    
    # Preload PyTorch to avoid DLL loading issues
    try:
        print("[LOADING] Preloading PyTorch...")
        import torch
        _ = torch.tensor([1.0])
        print(f"[OK] PyTorch {torch.__version__} loaded")
    except Exception as e:
        print(f"[WARNING] PyTorch preload warning: {e}")
    
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
    print("[LOADING] Configuring FFmpeg...")
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
        
        print(f"[OK] FFmpeg configured: {ffmpeg_exe}")
    except Exception as e:
        print(f"[WARNING] FFmpeg configuration warning: {e}")
        print(f"   FFmpeg may not be available, processing will fail")
    
    # Preload AI libraries (AFTER ffmpeg is configured)
    try:
        print("[LOADING] Preloading AI libraries...")
        from openvoice.api import ToneColorConverter
        from demucs.pretrained import get_model
        import torchaudio
        print("[OK] AI libraries loaded")
    except Exception as e:
        print(f"[WARNING] AI library preload warning: {e}")
    
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
