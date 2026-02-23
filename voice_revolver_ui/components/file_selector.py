"""
File Selector Component

A reusable file/folder selection widget with browse button.
Used for file path input with file dialog support.
"""

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Callable, Optional, Tuple


class FileSelector(ttk.Frame):
    """A file/folder selector with label, entry field, and browse button.
    
    Features:
    - Label text
    - Entry field showing selected path
    - Browse button to open file dialog
    - Support for file or folder selection
    - Optional file type filters
    - Optional callback on selection
    """
    
    def __init__(
        self,
        parent,
        label: str,
        mode: str = "file",  # "file" or "folder"
        file_types: Optional[Tuple[Tuple[str, str], ...]] = None,
        initial_path: str = "",
        on_select: Optional[Callable[[str], None]] = None,
        entry_width: int = 40,
        **kwargs
    ):
        """Initialize the file selector.
        
        Args:
            parent: Parent tkinter widget
            label: Text label to display
            mode: Selection mode - "file" or "folder"
            file_types: File type filters for file mode, e.g.,
                       (("Audio Files", "*.wav *.mp3"), ("All Files", "*.*"))
            initial_path: Initial path to display (default: "")
            on_select: Optional callback when file/folder is selected (receives path string)
            entry_width: Width of the entry field (default: 40)
            **kwargs: Additional configuration for the Frame
        """
        super().__init__(parent, **kwargs)
        
        self.label_text = label
        self.mode = mode
        self.file_types = file_types or (("All Files", "*.*"),)
        self.on_select_callback = on_select
        self.entry_width = entry_width
        
        # Create variable
        self.path_var = tk.StringVar(value=initial_path)
        
        # Setup UI
        self._setup_ui()
    
    def _setup_ui(self):
        """Create and layout child widgets."""
        # Configure grid columns
        self.columnconfigure(1, weight=1)
        
        # Label
        self.label_widget = ttk.Label(self, text=self.label_text)
        self.label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        # Entry field
        self.entry = ttk.Entry(self, textvariable=self.path_var, width=self.entry_width)
        self.entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Browse button
        self.browse_btn = ttk.Button(self, text="Browse...", command=self._browse)
        self.browse_btn.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
    
    def _browse(self):
        """Open file/folder dialog and update entry."""
        try:
            if self.mode == "folder":
                path = filedialog.askdirectory(title=f"Select {self.label_text}")
            else:  # file mode
                path = filedialog.askopenfilename(
                    title=f"Select {self.label_text}",
                    filetypes=self.file_types
                )
            
            if path:  # User selected something (didn't cancel)
                self.path_var.set(path)
                
                # Call external callback if provided
                if self.on_select_callback:
                    self.on_select_callback(path)
                    
        except Exception as e:
            # Silently handle dialog errors
            print(f"File dialog error: {e}")
    
    def get(self) -> str:
        """Get current path."""
        return self.path_var.get()
    
    def set(self, path: str):
        """Set path value."""
        self.path_var.set(path)
    
    def clear(self):
        """Clear the path."""
        self.path_var.set("")
    
    def configure_entry(self, **kwargs):
        """Configure the entry widget."""
        self.entry.config(**kwargs)
    
    def configure_button(self, **kwargs):
        """Configure the browse button."""
        self.browse_btn.config(**kwargs)
    
    def configure_label(self, **kwargs):
        """Configure the label widget."""
        self.label_widget.config(**kwargs)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable the file selector."""
        state = 'normal' if enabled else 'disabled'
        self.entry.config(state=state)
        self.browse_btn.config(state=state)
    
    def set_file_types(self, file_types: Tuple[Tuple[str, str], ...]):
        """Update file type filters (for file mode only).
        
        Args:
            file_types: New file type filters, e.g.,
                       (("Audio Files", "*.wav *.mp3"), ("All Files", "*.*"))
        """
        self.file_types = file_types
