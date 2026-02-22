"""
Loading Dialog - Model loading and dependency checking dialog

Shows progress of FFmpeg setup and AI model downloads.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading

from voice_revolver_core.infrastructure.ffmpeg_checker import FFmpegChecker
from voice_revolver_core.infrastructure.model_manager import ModelManager


class LoadingDialog:
    """Model loading/download dialog"""
    
    def __init__(self, device, app_data_path):
        self.device = device
        self.app_data_path = app_data_path
        self.success = False
        self.error_message = ""
        
        self.window = tk.Tk()
        self.window.title("Voice Revolver AI - Loading")
        
        # Center window on screen
        window_width = 450
        window_height = 250
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.window.resizable(False, False)
        
        # Remove window decorations (no close/minimize buttons)
        self.window.overrideredirect(True)
        
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
                
                # Run async download in sync context
                import asyncio
                asyncio.run(model_manager.download_all_models(download_callback))
            
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
