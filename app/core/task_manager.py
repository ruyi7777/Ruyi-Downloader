"""Pure FIFO management for sequential download queue tasks."""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable, Optional, Tuple

from app.core.download_models import (
    DownloadProgress,
    DownloadQueueCounts,
    DownloadTask,
    DownloadTaskStatus,
)


class DownloadTaskStateError(RuntimeError):
    """Raised when a queue task transition would corrupt task state."""


class TaskManager:
    """Manage task state without networking, Qt signals, or GUI concerns."""

    def __init__(self) -> None:
        self._tasks: Dict[int, DownloadTask] = {}
        self._next_task_id = 1
        self._running_task_id: Optional[int] = None

    def enqueue(self, url: str, title: str = "") -> DownloadTask:
        """Append one queued task and return an immutable snapshot."""
        normalized_url = str(url).strip()
        if not normalized_url:
            raise ValueError("Download task URL must not be empty")

        task = DownloadTask(
            task_id=self._next_task_id,
            url=normalized_url,
            title=str(title or "").strip(),
        )
        self._next_task_id += 1
        self._tasks[task.task_id] = task
        return self._snapshot(task)

    def enqueue_many(
        self,
        items: Iterable[Tuple[str, str]],
    ) -> Tuple[DownloadTask, ...]:
        """Append tasks in iterable order and return their snapshots."""
        return tuple(self.enqueue(url, title) for url, title in items)

    def get_next_queued(self) -> Optional[DownloadTask]:
        """Atomically promote the first queued task to RUNNING."""
        if self._running_task_id is not None:
            raise DownloadTaskStateError(
                "A download task is already running"
            )

        for task in self._tasks.values():
            if task.status is DownloadTaskStatus.QUEUED:
                task.status = DownloadTaskStatus.RUNNING
                self._running_task_id = task.task_id
                return self._snapshot(task)
        return None

    def mark_completed(self, task_id: int) -> DownloadTask:
        task = self._get_task(task_id)
        self._require_status(task, DownloadTaskStatus.RUNNING)
        task.status = DownloadTaskStatus.COMPLETED
        task.error_message = ""
        self._clear_running(task_id)
        return self._snapshot(task)

    def mark_failed(self, task_id: int, error_message: str) -> DownloadTask:
        task = self._get_task(task_id)
        self._require_status(task, DownloadTaskStatus.RUNNING)
        task.status = DownloadTaskStatus.FAILED
        task.error_message = str(error_message or "下载失败")
        self._clear_running(task_id)
        return self._snapshot(task)

    def update_progress(
        self,
        task_id: int,
        progress: DownloadProgress,
    ) -> DownloadTask:
        task = self._get_task(task_id)
        self._require_status(task, DownloadTaskStatus.RUNNING)
        task.progress = progress
        return self._snapshot(task)

    def snapshot(self, task_id: int) -> DownloadTask:
        return self._snapshot(self._get_task(task_id))

    def snapshots(self) -> Tuple[DownloadTask, ...]:
        """Return ordered immutable snapshots for UI and tests."""
        return tuple(self._snapshot(task) for task in self._tasks.values())

    def counts(self) -> DownloadQueueCounts:
        counts = {
            status: 0
            for status in DownloadTaskStatus
        }
        for task in self._tasks.values():
            counts[task.status] += 1
        return DownloadQueueCounts(
            queued=counts[DownloadTaskStatus.QUEUED],
            running=counts[DownloadTaskStatus.RUNNING],
            completed=counts[DownloadTaskStatus.COMPLETED],
            failed=counts[DownloadTaskStatus.FAILED],
        )

    @property
    def is_finished(self) -> bool:
        if not self._tasks:
            return False
        return all(
            task.status.is_terminal for task in self._tasks.values()
        )

    @staticmethod
    def _snapshot(task: DownloadTask) -> DownloadTask:
        return replace(task)

    def _get_task(self, task_id: int) -> DownloadTask:
        try:
            return self._tasks[task_id]
        except KeyError as error:
            raise DownloadTaskStateError(
                f"Unknown download task id: {task_id}"
            ) from error

    @staticmethod
    def _require_status(
        task: DownloadTask,
        expected: DownloadTaskStatus,
    ) -> None:
        if task.status is not expected:
            raise DownloadTaskStateError(
                f"Task {task.task_id} is {task.status.value}, "
                f"expected {expected.value}"
            )

    def _clear_running(self, task_id: int) -> None:
        if self._running_task_id == task_id:
            self._running_task_id = None
