"""
FFmpeg Checker - Infrastructure Layer
Checks for FFmpeg availability and handles auto-download
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)


class FFmpegChecker:
    """
    Infrastructure component for FFmpeg management.
    Checks availability, auto-downloads if missing using static-ffmpeg.
    """
    
    def __init__(self, app_data_path: Path):
        self._app_data_path = app_data_path
        self._ffmpeg_path: Optional[Path] = None
        self._ffprobe_path: Optional[Path] = None
        self._version: Optional[str] = None
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available on system PATH"""
        return shutil.which("ffmpeg") is not None
    
    def ensure_available(
        self,
        download_callback: Optional[Callable[[float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Ensure FFmpeg is available, download if not.
        Uses static-ffmpeg for auto-download.
        Returns: (success, error_message)
        """
        # First check system FFmpeg
        if self.is_available():
            self._ffmpeg_path = Path(shutil.which("ffmpeg"))
            self._ffprobe_path = Path(shutil.which("ffprobe"))
            self._version = self._get_version()
            logger.info(f"Using system FFmpeg: {self._ffmpeg_path}")
            return True, None
        
        # Check for bundled FFmpeg in app data
        bundled = self._get_bundled_ffmpeg()
        if bundled and bundled.exists():
            self._ffmpeg_path = bundled
            ffprobe_name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
            ffprobe_candidate = bundled.parent / ffprobe_name
            if ffprobe_candidate.exists():
                self._ffprobe_path = ffprobe_candidate
            self._version = self._get_version()
            logger.info(f"Using bundled FFmpeg: {self._ffmpeg_path}")
            return True, None
        
        # Download using static-ffmpeg
        return self._download_ffmpeg(download_callback)
    
    def _get_bundled_ffmpeg(self) -> Optional[Path]:
        """Check for bundled FFmpeg in app data"""
        ffmpeg_dir = self._app_data_path / "ffmpeg"
        if sys.platform == "win32":
            ffmpeg_bin = ffmpeg_dir / "bin" / "ffmpeg.exe"
        else:
            ffmpeg_bin = ffmpeg_dir / "bin" / "ffmpeg"
        
        if ffmpeg_bin.exists():
            return ffmpeg_bin
        
        return None
    
    def _download_ffmpeg(
        self,
        download_callback: Optional[Callable[[float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Download FFmpeg using static-ffmpeg library.
        """
        try:
            from static_ffmpeg import run
            
            logger.info("Downloading FFmpeg (static-ffmpeg)...")
            
            # Download FFmpeg synchronously
            ffmpeg_path_str, ffprobe_path_str = run.get_or_fetch_platform_executables_else_raise()
            
            if ffmpeg_path_str:
                self._ffmpeg_path = Path(ffmpeg_path_str)
            if ffprobe_path_str:
                self._ffprobe_path = Path(ffprobe_path_str)
            self._version = self._get_version()
            
            logger.info(f"FFmpeg downloaded successfully: {self._ffmpeg_path}")
            
            if download_callback:
                download_callback(1.0)
            
            return True, None
            
        except Exception as e:
            error_msg = f"Failed to download FFmpeg: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def _get_version(self) -> Optional[str]:
        """Get FFmpeg version string"""
        try:
            ffmpeg_cmd = str(self._ffmpeg_path) if self._ffmpeg_path else "ffmpeg"
            result = subprocess.run(
                [ffmpeg_cmd, "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                first_line = result.stdout.split('\n')[0]
                return first_line.replace("ffmpeg version ", "")
        except Exception:
            pass
        
        return None
    
    def get_version(self) -> Optional[str]:
        """Get cached FFmpeg version string"""
        return self._version
    
    @property
    def ffmpeg_path(self) -> Optional[Path]:
        """Get path to FFmpeg executable"""
        return self._ffmpeg_path
    
    @property
    def ffprobe_path(self) -> Optional[Path]:
        """Get path to FFprobe executable"""
        return self._ffprobe_path
    
    def get_ffmpeg_dir(self) -> Optional[Path]:
        """Get FFmpeg binary directory for pydub"""
        if self._ffmpeg_path:
            return self._ffmpeg_path.parent
        return None
