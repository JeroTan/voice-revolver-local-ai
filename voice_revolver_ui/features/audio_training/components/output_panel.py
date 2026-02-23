"""Output panel for Audio Training workspace - Progress display and export."""

import tkinter as tk
from tkinter import ttk
from pathlib import Path
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class OutputPanel(ttk.Frame):
    """Right panel with training progress and export controls."""
    
    # Training steps
    STEPS = [
        ("Preprocessing audio", "preprocess"),
        ("Extracting features", "extract"),
        ("Training model", "train"),
        ("Building index", "index")
    ]
    
    def __init__(
        self,
        parent: ttk.Frame,
        on_export: Optional[Callable] = None,
        **kwargs
    ):
        """Initialize the output panel.
        
        Args:
            parent: Parent widget
            on_export: Callback when Export is clicked
        """
        super().__init__(parent, padding=10, **kwargs)
        
        self.on_export = on_export
        
        # State
        self.current_step = 0
        self.is_training = False
        self.output_path: Optional[Path] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Set up the UI components."""
        # Configure grid
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)  # Progress section expands
        
        row = 0
        
        # === Title ===
        title_label = ttk.Label(
            self,
            text="Training Progress",
            font=("Segoe UI", 14, "bold")
        )
        title_label.grid(row=row, column=0, sticky=tk.W, pady=(0, 10))
        row += 1
        
        # === Progress Section ===
        progress_frame = ttk.LabelFrame(self, text="Status", padding=15)
        progress_frame.grid(row=row, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        progress_frame.columnconfigure(1, weight=1)
        
        # Step indicators
        self.step_labels = []
        self.step_status_labels = []
        
        for idx, (step_name, step_key) in enumerate(self.STEPS):
            # Step number
            step_num_label = ttk.Label(
                progress_frame,
                text=f"Step {idx + 1}/{len(self.STEPS)}:",
                font=("Segoe UI", 9)
            )
            step_num_label.grid(row=idx, column=0, sticky=tk.W, pady=5)
            
            # Step name
            step_label = ttk.Label(
                progress_frame,
                text=step_name,
                font=("Segoe UI", 9)
            )
            step_label.grid(row=idx, column=1, sticky=tk.W, padx=(10, 0), pady=5)
            self.step_labels.append(step_label)
            
            # Status indicator
            status_label = ttk.Label(
                progress_frame,
                text="○",
                font=("Segoe UI", 10),
                foreground="gray"
            )
            status_label.grid(row=idx, column=2, sticky=tk.E, padx=(10, 0), pady=5)
            self.step_status_labels.append(status_label)
        
        # Separator
        separator = ttk.Separator(progress_frame, orient=tk.HORIZONTAL)
        separator.grid(row=len(self.STEPS), column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Current details frame
        details_frame = ttk.Frame(progress_frame)
        details_frame.grid(row=len(self.STEPS) + 1, column=0, columnspan=3, sticky=(tk.W, tk.E))
        details_frame.columnconfigure(1, weight=1)
        
        # Current epoch
        ttk.Label(details_frame, text="Epoch:", font=("Segoe UI", 9)).grid(row=0, column=0, sticky=tk.W, pady=2)
        self.epoch_var = tk.StringVar(value="--")
        self.epoch_label = ttk.Label(details_frame, textvariable=self.epoch_var, font=("Segoe UI", 9))
        self.epoch_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Loss
        ttk.Label(details_frame, text="Loss:", font=("Segoe UI", 9)).grid(row=1, column=0, sticky=tk.W, pady=2)
        self.loss_var = tk.StringVar(value="--")
        self.loss_label = ttk.Label(details_frame, textvariable=self.loss_var, font=("Segoe UI", 9))
        self.loss_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # ETA
        ttk.Label(details_frame, text="ETA:", font=("Segoe UI", 9)).grid(row=2, column=0, sticky=tk.W, pady=2)
        self.eta_var = tk.StringVar(value="--")
        self.eta_label = ttk.Label(details_frame, textvariable=self.eta_var, font=("Segoe UI", 9))
        self.eta_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=2)
        
        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            mode='determinate'
        )
        self.progress_bar.grid(row=len(self.STEPS) + 2, column=0, columnspan=3, 
                               sticky=(tk.W, tk.E), pady=(15, 5))
        
        # Progress percentage label
        self.progress_text_var = tk.StringVar(value="0%")
        self.progress_text_label = ttk.Label(
            progress_frame,
            textvariable=self.progress_text_var,
            font=("Segoe UI", 9),
            foreground="gray"
        )
        self.progress_text_label.grid(row=len(self.STEPS) + 3, column=0, columnspan=3, sticky=tk.W)
        
        # Message label
        self.message_var = tk.StringVar(value="Ready to train")
        self.message_label = ttk.Label(
            progress_frame,
            textvariable=self.message_var,
            font=("Segoe UI", 9),
            wraplength=350
        )
        self.message_label.grid(row=len(self.STEPS) + 4, column=0, columnspan=3, 
                                sticky=tk.W, pady=(10, 0))
        
        row += 1
        
        # === Output Section ===
        output_frame = ttk.LabelFrame(self, text="Output", padding=10)
        output_frame.grid(row=row, column=0, sticky=(tk.W, tk.E), pady=(0, 10))
        output_frame.columnconfigure(0, weight=1)
        
        # Output path display
        self.output_path_var = tk.StringVar(value="No model trained yet")
        self.output_path_label = ttk.Label(
            output_frame,
            textvariable=self.output_path_var,
            font=("Segoe UI", 9),
            foreground="gray",
            wraplength=350
        )
        self.output_path_label.grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        # Export button
        self.export_btn = ttk.Button(
            output_frame,
            text="Export Model (.zip)",
            command=self._on_export_clicked,
            state=tk.DISABLED
        )
        self.export_btn.grid(row=1, column=0, sticky=(tk.W, tk.E))
        
        row += 1
        
        # === Info Section ===
        info_frame = ttk.LabelFrame(self, text="Info", padding=10)
        info_frame.grid(row=row, column=0, sticky=(tk.W, tk.E))
        
        info_text = (
            "The trained model will be a .zip file containing:\n"
            "• .pth file - The neural network weights\n"
            "• .index file - Voice feature database\n\n"
            "Use this model in the Voice Cloning workspace\n"
            "by selecting it as an RVC model reference."
        )
        
        info_label = ttk.Label(
            info_frame,
            text=info_text,
            font=("Segoe UI", 8),
            foreground="gray",
            justify=tk.LEFT
        )
        info_label.grid(row=0, column=0, sticky=tk.W)
    
    def _on_export_clicked(self):
        """Handle Export button click."""
        if self.on_export:
            self.on_export()
    
    # === Public API ===
    
    def reset_progress(self):
        """Reset progress display."""
        self.current_step = 0
        
        # Reset step indicators
        for status_label in self.step_status_labels:
            status_label.configure(text="○", foreground="gray")
        
        # Reset details
        self.epoch_var.set("--")
        self.loss_var.set("--")
        self.eta_var.set("Calculating...")
        
        # Reset progress
        self.progress_var.set(0)
        self.progress_text_var.set("0%")
        self.message_var.set("Starting...")
        
        # Reset output
        self.output_path = None
        self.output_path_var.set("Training in progress...")
        self.export_btn.configure(state=tk.DISABLED)
    
    def update_progress(self, percent: float, message: str):
        """Update progress display.
        
        Args:
            percent: Progress percentage (0-100)
            message: Status message
        """
        self.progress_var.set(percent)
        self.progress_text_var.set(f"{int(percent)}%")
        self.message_var.set(message)
        
        # Update step indicators based on progress
        if percent < 25:
            self._set_step_status(0, "in_progress")
        elif percent < 50:
            self._set_step_status(0, "complete")
            self._set_step_status(1, "in_progress")
        elif percent < 90:
            self._set_step_status(0, "complete")
            self._set_step_status(1, "complete")
            self._set_step_status(2, "in_progress")
            
            # Parse epoch from message
            if "Epoch" in message:
                self.epoch_var.set(message.split("Epoch")[-1].strip().split()[0] if "Epoch" in message else "--")
        elif percent < 100:
            self._set_step_status(0, "complete")
            self._set_step_status(1, "complete")
            self._set_step_status(2, "complete")
            self._set_step_status(3, "in_progress")
        else:
            for i in range(4):
                self._set_step_status(i, "complete")
    
    def _set_step_status(self, step_idx: int, status: str):
        """Set step status indicator.
        
        Args:
            step_idx: Step index (0-3)
            status: "pending", "in_progress", or "complete"
        """
        if step_idx >= len(self.step_status_labels):
            return
        
        label = self.step_status_labels[step_idx]
        
        if status == "pending":
            label.configure(text="○", foreground="gray")
        elif status == "in_progress":
            label.configure(text="▶", foreground="blue")
        elif status == "complete":
            label.configure(text="✓", foreground="green")
        elif status == "failed":
            label.configure(text="✕", foreground="red")
    
    def set_training_state(self, is_training: bool):
        """Set training state."""
        self.is_training = is_training
        
        if is_training:
            self.export_btn.configure(state=tk.DISABLED)
    
    def set_training_complete(self, output_path: Path):
        """Set training complete state.
        
        Args:
            output_path: Path to the output zip file
        """
        self.output_path = output_path
        self.output_path_var.set(f"Model ready: {output_path.name}")
        self.output_path_label.configure(foreground="green")
        self.export_btn.configure(state=tk.NORMAL)
        
        # Update all steps to complete
        for i in range(4):
            self._set_step_status(i, "complete")
        
        self.epoch_var.set("Complete")
        self.eta_var.set("--")
        self.message_var.set("Training complete! Click 'Export' to save the model.")
    
    def set_training_failed(self, error: str):
        """Set training failed state.
        
        Args:
            error: Error message
        """
        self.output_path = None
        self.output_path_var.set("Training failed")
        self.output_path_label.configure(foreground="red")
        
        self.message_var.set(f"Error: {error[:100]}")
        self.message_label.configure(foreground="red")
        
        # Mark current step as failed
        for i, status_label in enumerate(self.step_status_labels):
            if status_label.cget("text") == "▶":
                self._set_step_status(i, "failed")
                break
