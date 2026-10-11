"""Unit tests for the pure sequential download task state machine."""
from __future__ import annotations

import unittest
from dataclasses import replace

from app.core.download_models import (
    DownloadProgress,
    DownloadStatus,
    DownloadTaskStatus,
)
from app.core.task_manager import DownloadTaskStateError, TaskManager


def _progress(percent: float = 42.0) -> DownloadProgress:
    return DownloadProgress(
        status=DownloadStatus.DOWNLOADING,
        percent=percent,
        downloaded_bytes=420,
        total_bytes=1000,
    )


class TaskManagerTests(unittest.TestCase):
    def test_fifo_order_and_immutable_snapshots(self) -> None:
        manager = TaskManager()
        created = manager.enqueue_many(
            [
                ("https://example.com/1", "一"),
                ("https://example.com/2", "二"),
                ("https://example.com/3", "三"),
            ]
        )

        self.assertEqual([task.task_id for task in created], [1, 2, 3])
        self.assertEqual(
            [task.url for task in manager.snapshots()],
            [task.url for task in created],
        )

        snapshot = manager.snapshot(1)
        original_status = snapshot.status
        manager.get_next_queued()
        self.assertEqual(snapshot.status, original_status)
        self.assertEqual(snapshot.status, DownloadTaskStatus.QUEUED)

    def test_success_transition_and_next_running_task(self) -> None:
        manager = TaskManager()
        manager.enqueue_many(
            [
                ("https://example.com/1", "一"),
                ("https://example.com/2", "二"),
            ]
        )

        first = manager.get_next_queued()
        self.assertIsNotNone(first)
        assert first is not None
        self.assertEqual(first.status, DownloadTaskStatus.RUNNING)

        with self.assertRaises(DownloadTaskStateError):
            manager.get_next_queued()

        completed = manager.mark_completed(first.task_id)
        self.assertEqual(completed.status, DownloadTaskStatus.COMPLETED)
        self.assertEqual(completed.error_message, "")

        second = manager.get_next_queued()
        self.assertIsNotNone(second)
        assert second is not None
        self.assertEqual(second.task_id, 2)

    def test_failure_keeps_error_and_allows_next_task(self) -> None:
        manager = TaskManager()
        manager.enqueue_many(
            [
                ("https://example.com/bad", "坏"),
                ("https://example.com/good", "好"),
            ]
        )

        first = manager.get_next_queued()
        assert first is not None
        failed = manager.mark_failed(first.task_id, "网络失败")
        self.assertEqual(failed.status, DownloadTaskStatus.FAILED)
        self.assertEqual(failed.error_message, "网络失败")

        second = manager.get_next_queued()
        assert second is not None
        self.assertEqual(second.task_id, 2)
        self.assertEqual(manager.counts().failed, 1)
        self.assertEqual(manager.counts().running, 1)

    def test_counts_and_finished_state(self) -> None:
        manager = TaskManager()
        self.assertFalse(manager.is_finished)

        manager.enqueue_many(
            [
                ("https://example.com/1", "一"),
                ("https://example.com/2", "二"),
            ]
        )
        counts = manager.counts()
        self.assertEqual(counts.queued, 2)
        self.assertEqual(counts.total, 2)

        first = manager.get_next_queued()
        assert first is not None
        manager.mark_completed(first.task_id)
        second = manager.get_next_queued()
        assert second is not None
        manager.mark_failed(second.task_id, "失败")

        counts = manager.counts()
        self.assertEqual(counts.completed, 1)
        self.assertEqual(counts.failed, 1)
        self.assertEqual(counts.finished, 2)
        self.assertTrue(manager.is_finished)

    def test_progress_only_updates_running_task(self) -> None:
        manager = TaskManager()
        task = manager.enqueue("https://example.com/1", "一")

        with self.assertRaises(DownloadTaskStateError):
            manager.update_progress(task.task_id, _progress())

        running = manager.get_next_queued()
        assert running is not None
        updated = manager.update_progress(running.task_id, _progress(55))
        self.assertIsNotNone(updated.progress)
        assert updated.progress is not None
        self.assertEqual(updated.progress.percent, 55)

        manager.mark_completed(running.task_id)
        with self.assertRaises(DownloadTaskStateError):
            manager.update_progress(running.task_id, _progress(80))

    def test_invalid_transitions_are_rejected(self) -> None:
        manager = TaskManager()
        task = manager.enqueue("https://example.com/1", "一")

        with self.assertRaises(DownloadTaskStateError):
            manager.mark_completed(task.task_id)
        with self.assertRaises(DownloadTaskStateError):
            manager.mark_failed(task.task_id, "提前失败")

        running = manager.get_next_queued()
        assert running is not None
        manager.mark_completed(running.task_id)
        with self.assertRaises(DownloadTaskStateError):
            manager.mark_failed(running.task_id, "完成后失败")
        self.assertIsNone(manager.get_next_queued())

    def test_unknown_task_and_empty_url_are_rejected(self) -> None:
        manager = TaskManager()
        with self.assertRaises(DownloadTaskStateError):
            manager.snapshot(999)
        with self.assertRaises(ValueError):
            manager.enqueue("   ", "空")


if __name__ == "__main__":
    unittest.main()
