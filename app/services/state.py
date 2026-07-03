"""
State management service for tasks.
"""

import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from app.models.const import TaskState
from app.models.schema import TaskData, TaskStatus, VideoParams
from app.utils import utils


class TaskStateStore:
    """In-memory and file-based task state storage."""

    def __init__(self, task_dir: str = "./tasks"):
        self.task_dir = Path(task_dir)
        self.task_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory store
        self._tasks: Dict[str, TaskData] = {}
        
        # Load existing tasks from disk
        self._load_existing_tasks()

    def _load_existing_tasks(self):
        """Load tasks from disk on startup."""
        for task_path in self.task_dir.iterdir():
            if task_path.is_dir():
                metadata_file = task_path / "metadata.json"
                if metadata_file.exists():
                    try:
                        metadata = utils.load_task_metadata(task_path.name)
                        status = metadata.get("status", "pending")
                        if status in ["pending", "processing", "paused"]:
                            # Restore task
                            pass
                    except Exception:
                        pass

    def create_task(
        self,
        task_id: str,
        params: VideoParams,
    ) -> TaskData:
        """Create a new task."""
        task_data = TaskData(
            task_id=task_id,
            params=params.dict() if hasattr(params, "dict") else {},
            status=TaskStatus.PENDING,
            created_at=time.time(),
            updated_at=time.time(),
        )
        
        self._tasks[task_id] = task_data
        self._save_task(task_id)
        
        logger.info(f"Created task {task_id}")
        return task_data

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[float] = None,
        **kwargs,
    ) -> Optional[TaskData]:
        """Update task state."""
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return None
        
        task = self._tasks[task_id]
        
        if status is not None:
            task.status = status
        if progress is not None:
            task.progress = progress
        
        task.updated_at = time.time()
        
        # Update output fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        self._save_task(task_id)
        return task

    def get_task(self, task_id: str) -> Optional[TaskData]:
        """Get task data."""
        return self._tasks.get(task_id)

    def _save_task(self, task_id: str):
        """Save task to disk."""
        if task_id not in self._tasks:
            return
        
        task = self._tasks[task_id]
        task_dir = utils.task_dir(task_id)
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Save metadata
        metadata_file = task_dir / "metadata.json"
        metadata = {
            "task_id": task_id,
            "status": task.status,
            "progress": task.progress,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "params": task.params,
        }
        
        # Add output fields
        for field in ["script", "prompts", "audio_file", "subtitle_path", "materials", "images"]:
            value = getattr(task, field, None)
            if value is not None:
                metadata[field] = value
        
        utils.write_text(metadata_file, json.dumps(metadata, indent=2, default=str))

    def list_tasks(
        self,
        limit: int = 50,
        status: Optional[TaskStatus] = None,
    ) -> List[Dict[str, Any]]:
        """List tasks with optional filtering."""
        tasks = []
        
        for task_id, task in list(self._tasks.items())[:limit]:
            if status and task.status != status:
                continue
            
            tasks.append({
                "task_id": task_id,
                "status": task.status,
                "progress": task.progress,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
            })
        
        return tasks

    def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        if task_id not in self._tasks:
            return False
        
        del self._tasks[task_id]
        
        # Remove task directory
        task_dir = utils.task_dir(task_id)
        if task_dir.exists():
            import shutil
            shutil.rmtree(task_dir)
        
        logger.info(f"Deleted task {task_id}")
        return True

    def clear_old_tasks(self, days: int = 7) -> int:
        """Clear tasks older than specified days."""
        cutoff = time.time() - (days * 86400)  # 86400 seconds per day
        cleared = 0
        
        for task_id in list(self._tasks.keys()):
            task = self._tasks[task_id]
            if task.created_at < cutoff:
                if self.delete_task(task_id):
                    cleared += 1
        
        logger.info(f"Cleared {cleared} old tasks")
        return cleared


# Global state store instance
state = TaskStateStore()
