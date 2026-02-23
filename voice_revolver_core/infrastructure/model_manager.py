"""
Model Manager - Infrastructure Layer
Manages AI model downloading and caching
"""

import os
import zipfile
from pathlib import Path
from typing import Optional, Callable
import asyncio
import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """
    Infrastructure component for model management.
    Auto-downloads models on first run, caches for offline use.
    """
    
    # OpenVoice V2 checkpoint URLs
    OPENVOICE_V2_CHECKPOINT_URL = "https://myshell-public-repo-host.s3.amazonaws.com/openvoice/checkpoints_v2_0417.zip"
    
    # Demucs model info (auto-downloaded by demucs package)
    DEMUCS_MODEL_NAME = "htdemucs_ft"
    
    # MDX model info (OPTIONAL - installed in separate venv-mdx)
    # See AGENT_MEMORY.md for MDX installation instructions
    MDX_MODEL_NAME = "MDX23C-8KFFT-InstVoc_HQ.ckpt"
    
    # RVC models are bundled with the portable app (not auto-downloaded)
    # Located in: rvc/models/pretraineds/, rvc/models/embedders/, rvc/models/predictors/
    
    def __init__(self, models_path: Path):
        self._models_path = models_path
        self._models_path.mkdir(parents=True, exist_ok=True)
        
        self._downloaded_models = set()
        self._download_callback: Optional[Callable[[str, float], None]] = None
        
        # Check what's already cached
        self._check_existing_cache()
    
    def _check_existing_cache(self):
        """Check what models are already cached"""
        # Check OpenVoice checkpoints
        openvoice_dir = self._models_path / "checkpoints_v2"
        if openvoice_dir.exists() and (openvoice_dir / "converter").exists():
            self._downloaded_models.add("openvoice")
            logger.info("OpenVoice V2 checkpoints found in cache")
        
        # Demucs models are downloaded by the package, we just check if package is available
        self._downloaded_models.add("demucs")
        
        # RVC models are bundled with the app (not auto-downloaded)
        # Embedders have their own wget download in rvc/lib/utils.py
        
        # MDX is optional (separate venv-mdx), not checked here
        # MDX availability is checked in mdx_wrapper.py at runtime
    
    @property
    def models_path(self) -> Path:
        """Get models directory path"""
        return self._models_path
    
    @property
    def openvoice_path(self) -> Path:
        """Get OpenVoice checkpoints directory"""
        return self._models_path / "checkpoints_v2"
    
    def set_download_callback(self, callback: Callable[[str, float], None]):
        """Set callback for download progress"""
        self._download_callback = callback
    
    def is_model_cached(self, model_name: str) -> bool:
        """Check if model is already cached"""
        return model_name in self._downloaded_models
    
    def get_model_path(self, model_name: str) -> Optional[Path]:
        """Get path to cached model"""
        if model_name == "openvoice":
            return self.openvoice_path
        elif model_name == "demucs":
            return self._models_path / "demucs"
        # MDX is in separate venv-mdx, not managed here
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
            ("openvoice", self._download_openvoice_models),
        ]
        
        # Demucs is handled by the demucs package - just mark as available
        self._downloaded_models.add("demucs")
        
        # RVC models are bundled with the app - no auto-download needed
        
        # MDX is optional (separate venv-mdx), not auto-downloaded
        
        for model_name, download_func in models:
            try:
                success, error = await download_func(progress_callback)
                if not success:
                    return False, f"Failed to download {model_name}: {error}"
                self._downloaded_models.add(model_name)
            except Exception as e:
                return False, str(e)
        
        return True, None
    
    async def _download_openvoice_models(
        self, 
        progress_callback: Optional[Callable[[str, float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Download OpenVoice V2 checkpoints from myshell S3.
        """
        import requests
        
        self._notify_progress("openvoice", 0.0, progress_callback)
        
        # Check if already downloaded
        openvoice_dir = self.openvoice_path
        if (openvoice_dir / "converter").exists() and (openvoice_dir / "base_speakers").exists():
            logger.info("OpenVoice V2 already cached")
            self._notify_progress("openvoice", 1.0, progress_callback)
            return True, None
        
        # Create temp download path
        zip_path = self._models_path / "checkpoints_v2.zip"
        
        try:
            # Download with progress tracking
            response = requests.get(self.OPENVOICE_V2_CHECKPOINT_URL, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            progress = downloaded / total_size
                            self._notify_progress("openvoice", progress * 0.8, progress_callback)
            
            # Extract zip
            self._notify_progress("openvoice", 0.85, progress_callback)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self._models_path)
            
            # Rename folder to checkpoints_v2 if needed
            extracted_dir = self._models_path / "checkpoints_v2"
            if not extracted_dir.exists():
                # Check if it was extracted with different name
                for item in self._models_path.iterdir():
                    if item.is_dir() and "checkpoints" in item.name.lower():
                        item.rename(self._models_path / "checkpoints_v2")
                        break
            
            # Clean up zip
            zip_path.unlink(missing_ok=True)
            
            self._notify_progress("openvoice", 1.0, progress_callback)
            logger.info("OpenVoice V2 checkpoints downloaded successfully")
            return True, None
            
        except Exception as e:
            logger.error(f"Failed to download OpenVoice V2: {e}")
            # Clean up partial download
            zip_path.unlink(missing_ok=True)
            return False, str(e)
    
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
            # RVC models bundled with app, MDX is optional
        }
    
    def clear_cache(self) -> int:
        """Clear all cached models, return count deleted"""
        count = 0
        if self._models_path.exists():
            for item in self._models_path.iterdir():
                try:
                    if item.is_file():
                        item.unlink()
                        count += 1
                    elif item.is_dir():
                        import shutil
                        shutil.rmtree(item)
                        count += 1
                except Exception:
                    pass
        
        self._downloaded_models.clear()
        return count
