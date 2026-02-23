"""Input panel for Audio Training workspace - Audio list and training settings."""

import tkinter as tk
from tkinter import ttk, filedialog
from pathlib import Path
from typing import Optional, Callable, List, Dict
import logging
import threading
import re

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

from voice_revolver_ui.components.labeled_slider import LabeledSlider

logger = logging.getLogger(__name__)


# Training quality presets
TRAINING_PRESETS = {
    "Quick": {
        "epochs": 200,
        "batch_size": 12,
        "sample_rate": 40000,
        "save_every": 100,
        "description": "~30 min training time"
    },
    "Balanced": {
        "epochs": 400,
        "batch_size": 8,
        "sample_rate": 40000,
        "save_every": 50,
        "description": "~1.5 hours training time"
    },
    "High Quality": {
        "epochs": 600,
        "batch_size": 4,
        "sample_rate": 48000,
        "save_every": 25,
        "description": "~3-4 hours training time"
    }
}

DEFAULT_PRESET = "Balanced"


class AudioItem:
    """Represents a single audio file in the training list."""
    
    def __init__(
        self,
        item_id: int,
        file_path: Path,
        display_name: str
    ):
        """Initialize audio item.
        
        Args:
            item_id: Unique identifier for this item
            file_path: Path to the audio file
            display_name: Name to display in the UI
        """
        self.item_id = item_id
        self.file_path = file_path
        self.display_name = display_name
        self.duration_seconds: float = 0.0
        
        # UI elements (set when row is created)
        self.frame: Optional[ttk.Frame] = None
        self.duration_label: Optional[ttk.Label] = None


