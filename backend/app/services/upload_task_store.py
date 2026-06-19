from __future__ import annotations

import io
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from threading import Lock


class UploadStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class UploadTask:
    task_id: str
    patient_id: str
    temp_dir: Path
    files_received: int = 0
    total_files: int | None = None
    status: UploadStatus = UploadStatus.PENDING
    progress: int = 0
    error: str | None = None
    result: dict | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class UploadTaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, UploadTask] = {}
        self._lock = Lock()

    def create(self, patient_id: str, temp_dir: Path, total_files: int | None = None) -> UploadTask:
        task_id = str(uuid.uuid4())
        task = UploadTask(
            task_id=task_id,
            patient_id=patient_id,
            temp_dir=temp_dir,
            total_files=total_files,
            status=UploadStatus.RUNNING,
        )
        with self._lock:
            self._tasks[task_id] = task
        return task

    def get(self, task_id: str) -> UploadTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def update_progress(self, task_id: str, files_received: int) -> UploadTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.files_received = files_received
            if task.total_files and task.total_files > 0:
                task.progress = min(99, int((files_received / task.total_files) * 100))
            return task

    def complete(self, task_id: str, result: dict) -> UploadTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.status = UploadStatus.DONE
            task.progress = 100
            task.result = result
            return task

    def fail(self, task_id: str, error: str) -> UploadTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.status = UploadStatus.ERROR
            task.error = error
            return task


upload_task_store = UploadTaskStore()
