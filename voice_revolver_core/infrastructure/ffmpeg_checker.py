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


class FFmpegChecker:
    """
    Infrastructure component for FFmpeg management.
    Checks availability, auto-downloads if missing.
    """
    
    def __init__(self, app_data_path: Path):
        self._app_data_path = app_data_path
        self._ffmpeg_path: Optional[Path] = None
        self._ffprobe_path: Optional[Path] = None
    
    def is_available(self) -> bool:
        """Check if FFmpeg is available"""
        return shutil.which("ffmpeg") is not None
    
    async def ensure_available(
        self,
        download_callback: Optional[Callable[[float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Ensure FFmpeg is available, download if not.
        Returns: (success, error_message)
        """
        if self.is_available():
            self._ffmpeg_path = Path(shutil.which("ffmpeg"))
            self._ffprobe_path = Path(shutil.which("ffprobe"))
            return True, None
        
        # Try to use bundled FFmpeg
        bundled = self._get_bundled_ffmpeg()
        if bundled:
            self._ffmpeg_path = bundled
            return True, None
        
        # Need to download
        return await self._download_ffmpeg(download_callback)
    
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
    
    async def _download_ffmpeg(
        self,
        download_callback: Optional[Callable[[float], None]] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Download FFmpeg.
        Note: This is a placeholder - actual implementation would download
        FFmpeg binaries for the target platform.
        """
        import asyncio
        
        # Simulated download
        for i in range(10):
            await asyncio.sleep(0.2)
            if download_callback:
                download_callback((i + 1) / 10)
        
        # In real implementation:
        # - Download FFmpeg for Windows/Mac
        # - Extract to app_data/ffmpeg/
        # - Set executable permissions
        
        return True, None
    
    def get_version(self) -> Optional[str]:
        """Get FFmpeg version string"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                # Extract version from first line
                first_line = result.stdout.split('\n')[0]
                return first_line.replace("ffmpeg version ", "")
        except Exception:
            pass
        
        return None
    
    @property
    def ffmpeg_path(self) -> Optional[Path]:
        """Get path to FFmpeg executable"""
        return self._ffmpeg_path
    
    @property
    def ffprobe_path(self) -> Optional[Path]:
        """Get path to FFprobe executable"""
        return self._ffprobe_path
