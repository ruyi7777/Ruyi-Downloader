"""Tests for sequential DownloadQueueController behavior with fake workers."""
from __future__ import annotations

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot
from PyQt6.QtWidgets import QApplication

from app.core.download_models import (
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
    DownloadTaskStatus,
)
from app.ui.download_queue_controller import DownloadQueueController


class _JoinedThreadTestPool:
    """Deterministic test pool without Qt's native QThreadPool lifecycle."""

    @staticmethod
    def start(worker) -> None:
        thread = threading.Thread(target=worker.run, daemon=True)
        thread.start()
        thread.join()


class _Signals(QObject):
    progress = pyqtSignal(object)
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str, str)


class _FakeWorker:
    active = 0
    max_active = 0
    lock = threading.Lock()

    def __init__(self, url: str, title: str, delay: float = 0.01) -> None:
        self.url = url
        self.title = title
        self.delay = delay
        self.signals = _Signals()

    @pyqtSlot()
    def run(self) -> None:
        with type(self).lock:
            type(self).active += 1
            type(self).max_active = max(
                type(self).max_active,
                type(self).active,
            )
        try:
            if "fail" in self.url:
                if self.delay:
                    time.sleep(self.delay)
                self.signals.failed.emit("模拟下载失败", "fake detail")
                return

            self.signals.progress.emit(
                DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    percent=50.0,
                    downloaded_bytes=50,
                    total_bytes=100,
                )
            )
            if self.delay:
                time.sleep(self.delay)
            self.signals.succeeded.emit(
                DownloadResult(
                    video_id=self.url.rsplit("/", 1)[-1],
                    title=self.title,
                    file_path=__import__("pathlib").Path("fake.mp4"),
                )
            )
        finally:
            with type(self).lock:
                type(self).active -= 1


def _process_until(app, predicate, timeout: float = 3.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return predicate()


class DownloadQueueControllerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        _FakeWorker.active = 0
        _FakeWorker.max_active = 0
        self.pool = _JoinedThreadTestPool()
        self.workers: list[_FakeWorker] = []
        self.started_ids: list[int] = []
        self.succeeded_ids: list[int] = []
        self.failed_ids: list[int] = []
        self.progress_events: list[tuple[int, float]] = []
        self.finished: list[tuple[int, int]] = []
        self.worker_delay = 0.01

        def factory(task):
            worker = _FakeWorker(
                task.url,
                task.title,
                delay=self.worker_delay,
            )
            self.workers.append(worker)
            return worker

        self.controller = DownloadQueueController(
            worker_factory=factory,
            thread_pool=self.pool,
        )
        self.controller.task_started.connect(
            lambda task: self.started_ids.append(task.task_id)
        )
        self.controller.task_succeeded.connect(
            lambda task, _result: self.succeeded_ids.append(task.task_id)
        )
        self.controller.task_failed.connect(
            lambda task, _message, _detail: self.failed_ids.append(task.task_id)
        )
        self.controller.task_progress.connect(
            lambda task, progress: self.progress_events.append(
                (task.task_id, progress.percent or 0.0)
            )
        )
        self.controller.queue_finished.connect(
            lambda snapshots, counts: self.finished.append(
                (counts.completed, counts.failed)
            )
        )

    def tearDown(self) -> None:
        self.controller.deleteLater()
        for worker in self.workers:
            signals = getattr(worker, "signals", None)
            if signals is not None:
                signals.deleteLater()
        for _ in range(5):
            self.app.processEvents()

    def _start_and_wait(self, items) -> None:
        self.assertTrue(self.controller.start(items))
        self.assertTrue(
            _process_until(
                self.app,
                lambda: not self.controller.is_running and bool(self.finished),
            )
        )

    def test_fifo_success_failure_and_single_running_worker(self) -> None:
        self._start_and_wait(
            [
                ("https://example.com/ok1", "一"),
                ("https://example.com/fail", "二"),
                ("https://example.com/ok2", "三"),
            ]
        )

        snapshots = self.controller.task_manager.snapshots()
        self.assertEqual(
            [task.status for task in snapshots],
            [
                DownloadTaskStatus.COMPLETED,
                DownloadTaskStatus.FAILED,
                DownloadTaskStatus.COMPLETED,
            ],
        )
        self.assertEqual(snapshots[1].error_message, "模拟下载失败")
        self.assertEqual(self.started_ids, [1, 2, 3])
        self.assertEqual(self.succeeded_ids, [1, 3])
        self.assertEqual(self.failed_ids, [2])
        self.assertEqual(self.finished, [(2, 1)])
        self.assertEqual(_FakeWorker.max_active, 1)
        self.assertEqual(
            [worker.url for worker in self.workers],
            [
                "https://example.com/ok1",
                "https://example.com/fail",
                "https://example.com/ok2",
            ],
        )

    def test_progress_belongs_to_current_task(self) -> None:
        self._start_and_wait(
            [
                ("https://example.com/ok1", "一"),
                ("https://example.com/ok2", "二"),
            ]
        )

        self.assertEqual(
            self.progress_events,
            [(1, 50.0), (2, 50.0)],
        )
        self.assertEqual(
            [
                task.progress.percent
                if task.progress is not None
                else None
                for task in self.controller.task_manager.snapshots()
            ],
            [50.0, 50.0],
        )

    def test_old_worker_signals_are_filtered_after_new_queue(self) -> None:
        self._start_and_wait([("https://example.com/old", "旧")])
        old_worker = self.workers[0]
        finished_before = list(self.finished)

        self.worker_delay = 0.2
        self.assertTrue(
            self.controller.start([("https://example.com/new", "新")])
        )
        self.assertEqual(len(self.workers), 2)
        current_task = self.controller.current_task
        self.assertIsNotNone(current_task)
        assert current_task is not None

        old_worker.signals.progress.emit(
            DownloadProgress(
                status=DownloadStatus.DOWNLOADING,
                percent=99.0,
                downloaded_bytes=99,
                total_bytes=100,
            )
        )
        old_worker.signals.succeeded.emit(
            DownloadResult(
                video_id="old",
                title="旧",
                file_path=__import__("pathlib").Path("old.mp4"),
            )
        )
        current_snapshot = self.controller.task_manager.snapshot(
            current_task.task_id
        )
        self.assertIsNone(current_snapshot.progress)
        self.assertEqual(self.finished, finished_before)

        self.assertTrue(
            _process_until(
                self.app,
                lambda: not self.controller.is_running,
            )
        )
        self.assertEqual(len(self.finished), 2)

    def test_start_is_rejected_while_queue_is_running(self) -> None:
        self.assertTrue(
            self.controller.start([("https://example.com/ok1", "一")])
        )
        self.assertFalse(
            self.controller.start([("https://example.com/ok2", "二")])
        )
        self.assertTrue(
            _process_until(
                self.app,
                lambda: not self.controller.is_running,
            )
        )
        self.assertEqual(len(self.workers), 1)


if __name__ == "__main__":
    unittest.main()
