"""
Startup Dialog - Device selection dialog

Shows GPU/CPU detection and allows user to select processing device.
"""

import tkinter as tk
from tkinter import ttk


class StartupDialog:
    """Device selection dialog"""
    
    def __init__(self):
        self.selected_device = "cpu"
        self.result = None
        
        self.window = tk.Tk()
        self.window.title("Voice Revolver AI - Setup")
        
        # Center window on screen
        window_width = 500
        window_height = 500
        screen_width = self.window.winfo_screenwidth()
        screen_height = self.window.winfo_screenheight()
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.window.geometry(f"{window_width}x{window_height}+{x}+{y}")
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
                self.gpu_radio.config(text="GPU (No NVIDIA GPU found)", state="disabled")
                self._select_device("cpu")
                
        except OSError as e:
            # CUDA PyTorch installed but CUDA Toolkit missing
            if "caffe2_nvrtc.dll" in str(e) or "cudnn" in str(e).lower() or "cublas" in str(e).lower():
                self.gpu_label.config(text="GPU: RTX detected - CUDA Toolkit required")
                self.gpu_radio.config(text="GPU (Install CUDA Toolkit 11.8)", state="disabled")
                # Enable CPU and continue button
                self.selected_device = "cpu"
                self.device_selection.set("cpu")
                self.device_info.config(
                    text="⚠️ GPU needs CUDA Toolkit 11.8.\nDownload: developer.nvidia.com/cuda-11-8-0\nContinuing with CPU (slower but works).", 
                    foreground="#ff8800"
                )
                self.continue_btn.config(state="normal")
            else:
                raise  # Re-raise if it's a different OSError
                
        except Exception as e:
            self.gpu_label.config(text="GPU: Detection failed")
            self.gpu_radio.config(text="GPU (Detection failed)", state="disabled")
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
