from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from threading import Lock
from uuid import uuid4

STALE_RUNNING_MIN_SECONDS = 1800
STALE_RUNNING_MAX_SECONDS = 7200
SECONDS_PER_SLICE_CPU = 15


def stale_timeout_for_exam(nb_coupes: int) -> int:
    """Délai avant expiration — ~15 s/coupe sur CPU, min 30 min, max 2 h."""
    estimated = max(nb_coupes, 1) * SECONDS_PER_SLICE_CPU
    return max(STALE_RUNNING_MIN_SECONDS, min(STALE_RUNNING_MAX_SECONDS, estimated))


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
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AnalyseTaskStore:
    def __init__(self) -> None:
        self._by_study: dict[str, AnalyseTask] = {}
        self._lock = Lock()

    def create(self, study_id: str) -> AnalyseTask:
        task = AnalyseTask(
            task_id=str(uuid4()),
            study_id=study_id,
            status=AnalyseStatus.RUNNING,
            progress=1,
        )
        with self._lock:
            self._by_study[study_id] = task
        return task

    def get_by_study(self, study_id: str) -> AnalyseTask | None:
        with self._lock:
            return self._by_study.get(study_id)

    def is_stale_running(self, study_id: str, max_seconds: int) -> bool:
        """Expire seulement si l'analyse tourne depuis max_seconds (pas entre deux updates)."""
        with self._lock:
            task = self._by_study.get(study_id)
            if task is None or task.status != AnalyseStatus.RUNNING:
                return False
            now = datetime.now(timezone.utc)
            started = task.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            return (now - started).total_seconds() >= max_seconds

    def touch(self, study_id: str) -> None:
        """Heartbeat — garde la tâche vivante pendant les phases CPU longues."""
        with self._lock:
            task = self._by_study.get(study_id)
            if task is not None:
                task.updated_at = datetime.now(timezone.utc)

    def is_stale_pending(self, study_id: str, max_seconds: int = 45) -> bool:
        with self._lock:
            task = self._by_study.get(study_id)
            if task is None or task.status != AnalyseStatus.PENDING:
                return False
            now = datetime.now(timezone.utc)
            started = task.started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            return (now - started).total_seconds() >= max_seconds

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
            task.updated_at = datetime.now(timezone.utc)
            return task

    def remove(self, study_id: str) -> None:
        with self._lock:
            self._by_study.pop(study_id, None)


analyse_task_store = AnalyseTaskStore()
