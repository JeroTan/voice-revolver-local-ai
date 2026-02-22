"""
Model Downloader - One-time HuggingFace authentication and model caching
Handles downloading ChatterBox TTS models with user-friendly authentication flow
"""

from pathlib import Path
from typing import Optional, Tuple
import logging
import os

logger = logging.getLogger(__name__)


class ModelDownloader:
    """Downloads and caches TTS models from HuggingFace"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """
        Initialize model downloader.
        
        Args:
            cache_dir: Directory to cache models (default: ./models)
        """
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "models" / "chatterbox"
        
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.turbo_dir = self.cache_dir / "turbo"
        self.mtl_dir = self.cache_dir / "mtl"
    
    def is_turbo_downloaded(self) -> bool:
        """Check if Turbo model is already cached"""
        required_files = [
            "ve.safetensors",
            "t3_turbo_v1.safetensors",
            "s3gen_meanflow.safetensors",
            "conds.pt"
        ]
        return all((self.turbo_dir / f).exists() for f in required_files)
    
    def is_mtl_downloaded(self) -> bool:
        """Check if MTL model is already cached"""
        required_files = [
            "ve.safetensors",
            "t3_mtl.safetensors",
            "s3gen_mtl.safetensors",
            "conds.pt"
        ]
        return all((self.mtl_dir / f).exists() for f in required_files)
    
    def download_turbo(self, token: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[Path]]:
        """
        Download Turbo TTS model from HuggingFace.
        
        Args:
            token: HuggingFace token (optional, will use HF_TOKEN env var or prompt)
            
        Returns:
            (success, error_message, model_path)
        """
        try:
            from huggingface_hub import snapshot_download
            
            # Check cache first
            if self.is_turbo_downloaded():
                logger.info("Turbo model already cached")
                return True, None, self.turbo_dir
            
            # Get token
            if token is None:
                token = os.getenv("HF_TOKEN")
            
            if token is None:
                return False, (
                    "HuggingFace token required for Turbo model.\n\n"
                    "To get a token:\n"
                    "1. Go to https://huggingface.co/settings/tokens\n"
                    "2. Create a new token (read access is sufficient)\n"
                    "3. Set environment variable: HF_TOKEN=your_token_here\n"
                    "   OR provide token when downloading\n\n"
                    "Alternatively, run: huggingface-cli login"
                ), None
            
            logger.info("Downloading Turbo model from HuggingFace (this may take a few minutes)...")
            
            local_path = snapshot_download(
                repo_id="ResembleAI/chatterbox-turbo",
                token=token,
                cache_dir=str(self.cache_dir / "hf_cache"),
                local_dir=str(self.turbo_dir),
                local_dir_use_symlinks=False,
                allow_patterns=["*.safetensors", "*.json", "*.txt", "*.pt", "*.model"]
            )
            
            logger.info(f"Turbo model downloaded successfully to: {self.turbo_dir}")
            return True, None, Path(local_path)
            
        except Exception as e:
            error_msg = f"Failed to download Turbo model: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def download_mtl(self, token: Optional[str] = None) -> Tuple[bool, Optional[str], Optional[Path]]:
        """
        Download Multilingual TTS model from HuggingFace.
        
        Args:
            token: HuggingFace token (optional)
            
        Returns:
            (success, error_message, model_path)
        """
        try:
            from huggingface_hub import snapshot_download
            
            # Check cache first
            if self.is_mtl_downloaded():
                logger.info("MTL model already cached")
                return True, None, self.mtl_dir
            
            # Get token (MTL might not require it, but try with it if available)
            if token is None:
                token = os.getenv("HF_TOKEN")
            
            logger.info("Downloading MTL model from HuggingFace (this may take a few minutes)...")
            
            local_path = snapshot_download(
                repo_id="ResembleAI/chatterbox-multilingual",
                token=token if token else False,  # Don't require token for MTL
                cache_dir=str(self.cache_dir / "hf_cache"),
                local_dir=str(self.mtl_dir),
                local_dir_use_symlinks=False,
                allow_patterns=["*.safetensors", "*.json", "*.txt", "*.pt", "*.model"]
            )
            
            logger.info(f"MTL model downloaded successfully to: {self.mtl_dir}")
            return True, None, Path(local_path)
            
        except Exception as e:
            error_msg = f"Failed to download MTL model: {str(e)}"
            logger.error(error_msg)
            return False, error_msg, None
    
    def get_turbo_path(self) -> Optional[Path]:
        """Get path to cached Turbo model (if exists)"""
        return self.turbo_dir if self.is_turbo_downloaded() else None
    
    def get_mtl_path(self) -> Optional[Path]:
        """Get path to cached MTL model (if exists)"""
        return self.mtl_dir if self.is_mtl_downloaded() else None
