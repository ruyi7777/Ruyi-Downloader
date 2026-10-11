"""Sequential download queue controller bridging Core tasks and Qt workers."""
from __future__ import annotations

import logging
from typing import Callable, Iterable, Optional, Tuple

from PyQt6.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

from app.core.download_models import (
    DownloadProgress,
    DownloadResult,
    DownloadTask,
)
from app.core.downloader import VideoDownloader
from app.core.task_manager import TaskManager
from app.ui.download_worker import DownloadWorker

logger = logging.getLogger(__name__)

WorkerFactory = Callable[[DownloadTask], QRunnable]
QueueItem = Tuple[str, str]


class DownloadQueueController(QObject):
    """Run one queued download at a time and filter stale worker signals."""

    queue_started = pyqtSignal(object, object)
    task_started = pyqtSignal(object)
    task_progress = pyqtSignal(object, object)
    task_succeeded = pyqtSignal(object, object)
    task_failed = pyqtSignal(object, str, str)
    queue_finished = pyqtSignal(object, object)

    def __init__(
        self,
        downloader: Optional[VideoDownloader] = None,
        worker_factory: Optional[WorkerFactory] = None,
        thread_pool: Optional[QThreadPool] = None,
    ) -> None:
        super().__init__()
        self._downloader = downloader
        self._worker_factory = worker_factory or self._create_worker
        self._thread_pool = thread_pool or QThreadPool.globalInstance()
        self._task_manager = TaskManager()
        self._generation = 0
        self._finished_generation: Optional[int] = None
        self._is_running = False
        self._current_worker: Optional[QRunnable] = None
        self._current_task_id: Optional[int] = None

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    @property
    def is_running(self) -> bool:
        return self._is_running

    @property
    def current_task(self) -> Optional[DownloadTask]:
        if self._current_task_id is None:
            return None
        return self._task_manager.snapshot(self._current_task_id)

    def start(self, items: Iterable[QueueItem]) -> bool:
        """Start a fresh FIFO queue. Returns False when no work was accepted."""
        if self._is_running:
            return False

        queue_items = tuple(items)
        if not queue_items:
            return False

        task_manager = TaskManager()
        task_manager.enqueue_many(queue_items)
        self._task_manager = task_manager
        self._generation += 1
        generation = self._generation
        self._finished_generation = None
        self._current_worker = None
        self._current_task_id = None
        self._is_running = True

        self.queue_started.emit(
            task_manager.snapshots(),
            task_manager.counts(),
        )
        self._advance(generation)
        return True

    def _create_worker(self, task: DownloadTask) -> DownloadWorker:
        return DownloadWorker(
            task.url,
            downloader=self._downloader,
        )

    def _advance(self, generation: int) -> None:
        if not self._is_current_generation(generation):
            return

        task = self._task_manager.get_next_queued()
        if task is None:
            self._finish(generation)
            return

        self._current_task_id = task.task_id
        try:
            worker = self._worker_factory(task)
            worker.signals.progress.connect(
                lambda progress, current_generation=generation,
                current_task_id=task.task_id: self._on_progress(
                    current_generation,
                    current_task_id,
                    progress,
                )
            )
            worker.signals.succeeded.connect(
                lambda result, current_generation=generation,
                current_task_id=task.task_id: self._on_succeeded(
                    current_generation,
                    current_task_id,
                    result,
                )
            )
            worker.signals.failed.connect(
                lambda user_message, detail,
                current_generation=generation,
                current_task_id=task.task_id: self._on_failed(
                    current_generation,
                    current_task_id,
                    user_message,
                    detail,
                )
            )
            self._current_worker = worker
            self.task_started.emit(task)
            self._thread_pool.start(worker)
        except Exception as error:
            detail = f"{type(error).__name__}: {error}"
            logger.exception("Unable to start download task %s", task.task_id)
            self._handle_failure(
                generation,
                task.task_id,
                "无法启动下载任务",
                detail,
            )

    def _on_progress(
        self,
        generation: int,
        task_id: int,
        progress: DownloadProgress,
    ) -> None:
        if not self._is_current_task(generation, task_id):
            return

        snapshot = self._task_manager.update_progress(task_id, progress)
        self.task_progress.emit(snapshot, progress)

    def _on_succeeded(
        self,
        generation: int,
        task_id: int,
        result: DownloadResult,
    ) -> None:
        if not self._is_current_task(generation, task_id):
            return

        snapshot = self._task_manager.mark_completed(task_id)
        self._clear_current_worker()
        self.task_succeeded.emit(snapshot, result)
        self._advance(generation)

    def _on_failed(
        self,
        generation: int,
        task_id: int,
        user_message: str,
        detail: str,
    ) -> None:
        if not self._is_current_task(generation, task_id):
            return
        self._handle_failure(
            generation,
            task_id,
            user_message,
            detail,
        )

    def _handle_failure(
        self,
        generation: int,
        task_id: Optional[int],
        user_message: str,
        detail: str,
    ) -> None:
        if (
            task_id is None
            or not self._is_current_generation(generation)
        ):
            return

        message = str(user_message or "下载失败")
        snapshot = self._task_manager.mark_failed(task_id, message)
        self._clear_current_worker()
        self.task_failed.emit(snapshot, message, str(detail or ""))
        self._advance(generation)

    def _finish(self, generation: int) -> None:
        if (
            not self._is_current_generation(generation)
            or self._finished_generation == generation
        ):
            return

        counts = self._task_manager.counts()
        snapshots = self._task_manager.snapshots()
        self._finished_generation = generation
        self._clear_current_worker()
        self._is_running = False
        self.queue_finished.emit(snapshots, counts)

    def _clear_current_worker(self) -> None:
        self._current_worker = None
        self._current_task_id = None

    def _is_current_generation(self, generation: int) -> bool:
        return self._is_running and generation == self._generation

    def _is_current_task(
        self,
        generation: int,
        task_id: int,
    ) -> bool:
        return (
            self._is_current_generation(generation)
            and self._current_task_id == task_id
        )
