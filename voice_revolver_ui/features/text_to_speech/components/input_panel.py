"""
Input Panel - TTS Component
Text input and parameter controls for TTS generation
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from pathlib import Path
from typing import Optional, Callable, Tuple
import logging
import json

from voice_revolver_ui.components.file_selector import FileSelector
from voice_revolver_ui.components.labeled_slider import LabeledSlider
from voice_revolver_ui.features.text_to_speech.components.language_selector import LanguageSelector
from voice_revolver_core.infrastructure.chatterbox_tts_wrapper import ChatterBoxTTSWrapper

logger = logging.getLogger(__name__)


class InputPanel(ttk.Frame):
    """Input panel for TTS controls"""
    
    def __init__(
        self,
        parent,
        device: str = "cpu",
        on_generate: Optional[Callable] = None,
        **kwargs
    ):
        """
        Initialize input panel.
        
        Args:
            parent: Parent widget
            device: Device to use (cpu/cuda)
            on_generate: Callback when Generate clicked
        """
        super().__init__(parent, **kwargs)
        
        self.device = device
        self.on_generate_callback = on_generate
        
        # Control variables
        self.use_default_voice_var = tk.BooleanVar(value=False)  # Default: use reference
        self.use_turbo_var = tk.BooleanVar(value=False)  # Default: MTL mode
        self.hf_token_var = tk.StringVar(value="")  # HuggingFace token for Turbo
        
        # Config file path for persistent token storage
        self.config_path = Path.home() / ".voice_revolver" / "config.json"
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load saved token
        self._load_token()
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Create UI components"""
        # Configure grid
        self.columnconfigure(0, weight=1)
        
        row = 0
        
        # === Text Input Area ===
        text_frame = ttk.LabelFrame(self, text="Text to Synthesize", padding=10)
        text_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        self.text_area = scrolledtext.ScrolledText(
            text_frame,
            wrap=tk.WORD,
            width=40,
            height=10,
            font=("Segoe UI", 10)
        )
        self.text_area.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.text_area.insert("1.0", "Enter text here to generate speech...")
        self.text_area.bind("<FocusIn>", self._on_text_focus)
        
        row += 1
        
        # === Parameter Controls ===
        params_frame = ttk.LabelFrame(self, text="Parameters", padding=10)
        params_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        params_frame.columnconfigure(0, weight=1)
        
        param_row = 0
        
        # Use Default Voice checkbox
        self.default_voice_check = ttk.Checkbutton(
            params_frame,
            text="Use Default Voice",
            variable=self.use_default_voice_var,
            command=self._on_default_voice_changed
        )
        self.default_voice_check.grid(row=param_row, column=0, sticky=tk.W, pady=(0, 5))
        param_row += 1
        
        # Reference Audio selector
        self.file_selector = FileSelector(
            params_frame,
            label="Reference Audio:",
            mode="file",
            file_types=(
                ("Audio Files", "*.wav *.mp3 *.flac"),
                ("All Files", "*.*")
            ),
            entry_width=35
        )
        self.file_selector.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=5)
        param_row += 1
        
        # Language selector
        self.language_selector = LanguageSelector(
            params_frame,
            languages_dict=ChatterBoxTTSWrapper.get_supported_languages(),
            default="en",
            on_change=self._on_language_changed
        )
        self.language_selector.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=5)
        param_row += 1
        
        # Use Improve Quality checkbox (English only - uses ChatterBoxTTS instead of MTL)
        self.turbo_check = ttk.Checkbutton(
            params_frame,
            text="Use Turbo to Improve Quality",
            variable=self.use_turbo_var,
            command=self._on_turbo_changed
        )
        self.turbo_check.grid(row=param_row, column=0, sticky=tk.W, pady=(5, 2))
        param_row += 1
        
        # Turbo availability note
        ttk.Label(
            params_frame,
            text="(Only available for English)",
            foreground="gray",
            font=("Segoe UI", 8)
        ).grid(row=param_row, column=0, sticky=tk.W, padx=(20, 0), pady=(0, 5))
        param_row += 1
        
        # HuggingFace Token input (for Turbo model)
        token_frame = ttk.Frame(params_frame)
        token_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), padx=(20, 0), pady=(0, 5))
        param_row += 1
        
        ttk.Label(token_frame, text="HuggingFace Token:", foreground="gray").pack(side=tk.LEFT)
        self.token_entry = ttk.Entry(
            token_frame,
            textvariable=self.hf_token_var,
            width=30,
            show="*",  # Hide token like password
            state='disabled'  # Start disabled (enabled when Turbo is checked)
        )
        self.token_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)
        
        # Token save button
        self.save_token_btn = ttk.Button(
            token_frame,
            text="Save",
            command=self._save_token,
            width=6,
            state='disabled'  # Start disabled
        )
        self.save_token_btn.pack(side=tk.LEFT, padx=(5, 0))
        
        # Token note
        ttk.Label(
            params_frame,
            text="A token is required to run Turbo",
            foreground="gray",
            font=("Segoe UI", 8)
        ).grid(row=param_row, column=0, sticky=tk.W, padx=(20, 0), pady=(0, 5))
        param_row += 1
        
        # Quality status label
        self.quality_label = ttk.Label(
            params_frame,
            text="",
            foreground="gray",
            font=("Segoe UI", 8)
        )
        self.quality_label.grid(row=param_row, column=0, sticky=tk.W, padx=(20, 0))
        param_row += 1
        
        # Separator
        ttk.Separator(params_frame, orient=tk.HORIZONTAL).grid(
            row=param_row, column=0, sticky=(tk.W, tk.E), pady=10
        )
        param_row += 1
        
        # Energy slider (exaggeration)
        self.energy_slider = LabeledSlider(
            params_frame,
            label="Energy:",
            from_=0.0,
            to=1.0,
            initial_value=0.7,
            value_format="{:.2f}",
            length=200
        )
        self.energy_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Speed slider (cfg_weight)
        self.speed_slider = LabeledSlider(
            params_frame,
            label="Speed:",
            from_=0.0,
            to=1.0,
            initial_value=0.4,
            value_format="{:.2f}",
            length=200
        )
        self.speed_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Variation slider (temperature)
        self.variation_slider = LabeledSlider(
            params_frame,
            label="Variation:",
            from_=0.1,
            to=1.5,
            initial_value=0.9,
            value_format="{:.2f}",
            length=200
        )
        self.variation_slider.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=3)
        param_row += 1
        
        # Generate Controls (Device + Button)
        ttk.Separator(params_frame, orient=tk.HORIZONTAL).grid(
            row=param_row, column=0, sticky=(tk.W, tk.E), pady=10
        )
        param_row += 1
        
        generate_control_frame = ttk.Frame(params_frame)
        generate_control_frame.grid(row=param_row, column=0, sticky=(tk.W, tk.E), pady=5)
        generate_control_frame.columnconfigure(1, weight=1)
        
        # Device dropdown
        ttk.Label(generate_control_frame, text="Device:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.device_var = tk.StringVar(value=self.device)
        self.device_combo = ttk.Combobox(
            generate_control_frame,
            textvariable=self.device_var,
            values=["cpu", "cuda"],
            state="readonly",
            width=10
        )
        self.device_combo.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        # Generate button (sticks to right)
        self.generate_btn = ttk.Button(
            generate_control_frame,
            text="🎤 Generate Speech",
            command=self._on_generate_clicked,
            style='Accent.TButton'
        )
        self.generate_btn.grid(row=0, column=2, sticky=tk.E, padx=(10, 0))
        
        # Make text area expand
        self.rowconfigure(0, weight=1)
    
    def _on_text_focus(self, event):
        """Clear placeholder text on focus"""
        current_text = self.text_area.get("1.0", tk.END).strip()
        if current_text == "Enter text here to generate speech...":
            self.text_area.delete("1.0", tk.END)
    
    def _on_generate_clicked(self):
        """Handle generate button click"""
        if self.on_generate_callback:
            self.on_generate_callback()
    
    def _on_default_voice_changed(self):
        """Handle default voice checkbox change"""
        use_default = self.use_default_voice_var.get()
        self.file_selector.set_enabled(not use_default)
    
    def _on_language_changed(self, language_code: str):
        """Handle language change - enable/disable turbo mode"""
        if language_code == "en":
            # English: enable turbo option
            self.turbo_check.config(state="normal")
            self._update_quality_label()
        else:
            # Other languages: disable turbo
            self.turbo_check.config(state="disabled")
            self.use_turbo_var.set(False)
            self.quality_label.config(
                text="English Model: Not available for other languages",
                foreground="gray"
            )
    
    def _on_turbo_changed(self):
        """Handle turbo checkbox change"""
        # Update quality label
        self._update_quality_label()
        
        # Enable/disable token field based on turbo checkbox
        token_state = 'normal' if self.use_turbo_var.get() else 'disabled'
        self.token_entry.config(state=token_state)
        self.save_token_btn.config(state=token_state)
    
    def _update_quality_label(self):
        """Update quality status label"""
        if self.use_turbo_var.get():
            self.quality_label.config(
                text="Turbo mode enabled",
                foreground="green"
            )
        else:
            self.quality_label.config(text="", foreground="gray")
    
    def get_text(self) -> str:
        """Get text from text area"""
        text = self.text_area.get("1.0", tk.END).strip()
        if text == "Enter text here to generate speech...":
            return ""
        return text
    
    def get_language(self) -> str:
        """Get selected language code"""
        return self.language_selector.get_language_code()
    
    def get_reference_audio(self) -> Optional[Path]:
        """Get reference audio path"""
        path_str = self.file_selector.path_var.get()
        if path_str:
            return Path(path_str)
        return None
    
    def get_use_default_voice(self) -> bool:
        """Check if using default voice"""
        return self.use_default_voice_var.get()
    
    def get_device(self) -> str:
        """Get selected device"""
        return self.device_var.get()
    
    def get_use_turbo(self) -> bool:
        """Check if using turbo mode"""
        return self.use_turbo_var.get()
    
    def get_exaggeration(self) -> float:
        """Get energy/exaggeration value"""
        return self.energy_slider.var.get()
    
    def get_cfg_weight(self) -> float:
        """Get speed/cfg_weight value"""
        return self.speed_slider.var.get()
    
    def get_temperature(self) -> float:
        """Get variation/temperature value"""
        return self.variation_slider.var.get()
    
    def validate(self) -> Tuple[bool, str]:
        """
        Validate inputs before generation.
        
        Returns:
            (is_valid, error_message)
        """
        # Check text
        text = self.get_text()
        if not text:
            return False, "Please enter text to synthesize"
        
        # Check HuggingFace token if using Turbo mode
        if self.use_turbo_var.get():
            token = self.get_hf_token()
            if not token:
                return False, "Please enter HuggingFace token for Turbo model (get free token from https://huggingface.co/settings/tokens)"
        
        # Check reference audio if not using default
        if not self.use_default_voice_var.get():
            ref_path = self.get_reference_audio()
            if not ref_path:
                return False, "Please select reference audio or check 'Use Default Voice'"
            
            if not ref_path.exists():
                return False, f"Reference audio file not found: {ref_path}"
        
        return True, ""
    
    def set_enabled(self, enabled: bool):
        """Enable/disable all controls"""
        state = 'normal' if enabled else 'disabled'
        
        self.text_area.config(state=state)
        self.default_voice_check.config(state=state)
        self.file_selector.set_enabled(enabled and not self.use_default_voice_var.get())
        self.language_selector.set_enabled(enabled)
        
        # Turbo checkbox only if English and enabled
        if enabled and self.get_language() == "en":
            self.turbo_check.config(state='normal')
        else:
            self.turbo_check.config(state='disabled')
        
        # Token field - enabled only when Turbo is checked
        token_state = 'normal' if (enabled and self.use_turbo_var.get()) else 'disabled'
        self.token_entry.config(state=token_state)
        self.save_token_btn.config(state=token_state)
        
        # Device dropdown and Generate button
        self.device_combo.config(state='readonly' if enabled else 'disabled')
        self.generate_btn.config(state=state)
        
        # Sliders and their controls
        self.energy_slider.slider.config(state=state)
        self.energy_slider.value_entry.config(state=state)
        self.energy_slider.reset_btn.config(state=state)
        
        self.speed_slider.slider.config(state=state)
        self.speed_slider.value_entry.config(state=state)
        self.speed_slider.reset_btn.config(state=state)
        
        self.variation_slider.slider.config(state=state)
        self.variation_slider.value_entry.config(state=state)
        self.variation_slider.reset_btn.config(state=state)
    
    def get_hf_token(self) -> Optional[str]:
        """Get HuggingFace token for Turbo model"""
        token = self.hf_token_var.get().strip()
        return token if token else None
    
    def _load_token(self):
        """Load saved HuggingFace token from config file"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    token = config.get('hf_token', '')
                    if token:
                        self.hf_token_var.set(token)
                        logger.info("Loaded saved HuggingFace token")
        except Exception as e:
            logger.warning(f"Failed to load token from config: {e}")
    
    def _save_token(self):
        """Save HuggingFace token to config file"""
        try:
            token = self.hf_token_var.get().strip()
            
            # Load existing config or create new
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
            
            # Update token
            config['hf_token'] = token
            
            # Save config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info("HuggingFace token saved successfully")
            
            # Show feedback
            original_text = self.save_token_btn.config('text')[-1]
            self.save_token_btn.config(text="✓ Saved")
            self.after(2000, lambda: self.save_token_btn.config(text=original_text))
            
        except Exception as e:
            logger.error(f"Failed to save token: {e}")