class InputPanel(ttk.Frame):
    """Left panel with model name, audio list, and training settings."""
    
    # Parameter ranges and defaults
    PARAM_SPECS = {
        "epochs": {"min": 100, "max": 1000, "default": 400, "step": 50},
        "batch_size": {"min": 4, "max": 16, "default": 8, "step": 2},
        "sample_rate": {"min": 32000, "max": 48000, "default": 40000, "step": 8000},
        "save_every": {"min": 25, "max": 100, "default": 50, "step": 25}
    }
    
    def __init__(
        self,
        parent: ttk.Frame,
        on_train: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
        initial_device: str = "cuda",
        **kwargs
    ):
        """Initialize the input panel.
        
        Args:
            parent: Parent widget
            on_train: Callback when Start Training is clicked
            on_cancel: Callback when Cancel is clicked
            initial_device: Initial device selection (cuda/cpu) from startup
        """
        super().__init__(parent, padding=10, **kwargs)
        
        self.on_train = on_train
        self.on_cancel = on_cancel
        self.initial_device = initial_device
        
        # Audio file management
        self.audio_items: List[AudioItem] = []
        self.next_item_id = 1
        
        # State
        self.is_training = False
        
        # Control variables
        self.model_name_var = tk.StringVar(value="")
        self.preset_var = tk.StringVar(value=DEFAULT_PRESET)
        self.device_var = tk.StringVar(value=self.initial_device)  # Sync with startup selection
        self.use_advanced_var = tk.BooleanVar(value=False)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)  # Audio list expands
        
        row = 0
        
        # === Title ===
        title_label = ttk.Label(
            self,
            text="Audio Training",
            font=("Segoe UI", 14, "bold")
        )
        title_label.grid(row=row, column=0, sticky=tk.W, pady=(0, 10))
        row += 1
        
        # === Model Name Section ===
        name_frame = ttk.LabelFrame(self, text="Model Name", padding=10)
        name_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        name_frame.columnconfigure(0, weight=1)
        
        self.model_name_entry = ttk.Entry(
            name_frame,
            textvariable=self.model_name_var,
            font=("Segoe UI", 10)
        )
        self.model_name_entry.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        
        name_hint = ttk.Label(
            name_frame,
            text="Letters, numbers, and underscores only",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        name_hint.grid(row=1, column=0, sticky=tk.W)
        
        # Validate model name on change
        self.model_name_var.trace_add("write", self._validate_model_name)
        
        row += 1
        
        # === Audio Files Section ===
        audio_frame = ttk.LabelFrame(self, text="Audio Samples", padding=5)
        audio_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        audio_frame.columnconfigure(0, weight=1)
        audio_frame.rowconfigure(0, weight=1)
        
        # Scrollable canvas for audio files
        self.audio_canvas = tk.Canvas(audio_frame, highlightthickness=0, height=180)
        self.audio_scrollbar = ttk.Scrollbar(
            audio_frame,
            orient=tk.VERTICAL,
            command=self.audio_canvas.yview
        )
        self.audio_inner_frame = ttk.Frame(self.audio_canvas)
        
        self.audio_canvas.configure(yscrollcommand=self.audio_scrollbar.set)
        
        # Create window in canvas
        self.audio_window = self.audio_canvas.create_window(
            (0, 0),
            window=self.audio_inner_frame,
            anchor=tk.NW
        )
        
        # Grid layout
        self.audio_canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.audio_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Configure inner frame expansion
        self.audio_inner_frame.columnconfigure(0, weight=1)
        
        # Bind canvas resize
        self.audio_canvas.bind("<Configure>", self._on_canvas_configure)
        self.audio_inner_frame.bind("<Configure>", self._on_frame_configure)
        
        # Bind mousewheel scrolling
        self.audio_canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # Empty state label
        self.empty_label = ttk.Label(
            self.audio_inner_frame,
            text="No audio files added.\nClick 'Add Audio Files' to begin.",
            foreground="gray",
            justify=tk.CENTER
        )
        self.empty_label.grid(row=0, column=0, pady=30)
        
        # Total duration display
        self.duration_frame = ttk.Frame(audio_frame)
        self.duration_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        self.total_duration_var = tk.StringVar(value="Total: 0:00")
        self.duration_label = ttk.Label(
            self.duration_frame,
            textvariable=self.total_duration_var,
            font=("Segoe UI", 9)
        )
        self.duration_label.pack(side=tk.LEFT)
        
        self.duration_status_var = tk.StringVar(value="")
        self.duration_status_label = ttk.Label(
            self.duration_frame,
            textvariable=self.duration_status_var,
            font=("Segoe UI", 9)
        )
        self.duration_status_label.pack(side=tk.LEFT, padx=(10, 0))
        
        row += 1
        
        # === Add Audio Button ===
        self.add_audio_btn = ttk.Button(
            self,
            text="Add Audio Files",
            command=self._on_add_audio_clicked
        )
        self.add_audio_btn.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        row += 1
        
        # === Training Settings Section ===
        settings_frame = ttk.LabelFrame(self, text="Training Settings", padding=10)
        settings_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        settings_frame.columnconfigure(1, weight=1)
        
        # Quality Preset dropdown (visible in simple mode)
        self.preset_frame = ttk.Frame(settings_frame)
        self.preset_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 5))
        self.preset_frame.columnconfigure(1, weight=1)
        
        ttk.Label(self.preset_frame, text="Quality:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.preset_combo = ttk.Combobox(
            self.preset_frame,
            textvariable=self.preset_var,
            values=list(TRAINING_PRESETS.keys()),
            state="readonly",
            width=15
        )
        self.preset_combo.grid(row=0, column=1, sticky=tk.W)
        self.preset_combo.bind("<<ComboboxSelected>>", self._on_preset_changed)
        
        self.preset_desc_var = tk.StringVar(value=TRAINING_PRESETS[DEFAULT_PRESET]["description"])
        self.preset_desc_label = ttk.Label(
            self.preset_frame,
            textvariable=self.preset_desc_var,
            font=("Segoe UI", 8),
            foreground="gray"
        )
        self.preset_desc_label.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        # Device selector (GPU/CPU)
        device_frame = ttk.Frame(settings_frame)
        device_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 5))
        device_frame.columnconfigure(1, weight=1)
        
        ttk.Label(device_frame, text="Device:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.device_combo = ttk.Combobox(
            device_frame,
            textvariable=self.device_var,
            values=["cuda", "cpu"],
            state="readonly",
            width=10
        )
        self.device_combo.grid(row=0, column=1, sticky=tk.W)
        
        device_desc = ttk.Label(
            device_frame,
            text="GPU (cuda) is much faster. Use CPU if no NVIDIA GPU.",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        device_desc.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(2, 0))
        
        # Use Advanced Settings checkbox
        self.advanced_check = ttk.Checkbutton(
            settings_frame,
            text="Use Advanced Settings",
            variable=self.use_advanced_var,
            command=self._on_advanced_toggled
        )
        self.advanced_check.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(5, 0))
        
        # Advanced parameters frame (hidden by default)
        self.advanced_frame = ttk.Frame(settings_frame)
        self.advanced_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        self.advanced_frame.columnconfigure(0, weight=1)
        self.advanced_frame.grid_remove()  # Hidden by default
        
        # Create parameter sliders
        self._create_parameter_sliders()
        
        row += 1
        
        # === Action Buttons ===
        button_frame = ttk.Frame(self)
        button_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 5))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        
        self.train_btn = ttk.Button(
            button_frame,
            text="Start Training",
            command=self._on_train_clicked,
            style="Accent.TButton"
        )
        self.train_btn.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
        
        self.cancel_btn = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel_clicked,
            state=tk.DISABLED
        )
        self.cancel_btn.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(5, 0))
    
    def _create_parameter_sliders(self):
        """Create the parameter sliders for advanced mode."""
        param_row = 0
        
        # Epochs slider
        epochs_frame = ttk.Frame(self.advanced_frame)
        epochs_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        epochs_frame.columnconfigure(0, weight=1)
        
        epochs_header = ttk.Frame(epochs_frame)
        epochs_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        epochs_header.columnconfigure(0, weight=1)
        
        ttk.Label(epochs_header, text="Epochs", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.epochs_reset_btn = ttk.Button(
            epochs_header, text="↺", width=3,
            command=lambda: self._reset_param("epochs")
        )
        self.epochs_reset_btn.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Label(
            epochs_frame,
            text="Number of training iterations (more = better, but risk of overfitting)",
            font=("Segoe UI", 8),
            foreground="gray"
        ).grid(row=1, column=0, sticky=tk.W)
        
        epochs_control = ttk.Frame(epochs_frame)
        epochs_control.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(3, 0))
        epochs_control.columnconfigure(0, weight=1)
        
        self.epochs_var = tk.IntVar(value=self.PARAM_SPECS["epochs"]["default"])
        self.epochs_slider = ttk.Scale(
            epochs_control,
            from_=self.PARAM_SPECS["epochs"]["min"],
            to=self.PARAM_SPECS["epochs"]["max"],
            variable=self.epochs_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self._on_slider_changed("epochs", v)
        )
        self.epochs_slider.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.epochs_entry = ttk.Entry(epochs_control, width=8, justify=tk.CENTER)
        self.epochs_entry.grid(row=0, column=1)
        self.epochs_entry.insert(0, str(self.PARAM_SPECS["epochs"]["default"]))
        self.epochs_entry.bind("<Return>", lambda e: self._on_entry_changed("epochs"))
        self.epochs_entry.bind("<FocusOut>", lambda e: self._on_entry_changed("epochs"))
        
        ttk.Label(epochs_control, text="(100-1000)").grid(row=0, column=2, padx=(5, 0))
        
        param_row += 1
        
        # Batch Size slider
        batch_frame = ttk.Frame(self.advanced_frame)
        batch_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        batch_frame.columnconfigure(0, weight=1)
        
        batch_header = ttk.Frame(batch_frame)
        batch_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        batch_header.columnconfigure(0, weight=1)
        
        ttk.Label(batch_header, text="Batch Size", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.batch_reset_btn = ttk.Button(
            batch_header, text="↺", width=3,
            command=lambda: self._reset_param("batch_size")
        )
        self.batch_reset_btn.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Label(
            batch_frame,
            text="Chunks processed at once (lower = better quality, slower training)",
            font=("Segoe UI", 8),
            foreground="gray"
        ).grid(row=1, column=0, sticky=tk.W)
        
        batch_control = ttk.Frame(batch_frame)
        batch_control.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(3, 0))
        batch_control.columnconfigure(0, weight=1)
        
        self.batch_var = tk.IntVar(value=self.PARAM_SPECS["batch_size"]["default"])
        self.batch_slider = ttk.Scale(
            batch_control,
            from_=self.PARAM_SPECS["batch_size"]["min"],
            to=self.PARAM_SPECS["batch_size"]["max"],
            variable=self.batch_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self._on_slider_changed("batch_size", v)
        )
        self.batch_slider.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.batch_entry = ttk.Entry(batch_control, width=8, justify=tk.CENTER)
        self.batch_entry.grid(row=0, column=1)
        self.batch_entry.insert(0, str(self.PARAM_SPECS["batch_size"]["default"]))
        self.batch_entry.bind("<Return>", lambda e: self._on_entry_changed("batch_size"))
        self.batch_entry.bind("<FocusOut>", lambda e: self._on_entry_changed("batch_size"))
        
        ttk.Label(batch_control, text="(4-16)").grid(row=0, column=2, padx=(5, 0))
        
        param_row += 1
        
        # Sample Rate slider
        sr_frame = ttk.Frame(self.advanced_frame)
        sr_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        sr_frame.columnconfigure(0, weight=1)
        
        sr_header = ttk.Frame(sr_frame)
        sr_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        sr_header.columnconfigure(0, weight=1)
        
        ttk.Label(sr_header, text="Sample Rate", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.sr_reset_btn = ttk.Button(
            sr_header, text="↺", width=3,
            command=lambda: self._reset_param("sample_rate")
        )
        self.sr_reset_btn.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Label(
            sr_frame,
            text="Audio quality in Hz (higher = more detail, longer training)",
            font=("Segoe UI", 8),
            foreground="gray"
        ).grid(row=1, column=0, sticky=tk.W)
        
        sr_control = ttk.Frame(sr_frame)
        sr_control.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(3, 0))
        sr_control.columnconfigure(0, weight=1)
        
        self.sr_var = tk.IntVar(value=self.PARAM_SPECS["sample_rate"]["default"])
        self.sr_slider = ttk.Scale(
            sr_control,
            from_=self.PARAM_SPECS["sample_rate"]["min"],
            to=self.PARAM_SPECS["sample_rate"]["max"],
            variable=self.sr_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self._on_slider_changed("sample_rate", v)
        )
        self.sr_slider.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.sr_entry = ttk.Entry(sr_control, width=8, justify=tk.CENTER)
        self.sr_entry.grid(row=0, column=1)
        self.sr_entry.insert(0, str(self.PARAM_SPECS["sample_rate"]["default"]))
        self.sr_entry.bind("<Return>", lambda e: self._on_entry_changed("sample_rate"))
        self.sr_entry.bind("<FocusOut>", lambda e: self._on_entry_changed("sample_rate"))
        
        ttk.Label(sr_control, text="(32k-48k)").grid(row=0, column=2, padx=(5, 0))
        
        param_row += 1
        
        # Save Every slider
        save_frame = ttk.Frame(self.advanced_frame)
        save_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=(0, 8))
        save_frame.columnconfigure(0, weight=1)
        
        save_header = ttk.Frame(save_frame)
        save_header.grid(row=0, column=0, sticky=(tk.W, tk.E))
        save_header.columnconfigure(0, weight=1)
        
        ttk.Label(save_header, text="Save Every", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky=tk.W)
        self.save_reset_btn = ttk.Button(
            save_header, text="↺", width=3,
            command=lambda: self._reset_param("save_every")
        )
        self.save_reset_btn.grid(row=0, column=1, sticky=tk.E)
        
        ttk.Label(
            save_frame,
            text="Save checkpoint every N epochs (lower = more checkpoints to compare)",
            font=("Segoe UI", 8),
            foreground="gray"
        ).grid(row=1, column=0, sticky=tk.W)
        
        save_control = ttk.Frame(save_frame)
        save_control.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(3, 0))
        save_control.columnconfigure(0, weight=1)
        
        self.save_var = tk.IntVar(value=self.PARAM_SPECS["save_every"]["default"])
        self.save_slider = ttk.Scale(
            save_control,
            from_=self.PARAM_SPECS["save_every"]["min"],
            to=self.PARAM_SPECS["save_every"]["max"],
            variable=self.save_var,
            orient=tk.HORIZONTAL,
            command=lambda v: self._on_slider_changed("save_every", v)
        )
        self.save_slider.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.save_entry = ttk.Entry(save_control, width=8, justify=tk.CENTER)
        self.save_entry.grid(row=0, column=1)
        self.save_entry.insert(0, str(self.PARAM_SPECS["save_every"]["default"]))
        self.save_entry.bind("<Return>", lambda e: self._on_entry_changed("save_every"))
        self.save_entry.bind("<FocusOut>", lambda e: self._on_entry_changed("save_every"))
        
        ttk.Label(save_control, text="(25-100)").grid(row=0, column=2, padx=(5, 0))
    
    def _on_canvas_configure(self, event):
        """Handle canvas resize."""
        self.audio_canvas.itemconfig(self.audio_window, width=event.width)
    
    def _on_frame_configure(self, event):
        """Handle inner frame resize."""
        self.audio_canvas.configure(scrollregion=self.audio_canvas.bbox("all"))
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling."""
        self.audio_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def _validate_model_name(self, *args):
        """Validate and sanitize model name."""
        current = self.model_name_var.get()
        # Only allow alphanumeric and underscore
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '', current)
        if sanitized != current:
            self.model_name_var.set(sanitized)
    
    def _on_add_audio_clicked(self):
        """Handle Add Audio Files button click."""
        if self.is_training:
            return
        
        files = filedialog.askopenfilenames(
            title="Select Audio Files",
            filetypes=[
                ("Audio Files", "*.wav *.mp3 *.flac *.ogg *.m4a"),
                ("All Files", "*.*")
            ]
        )
        
        if not files:
            return
        
        for file_path in files:
            self._add_audio_file(Path(file_path))
    
    def _add_audio_file(self, file_path: Path):
        """Add an audio file to the list."""
        # Check if already added
        for item in self.audio_items:
            if item.file_path == file_path:
                logger.info(f"File already added: {file_path}")
                return
        
        # Create audio item
        item = AudioItem(
            item_id=self.next_item_id,
            file_path=file_path,
            display_name=file_path.name
        )
        self.next_item_id += 1
        
        # Add to list
        self.audio_items.append(item)
        
        # Hide empty label
        self.empty_label.grid_remove()
        
        # Create UI row
        self._create_audio_row(item)
        
        # Load duration async
        self._load_duration_async(item)
    
    def _create_audio_row(self, item: AudioItem):
        """Create UI row for an audio item."""
        row_idx = len(self.audio_items) - 1
        
        # Row frame
        frame = ttk.Frame(self.audio_inner_frame, padding=(5, 3))
        frame.grid(row=row_idx, column=0, sticky=(tk.W, tk.E), pady=2)
        frame.columnconfigure(1, weight=1)
        item.frame = frame
        
        # File name
        name_label = ttk.Label(
            frame,
            text=item.display_name,
            font=("Segoe UI", 9),
            width=25,
            anchor=tk.W
        )
        name_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        
        # Truncate long names
        if len(item.display_name) > 25:
            name_label.configure(text=item.display_name[:22] + "...")
        
        # Duration label
        duration_label = ttk.Label(
            frame,
            text="Loading...",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        duration_label.grid(row=0, column=1, sticky=tk.E, padx=(0, 10))
        item.duration_label = duration_label
        
        # Remove button
        remove_btn = ttk.Button(
            frame,
            text="✕",
            width=3,
            command=lambda i=item: self._remove_audio_file(i)
        )
        remove_btn.grid(row=0, column=2, sticky=tk.E)
    
    def _remove_audio_file(self, item: AudioItem):
        """Remove an audio file from the list."""
        if self.is_training:
            return
        
        # Remove from list
        if item in self.audio_items:
            self.audio_items.remove(item)
        
        # Destroy UI
        if item.frame:
            item.frame.destroy()
        
        # Rebuild rows
        self._rebuild_audio_rows()
        
        # Update total duration
        self._update_total_duration()
        
        # Show empty label if needed
        if not self.audio_items:
            self.empty_label.grid()
    
    def _rebuild_audio_rows(self):
        """Rebuild audio rows after removal."""
        for idx, item in enumerate(self.audio_items):
            if item.frame:
                item.frame.grid(row=idx, column=0, sticky=(tk.W, tk.E), pady=2)
    
    def _load_duration_async(self, item: AudioItem):
        """Load audio duration in background thread."""
        def load():
            try:
                if LIBROSA_AVAILABLE:
                    duration = librosa.get_duration(path=str(item.file_path))
                    item.duration_seconds = duration
                    self.after(0, lambda: self._on_duration_loaded(item))
                else:
                    self.after(0, lambda: self._on_duration_error(item, "librosa not available"))
            except Exception as e:
                self.after(0, lambda: self._on_duration_error(item, str(e)))
        
        thread = threading.Thread(target=load, daemon=True)
        thread.start()
    
    def _on_duration_loaded(self, item: AudioItem):
        """Handle duration loaded."""
        if item.duration_label:
            mins = int(item.duration_seconds // 60)
            secs = int(item.duration_seconds % 60)
            item.duration_label.configure(
                text=f"{mins}:{secs:02d}",
                foreground="black"
            )
        
        self._update_total_duration()
    
    def _on_duration_error(self, item: AudioItem, error: str):
        """Handle duration load error."""
        if item.duration_label:
            item.duration_label.configure(text="Error", foreground="red")
        logger.warning(f"Failed to load duration for {item.file_path}: {error}")
    
    def _update_total_duration(self):
        """Update total duration display."""
        total_seconds = sum(item.duration_seconds for item in self.audio_items)
        total_minutes = total_seconds / 60
        
        mins = int(total_seconds // 60)
        secs = int(total_seconds % 60)
        self.total_duration_var.set(f"Total: {mins}:{secs:02d}")
        
        # Update status indicator
        if total_minutes < 5:
            self.duration_status_var.set("⚠️ Not enough audio (min 10 min)")
            self.duration_status_label.configure(foreground="red")
        elif total_minutes < 10:
            self.duration_status_var.set("⚠️ Minimum viable")
            self.duration_status_label.configure(foreground="orange")
        elif total_minutes <= 30:
            self.duration_status_var.set("✓ Good to train!")
            self.duration_status_label.configure(foreground="green")
        else:
            self.duration_status_var.set("⚠️ May be excessive")
            self.duration_status_label.configure(foreground="orange")
    
    def _on_preset_changed(self, event=None):
        """Handle preset selection change."""
        preset = self.preset_var.get()
        if preset in TRAINING_PRESETS:
            params = TRAINING_PRESETS[preset]
            self.preset_desc_var.set(params["description"])
            
            # Update slider values if advanced is visible
            if self.use_advanced_var.get():
                self.epochs_var.set(params["epochs"])
                self.epochs_entry.delete(0, tk.END)
                self.epochs_entry.insert(0, str(params["epochs"]))
                
                self.batch_var.set(params["batch_size"])
                self.batch_entry.delete(0, tk.END)
                self.batch_entry.insert(0, str(params["batch_size"]))
                
                self.sr_var.set(params["sample_rate"])
                self.sr_entry.delete(0, tk.END)
                self.sr_entry.insert(0, str(params["sample_rate"]))
                
                self.save_var.set(params["save_every"])
                self.save_entry.delete(0, tk.END)
                self.save_entry.insert(0, str(params["save_every"]))
    
    def _on_advanced_toggled(self):
        """Handle advanced settings toggle."""
        if self.use_advanced_var.get():
            # Show advanced frame, hide preset
            self.preset_frame.grid_remove()
            self.advanced_frame.grid()
            
            # Apply preset values to sliders
            self._on_preset_changed()
        else:
            # Hide advanced frame, show preset
            self.advanced_frame.grid_remove()
            self.preset_frame.grid()
    
    def _on_slider_changed(self, param: str, value):
        """Handle slider value change."""
        # Round to step
        spec = self.PARAM_SPECS[param]
        int_value = int(round(float(value) / spec["step"]) * spec["step"])
        
        # Update entry
        entry = getattr(self, f"{param.split('_')[0]}_entry", None)
        if param == "batch_size":
            entry = self.batch_entry
        elif param == "sample_rate":
            entry = self.sr_entry
        elif param == "save_every":
            entry = self.save_entry
        else:
            entry = self.epochs_entry
        
        if entry:
            entry.delete(0, tk.END)
            entry.insert(0, str(int_value))
        
        # Update var to rounded value
        var = getattr(self, f"{param.split('_')[0]}_var", None)
        if param == "batch_size":
            var = self.batch_var
        elif param == "sample_rate":
            var = self.sr_var
        elif param == "save_every":
            var = self.save_var
        else:
            var = self.epochs_var
        
        if var:
            var.set(int_value)
    
    def _on_entry_changed(self, param: str):
        """Handle entry value change."""
        spec = self.PARAM_SPECS[param]
        
        # Get entry and var
        if param == "epochs":
            entry, var = self.epochs_entry, self.epochs_var
        elif param == "batch_size":
            entry, var = self.batch_entry, self.batch_var
        elif param == "sample_rate":
            entry, var = self.sr_entry, self.sr_var
        else:
            entry, var = self.save_entry, self.save_var
        
        try:
            value = int(entry.get())
            value = max(spec["min"], min(spec["max"], value))
            var.set(value)
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        except ValueError:
            # Reset to current var value
            entry.delete(0, tk.END)
            entry.insert(0, str(var.get()))
    
    def _reset_param(self, param: str):
        """Reset a parameter to default."""
        spec = self.PARAM_SPECS[param]
        default = spec["default"]
        
        if param == "epochs":
            self.epochs_var.set(default)
            self.epochs_entry.delete(0, tk.END)
            self.epochs_entry.insert(0, str(default))
        elif param == "batch_size":
            self.batch_var.set(default)
            self.batch_entry.delete(0, tk.END)
            self.batch_entry.insert(0, str(default))
        elif param == "sample_rate":
            self.sr_var.set(default)
            self.sr_entry.delete(0, tk.END)
            self.sr_entry.insert(0, str(default))
        elif param == "save_every":
            self.save_var.set(default)
            self.save_entry.delete(0, tk.END)
            self.save_entry.insert(0, str(default))
    
    def _on_train_clicked(self):
        """Handle Start Training button click."""
        if self.on_train:
            self.on_train()
    
    def _on_cancel_clicked(self):
        """Handle Cancel button click."""
        if self.on_cancel:
            self.on_cancel()
    
    # === Public API ===
    
    def get_model_name(self) -> str:
        """Get the model name."""
        return self.model_name_var.get().strip()
    
    def get_audio_files(self) -> List[Path]:
        """Get list of audio file paths."""
        return [item.file_path for item in self.audio_items]
    
    def get_total_duration_minutes(self) -> float:
        """Get total duration in minutes."""
        return sum(item.duration_seconds for item in self.audio_items) / 60
    
    def get_training_params(self) -> dict:
        """Get training parameters."""
        device = self.device_var.get()
        
        if self.use_advanced_var.get():
            return {
                "epochs": self.epochs_var.get(),
                "batch_size": self.batch_var.get(),
                "sample_rate": self.sr_var.get(),
                "save_every": self.save_var.get(),
                "device": device
            }
        else:
            preset = self.preset_var.get()
            params = TRAINING_PRESETS.get(preset, TRAINING_PRESETS[DEFAULT_PRESET])
            return {
                "epochs": params["epochs"],
                "batch_size": params["batch_size"],
                "sample_rate": params["sample_rate"],
                "save_every": params["save_every"],
                "device": device
            }
    
    def set_training_state(self, is_training: bool):
        """Set training state and update UI."""
        self.is_training = is_training
        
        if is_training:
            self.train_btn.configure(state=tk.DISABLED)
            self.cancel_btn.configure(state=tk.NORMAL)
            self.add_audio_btn.configure(state=tk.DISABLED)
            self.model_name_entry.configure(state=tk.DISABLED)
            self.preset_combo.configure(state=tk.DISABLED)
            self.device_combo.configure(state=tk.DISABLED)
            self.advanced_check.configure(state=tk.DISABLED)
        else:
            self.train_btn.configure(state=tk.NORMAL)
            self.cancel_btn.configure(state=tk.DISABLED)
            self.add_audio_btn.configure(state=tk.NORMAL)
            self.model_name_entry.configure(state=tk.NORMAL)
            self.preset_combo.configure(state="readonly")
            self.device_combo.configure(state="readonly")
            self.advanced_check.configure(state=tk.NORMAL)
