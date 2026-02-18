"""
File Manager - Domain Entity
Handles temp files, export workflow, and file naming
"""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from .base import ErrorCode, generate_auto_filename


@dataclass
class FileOperationResult:
    """Result of file operation"""
    success: bool = False
    path: Optional[Path] = None
    error_code: Optional[ErrorCode] = None
    error_message: str = ""


class FileManager:
    """
    Domain entity for file management.
    Handles temp storage, exports, and naming.
    """
    
    def __init__(self, app_data_path: Path):
        self._app_data_path = app_data_path
        self._temp_path = app_data_path / "temp"
        self._exports_path = app_data_path / "exports"
    
    @property
    def temp_path(self) -> Path:
        """Get temp directory path"""
        return self._temp_path
    
    @property
    def exports_path(self) -> Path:
        """Get exports directory path"""
        return self._exports_path
    
    def generate_temp_filename(self, extension: str) -> str:
        """Generate auto filename for temp file"""
        return generate_auto_filename(extension)
    
    def generate_export_filename(self, base_name: Optional[str], extension: str) -> str:
        """Generate filename for export"""
        if base_name:
            return f"{base_name}.{extension}"
        return generate_auto_filename(extension)
    
    def validate_export_path(self, path: Path) -> tuple[bool, Optional[ErrorCode]]:
        """Validate export path is writable"""
        try:
            # Check parent directory exists or can be created
            parent = path.parent
            if not parent.exists():
                parent.mkdir(parents=True, exist_ok=True)
            
            # Try to create a test file
            test_file = parent / ".write_test"
            test_file.touch()
            test_file.unlink()
            
            return True, None
            
        except Exception as e:
            return False, ErrorCode.FILE_WRITE_FAILED
    
    def get_file_size_mb(self, path: Path) -> float:
        """Get file size in MB"""
        if not path.exists():
            return 0.0
        return path.stat().st_size / (1024 * 1024)
    
    def cleanup_temp_files(self) -> int:
        """Clean up all temp files, return count of deleted files"""
        if not self._temp_path.exists():
            return 0
        
        count = 0
        for file in self._temp_path.iterdir():
            if file.is_file():
                try:
                    file.unlink()
                    count += 1
                except Exception:
                    pass
        return count
