"""
Model Manager - Infrastructure Layer
Manages AI model downloading and caching
"""

import os
from pathlib import Path
from typing import Optional, Callable
import asyncio


class ModelManager:
    """
    Infrastructure component for model management.
    Auto-downloads models on first run, caches for offline use.
    """
    
    # Model URLs (to be configured with actual URLs)
    DEMUCS_MODEL_URL = "https://dl.fbaipublicfiles.com/demucs/hdemucs_mix.yaml"
    DEMUCS_MODEL_PATHS = [
        "e98347006d8a8437e7102a539b92bbe6d891adab.th",  # htdemucs_ft
    ]
    
    OPENVOICE_MODEL_URL = "https://github.com/myshell-ai/OpenVoice/releases/download/v2.0.0/"
    
    def __init__(self, models_path: Path):
        self._models_path = models_path
        self._models_path.mkdir(parents=True, exist_ok=True)
        
        self._downloaded_models = set()
        self._download_callback: Optional[Callable[[str, float], None]] = None
    
    @property
    def models_path(self) -> Path:
        """Get models directory path"""
        return self._models_path
    
    def set_download_callback(self, callback: Callable[[str, float], None]):
        """Set callback for download progress"""
        self._download_callback = callback
    
    def is_model_cached(self, model_name: str) -> bool:
        """Check if model is already cached"""
        return model_name in self._downloaded_models
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get path to cached model"""
        model_path = self._models_path / model_name
        if model_path.exists():
            return model_path
        return None
    
    async def download_all_models(
        self, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Download all required models.
        Returns: (success, error_message)
        """
        models = [
            ("demucs", self._download_demucs_models),
            ("openvoice", self._download_openvoice_models),
        ]
        
        for model_name, download_func in models:
            try:
                success, error = await download_func(progress_callback)
                if not success:
                    return False, f"Failed to download {model_name}: {error}"
                self._downloaded_models.add(model_name)
            except Exception as e:
                return False, str(e)
        
        return True, None
    
    async def _download_demucs_models(
        self, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """Download Demucs models"""
        # Simulated download - actual implementation would use urllib or requests
        for i, model_file in enumerate(self.DEMUCS_MODEL_PATHS):
            self._notify_progress(f"demucs_{i}", (i + 1) / len(self.DEMUCS_MODEL_PATHS), progress_callback)
            await asyncio.sleep(0.5)  # Simulate download time
        
        return True, None
    
    async def _download_openvoice_models(
        self, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """Download OpenVoice models"""
        # Simulated download - actual implementation would download checkpoint
        self._notify_progress("openvoice", 0.5, progress_callback)
        await asyncio.sleep(0.5)
        
        return True, None
    
    def _notify_progress(
        self, 
        model_name: str, 
        progress: float, 
        callback: Optional[Callable[[str, float], None]]
    ):
        """Notify progress to callback"""
        if callback:
            callback(model_name, progress)
        if self._download_callback:
            self._download_callback(model_name, progress)
    
    def check_cache(self) -> dict:
        """Check which models are cached"""
        return {
            "demucs": "demucs" in self._downloaded_models,
            "openvoice": "openvoice" in self._downloaded_models,
        }
    
    def clear_cache(self) -> int:
        """Clear all cached models, return count deleted"""
        count = 0
        if self._models_path.exists():
            for file in self._models_path.iterdir():
                if file.is_file():
                    try:
                        file.unlink()
                        count += 1
                    except Exception:
                        pass
        
        self._downloaded_models.clear()
        return count
