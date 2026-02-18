"""
Compute Controller - Infrastructure Layer
Manages GPU/CPU device selection
"""

import os
from typing import Optional


class ComputeController:
    """
    Infrastructure component for compute device management.
    Auto-detects GPU availability and manages device selection.
    """
    
    def __init__(self):
        self._device: Optional[str] = None
        self._has_cuda = False
        self._check_cuda()
    
    def _check_cuda(self):
        """Check if CUDA is available"""
        try:
            import torch
            self._has_cuda = torch.cuda.is_available()
        except ImportError:
            self._has_cuda = False
    
    @property
    def has_gpu(self) -> bool:
        """Check if GPU is available"""
        return self._has_cuda
    
    @property
    def device(self) -> str:
        """Get current device"""
        if self._device is None:
            return self.get_suggested_device()
        return self._device
    
    def get_suggested_device(self) -> str:
        """Get suggested device based on hardware"""
        if self._has_cuda:
            return "cuda"
        return "cpu"
    
    def set_device(self, device: str) -> bool:
        """Manually set device (cuda/cpu)"""
        if device == "cuda" and not self._has_cuda:
            return False
        
        if device in ["cuda", "cpu"]:
            self._device = device
            return True
        
        return False
    
    def get_device_info(self) -> dict:
        """Get device information for UI"""
        info = {
            "has_cuda": self._has_cuda,
            "current_device": self.device,
            "suggested_device": self.get_suggested_device(),
        }
        
        if self._has_cuda:
            try:
                import torch
                info["cuda_device_name"] = torch.cuda.get_device_name(0)
                info["cuda_device_count"] = torch.cuda.device_count()
            except Exception:
                pass
        
        return info
    
    def reset_to_suggested(self):
        """Reset to suggested device"""
        self._device = None
