"""
Progress Tracker - Domain Entity
Tracks processing progress with unique keys
"""

from typing import Dict, Optional
from dataclasses import dataclass, field
import threading

from .base import ProgressInfo, ProcessingStage, generate_task_key


class ProgressTracker:
    """
    Domain entity for progress tracking.
    Manages multiple concurrent tasks.
    """
    
    def __init__(self):
        self._tasks: Dict[str, ProgressInfo] = {}
        self._lock = threading.Lock()
    
    def start_task(self, name: str = "default") -> str:
        """Start a new task and return task key"""
        task_key = generate_task_key()
        
        with self._lock:
            self._tasks[task_key] = ProgressInfo(
                task_key=task_key,
                stage=ProcessingStage.LOADING_MODELS,
                percentage=0,
                message="Starting task...",
                status="running"
            )
        
        return task_key
    
    def update_progress(self, task_key: str, stage: ProcessingStage, percentage: int, message: str = ""):
        """Update task progress"""
        with self._lock:
            if task_key in self._tasks:
                self._tasks[task_key].stage = stage
                self._tasks[task_key].percentage = min(100, max(0, percentage))
                self._tasks[task_key].message = message
    
    def get_progress(self, task_key: str) -> Optional[ProgressInfo]:
        """Get progress info for task"""
        with self._lock:
            return self._tasks.get(task_key)
    
    def complete_task(self, task_key: str, success: bool = True):
        """Mark task as complete"""
        with self._lock:
            if task_key in self._tasks:
                self._tasks[task_key].stage = ProcessingStage.COMPLETE if success else ProcessingStage.FAILED
                self._tasks[task_key].percentage = 100 if success else self._tasks[task_key].percentage
                self._tasks[task_key].status = "complete" if success else "failed"
    
    def cancel_task(self, task_key: str):
        """Cancel a task"""
        with self._lock:
            if task_key in self._tasks:
                self._tasks[task_key].stage = ProcessingStage.FAILED
                self._tasks[task_key].status = "cancelled"
                self._tasks[task_key].message = "Task cancelled by user"
    
    def get_all_tasks(self) -> Dict[str, ProgressInfo]:
        """Get all tasks"""
        with self._lock:
            return dict(self._tasks)
    
    def cleanup_completed(self, max_age_seconds: int = 3600):
        """Remove old completed tasks"""
        # This would need timestamp tracking - simplified for now
        pass
