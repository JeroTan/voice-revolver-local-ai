"""
Labeled Slider Component

A reusable slider widget with label and value display.
Used for numeric input with visual feedback.
"""

import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional, Union


class LabeledSlider(ttk.Frame):
    """A slider with label and value display.
    
    Features:
    - Label text on the left
    - Slider in the middle
    - Value display on the right
    - Customizable value formatting
    - Optional callback on value change
    """
    
    def __init__(
        self,
        parent,
        label: str,
        from_: float,
        to: float,
        initial_value: float = 0,
        orient: str = tk.HORIZONTAL,
        length: int = 150,
        value_format: Union[str, Callable[[float], str]] = "{:.0f}",
        on_change: Optional[Callable[[float], None]] = None,
        **kwargs
    ):
        """Initialize the labeled slider.
        
        Args:
            parent: Parent tkinter widget
            label: Text label to display
            from_: Minimum value
            to: Maximum value
            initial_value: Starting value (default: 0)
            orient: Slider orientation (tk.HORIZONTAL or tk.VERTICAL)
            length: Slider length in pixels (default: 150)
            value_format: Format string or callable for value display
                         e.g., "{:.0f} dB", "{:.2f}", lambda v: f"{int(v)} semitones"
            on_change: Optional callback when value changes (receives float value)
            **kwargs: Additional configuration for the Frame
        """
        super().__init__(parent, **kwargs)
        
        self.label_text = label
        self.value_format = value_format
        self.on_change_callback = on_change
        
        # Create variable
        self.var = tk.DoubleVar(value=initial_value)
        
        # Setup UI
        self._setup_ui(from_, to, orient, length)
        
        # Update initial value display
        self._on_value_change(initial_value)
    
    def _setup_ui(self, from_: float, to: float, orient: str, length: int):
        """Create and layout child widgets."""
        # Configure grid columns
        self.columnconfigure(1, weight=1)
        
        # Label
        self.label_widget = ttk.Label(self, text=self.label_text)
        self.label_widget.grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        # Slider
        self.slider = ttk.Scale(
            self,
            from_=from_,
            to=to,
            variable=self.var,
            orient=orient,
            length=length,
            command=self._on_value_change
        )
        self.slider.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        # Value display
        self.value_label = ttk.Label(self, text="")
        self.value_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
    
    def _on_value_change(self, value):
        """Handle slider value changes."""
        try:
            value_float = float(value)
            
            # Format value for display
            if callable(self.value_format):
                display_text = self.value_format(value_float)
            else:
                display_text = self.value_format.format(value_float)
            
            self.value_label.config(text=display_text)
            
            # Call external callback if provided
            if self.on_change_callback:
                self.on_change_callback(value_float)
                
        except (ValueError, TypeError) as e:
            # If formatting fails, display raw value
            self.value_label.config(text=str(value))
    
    def get(self) -> float:
        """Get current slider value."""
        return self.var.get()
    
    def set(self, value: float):
        """Set slider value."""
        self.var.set(value)
    
    def configure_slider(self, **kwargs):
        """Configure the slider widget."""
        self.slider.config(**kwargs)
    
    def configure_label(self, **kwargs):
        """Configure the label widget."""
        self.label_widget.config(**kwargs)
    
    def configure_value_display(self, **kwargs):
        """Configure the value display widget."""
        self.value_label.config(**kwargs)
