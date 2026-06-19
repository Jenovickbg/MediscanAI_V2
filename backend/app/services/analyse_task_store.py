from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from uuid import uuid4


class AnalyseStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class AnalyseTask:
    task_id: str
    study_id: str
    status: AnalyseStatus = AnalyseStatus.PENDING
    progress: int = 0
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyseTaskStore:
    def __init__(self) -> None:
        self._by_study: dict[str, AnalyseTask] = {}
        self._lock = Lock()

    def create(self, study_id: str) -> AnalyseTask:
        task = AnalyseTask(task_id=str(uuid4()), study_id=study_id)
        with self._lock:
            self._by_study[study_id] = task
        return task

    def get_by_study(self, study_id: str) -> AnalyseTask | None:
        with self._lock:
            return self._by_study.get(study_id)

    def update(
        self,
        study_id: str,
        *,
        status: AnalyseStatus | None = None,
        progress: int | None = None,
        error: str | None = None,
    ) -> AnalyseTask | None:
        with self._lock:
            task = self._by_study.get(study_id)
            if task is None:
                return None
            if status is not None:
                task.status = status
            if progress is not None:
                task.progress = progress
            if error is not None:
                task.error = error
            return task


analyse_task_store = AnalyseTaskStore()
