"""
Project Service - Application Layer
Handles saving and loading .vra project files
"""

import json
from pathlib import Path
from typing import Optional
from dataclasses import asdict

from ..domain import (
    ProjectData,
    ErrorCode,
)


class ProjectService:
    """
    Application service for project management.
    Handles .vra file format (JSON-based).
    """
    
    PROJECT_FILE_EXTENSION = ".vra"
    
    def __init__(self):
        pass
    
    def create_new_project(self) -> ProjectData:
        """Create a new empty project"""
        return ProjectData()
    
    def save_project(self, project: ProjectData, file_path: Path) -> tuple[bool, Optional[ErrorCode], str]:
        """Save project to .vra file"""
        try:
            # Update timestamp
            from datetime import datetime
            project.updated_at = datetime.now().isoformat()
            
            # Convert to JSON
            project_dict = asdict(project)
            
            # Handle VoiceConversionParams nested object
            if project.voice_params:
                project_dict['voice_params'] = asdict(project.voice_params)
            
            # Write to file
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(project_dict, f, indent=2, ensure_ascii=False)
            
            return True, None, f"Project saved to {file_path}"
            
        except Exception as e:
            return False, ErrorCode.FILE_WRITE_FAILED, str(e)
    
    def load_project(self, file_path: Path) -> tuple[Optional[ProjectData], Optional[ErrorCode], str]:
        """Load project from .vra file"""
        try:
            if not file_path.exists():
                return None, ErrorCode.FILE_NOT_FOUND, "Project file not found"
            
            if file_path.suffix.lower() != self.PROJECT_FILE_EXTENSION:
                return None, ErrorCode.UNSUPPORTED_FORMAT, "Invalid project file format"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                project_dict = json.load(f)
            
            # Reconstruct ProjectData
            voice_params_dict = project_dict.pop('voice_params', {})
            from ..domain import VoiceConversionParams
            voice_params = VoiceConversionParams(**voice_params_dict)
            
            project = ProjectData(**project_dict)
            project.voice_params = voice_params
            
            return project, None, "Project loaded successfully"
            
        except json.JSONDecodeError as e:
            return None, ErrorCode.FILE_NOT_FOUND, f"Invalid project file: {e}"
        except Exception as e:
            return None, ErrorCode.FILE_WRITE_FAILED, str(e)
    
    def validate_project_for_export(self, project: ProjectData) -> tuple[bool, str]:
        """Validate project has required data for export"""
        if not project.original_file:
            return False, "Original audio file not set"
        
        if not project.reference_file:
            return False, "Reference voice file not set"
        
        original_path = Path(project.original_file)
        if not original_path.exists():
            return False, f"Original file not found: {project.original_file}"
        
        reference_path = Path(project.reference_file)
        if not reference_path.exists():
            return False, f"Reference file not found: {project.reference_file}"
        
        return True, "Project is valid for export"
    
    def get_default_project_path(self, project_name: str) -> Path:
        """Get default project save path"""
        from datetime import datetime
        date_str = datetime.now().strftime("%Y%m%d")
        return Path(f"{project_name}_{date_str}{self.PROJECT_FILE_EXTENSION}")
