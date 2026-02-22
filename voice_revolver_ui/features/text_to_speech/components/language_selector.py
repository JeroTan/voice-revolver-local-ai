"""
Language Selector - TTS Component
Searchable dropdown for language selection
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Optional, Callable


class LanguageSelector(ttk.Frame):
    """Searchable language dropdown with filtering"""
    
    def __init__(
        self,
        parent,
        languages_dict: Dict[str, str],
        default: str = "en",
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize language selector.
        
        Args:
            parent: Parent widget
            languages_dict: Dict mapping language codes to display names
            default: Default language code
            on_change: Optional callback when language changes(lang_code)
        """
        super().__init__(parent, **kwargs)
        
        self.languages_dict = languages_dict
        self.on_change_callback = on_change
        
        # Current selection
        self.lang_var = tk.StringVar(value=default)
        
        # Create sorted list of display names with codes
        self.lang_items = sorted(
            [(code, name) for code, name in languages_dict.items()],
            key=lambda x: x[1]  # Sort by display name
        )
        self.display_names = [name for _, name in self.lang_items]
        
        self._setup_ui()
        
        # Set initial value
        self._set_display_value(default)
    
    def _setup_ui(self):
        """Create UI components"""
        # Label
        label = ttk.Label(self, text="Language:")
        label.grid(row=0, column=0, padx=(0, 10), sticky=tk.W)
        
        # Combobox with search
        self.combobox = ttk.Combobox(
            self,
            values=self.display_names,
            state="readonly",
            width=25
        )
        self.combobox.grid(row=0, column=1, sticky=(tk.W, tk.E))
        self.combobox.bind("<<ComboboxSelected>>", self._on_selection)
        
        self.columnconfigure(1, weight=1)
    
    def _set_display_value(self, lang_code: str):
        """Set combobox to show language name for given code"""
        if lang_code in self.languages_dict:
            display_name = self.languages_dict[lang_code]
            self.combobox.set(display_name)
    
    def _on_selection(self, event=None):
        """Handle combobox selection"""
        display_name = self.combobox.get()
        
        # Find language code for selected display name
        for code, name in self.lang_items:
            if name == display_name:
                old_value = self.lang_var.get()
                self.lang_var.set(code)
                
                # Notify callback if value changed
                if code != old_value and self.on_change_callback:
                    self.on_change_callback(code)
                break
    
    def get_language_code(self) -> str:
        """Get currently selected language code"""
        return self.lang_var.get()
    
    def get_language_name(self) -> str:
        """Get currently selected language display name"""
        code = self.lang_var.get()
        return self.languages_dict.get(code, code)
    
    def set_enabled(self, enabled: bool):
        """Enable/disable the selector"""
        state = 'readonly' if enabled else 'disabled'
        self.combobox.config(state=state)
