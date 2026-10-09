"""Tests for cooperative batch parsing cancellation and GUI recovery."""
from __future__ import annotations

import os
import threading
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.core.settings import SettingsManager
from app.core.video_info import VideoInfo, VideoParseCancelled, VideoParseError
from app.ui.main_window import MainWindow
from app.ui.video_info_worker import VideoInfoBatchWorker


def _video_info(url: str) -> VideoInfo:
    return VideoInfo(
        video_id=url.rsplit("/", 1)[-1],
        title="测试标题",
        uploader="测试作者",
        duration_seconds=63,
        webpage_url=url,
    )


class _CancelAfterFirstSuccessParser:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def parse(self, url: str) -> VideoInfo:
        self.calls.append(url)
        return _video_info(url)


class _GuiCancellableParser:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._cancel_event: threading.Event | None = None

    def set_cancel_event(self, cancel_event) -> None:
        self._cancel_event = cancel_event

    def parse(self, url: str) -> VideoInfo:
        self.calls.append(url)
        if len(self.calls) >= 2 and self._cancel_event is not None:
            self._cancel_event.wait(1.0)
            if self._cancel_event.is_set():
                raise VideoParseCancelled("test cancellation")
        return _video_info(url)


class BatchCancellationTests(unittest.TestCase):
    def test_cancel_before_next_url_preserves_success_and_is_not_failure(self) -> None:
        parser = _CancelAfterFirstSuccessParser()
        urls = [
            "https://example.com/one",
            "https://example.com/two",
            "https://example.com/three",
        ]
        worker = VideoInfoBatchWorker(urls, parser=parser)
        succeeded: list[tuple[int, str]] = []
        failed: list[tuple[int, str]] = []
        finished: list[tuple[int, int]] = []

        worker.signals.succeeded.connect(
            lambda index, info: (
                succeeded.append((index, info.video_id)),
                worker.cancel(),
            )
        )
        worker.signals.failed.connect(
            lambda index, message, _detail: failed.append((index, message))
        )
        worker.signals.finished.connect(
            lambda success, failure: finished.append((success, failure))
        )

        worker.run()

        self.assertEqual(parser.calls, [urls[0]])
        self.assertEqual(succeeded, [(0, "one")])
        self.assertEqual(failed, [])
        self.assertEqual(finished, [(1, 0)])
        self.assertTrue(worker.is_cancelled)

    def test_parser_receives_thread_safe_cancel_event(self) -> None:
        from unittest.mock import MagicMock

        from app.core.video_info_parser import VideoInfoParser

        service = MagicMock()
        service.extract_video_info.return_value = _video_info(
            "https://www.bilibili.com/video/BV123"
        )
        parser = VideoInfoParser(service=service, settings=SettingsManager())
        cancel_event = threading.Event()
        parser.set_cancel_event(cancel_event)

        result = parser.parse("https://www.bilibili.com/video/BV123")

        self.assertEqual(result.video_id, "BV123")
        service.extract_video_info.assert_called_once_with(
            "https://www.bilibili.com/video/BV123",
            cookie_file=None,
            cancel_event=cancel_event,
        )


class GuiCancellationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.settings = SettingsManager()
        self.settings.load()
        self.parser = _GuiCancellableParser()
        self.window = MainWindow(settings=self.settings, parser=self.parser)
        self.window.resize(880, 760)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        if self.window._is_parsing:
            deadline = time.monotonic() + 2
            while self.window._is_parsing and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
        self.window.close()
        self.app.processEvents()

    def _process_until(self, predicate, timeout: float = 3.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.005)
        return predicate()

    def test_single_button_normal_completion_and_stale_signal_guard(self) -> None:
        self.assertEqual(self.window.parse_button.text(), "解析视频")
        self.assertTrue(self.window.parse_button.isEnabled())

        self.window.url_input.setPlainText("https://example.com/normal")
        self.window._on_parse_button_clicked()
        self.assertEqual(self.window.parse_button.text(), "取消解析")
        self.assertTrue(self.window.parse_button.isEnabled())

        completed = self._process_until(
            lambda: not self.window._is_parsing,
            timeout=2.0,
        )
        self.assertTrue(completed)
        self.assertEqual(self.window.parse_button.text(), "解析视频")
        self.assertTrue(self.window.parse_button.isEnabled())
        self.assertIn("解析完成", self.window.parse_status.text())

        # A delayed signal from an older task must not clear a newer task.
        self.window._is_parsing = True
        self.window._parse_worker = object()
        self.window._active_parse_task_id = 2
        self.window._parse_urls = ["https://example.com/current"]
        self.window._set_interaction_state("parsing")
        self.window._on_parse_finished(1, 0, 0)
        self.assertTrue(self.window._is_parsing)
        self.assertEqual(self.window._active_parse_task_id, 2)
        self.assertEqual(self.window.parse_button.text(), "取消解析")

        self.window._on_parse_finished(2, 1, 0)
        self.assertFalse(self.window._is_parsing)
        self.assertIsNone(self.window._active_parse_task_id)
        self.assertEqual(self.window.parse_button.text(), "解析视频")

    def test_gui_cancel_preserves_results_recovers_buttons_and_allows_restart(self) -> None:
        self.window.url_input.setPlainText(
            "https://example.com/one\n"
            "https://example.com/two\n"
            "https://example.com/three"
        )

        ticks = 0

        def on_tick() -> None:
            nonlocal ticks
            ticks += 1

        timer = QTimer()
        timer.setInterval(1)
        timer.timeout.connect(on_tick)
        timer.start()

        self.window._start_parse()
        self.assertTrue(self.window.parse_button.isEnabled())
        self.assertEqual(self.window.parse_button.text(), "取消解析")
        started_second = self._process_until(
            lambda: len(self.parser.calls) >= 2,
            timeout=2.0,
        )
        self.assertTrue(started_second)

        responsive_deadline = time.monotonic() + 0.03
        while time.monotonic() < responsive_deadline:
            self.app.processEvents()
            time.sleep(0.002)

        self.window._on_parse_button_clicked()
        self.assertTrue(self.window._parse_cancel_requested)
        self.assertFalse(self.window.parse_button.isEnabled())
        self.assertEqual(self.window.parse_button.text(), "正在取消…")
        self.assertIn("正在取消", self.window.parse_status.text())

        # Repeated cancellation through the same disabled state must be a no-op.
        self.window._on_parse_button_clicked()
        self.assertTrue(self.window._parse_cancel_requested)

        finished = self._process_until(
            lambda: not self.window._is_parsing,
            timeout=3.0,
        )
        timer.stop()
        self.assertTrue(finished)
        self.assertGreater(ticks, 0)

        statuses = [
            self.window.parse_results_table.item(row, 1).text()
            for row in range(self.window.parse_results_table.rowCount())
        ]
        self.assertTrue(statuses[0].startswith("成功"), statuses)
        self.assertEqual(statuses[1:], ["已取消", "已取消"], statuses)
        self.assertIn("解析已取消", self.window.parse_status.text())
        self.assertNotIn("解析失败", self.window.parse_status.text())
        self.assertEqual(len(self.parser.calls), 2)

        self.assertTrue(self.window.parse_button.isEnabled())
        self.assertEqual(self.window.parse_button.text(), "解析视频")
        self.assertTrue(self.window.download_button.isEnabled())
        self.assertTrue(self.window.url_input.isEnabled())
        self.assertIsNone(self.window._parse_worker)
        self.assertIsNone(self.window._active_parse_task_id)

        self.window.url_input.setPlainText(
            "https://www.bilibili.com/video/BVRestart"
        )
        self.window._start_parse()
        self.assertEqual(self.window.parse_button.text(), "取消解析")
        restarted = self._process_until(
            lambda: not self.window._is_parsing,
            timeout=2.0,
        )
        self.assertTrue(restarted)
        self.assertIn("解析完成", self.window.parse_status.text())
        self.assertTrue(self.window.parse_button.isEnabled())
        self.assertEqual(self.window.parse_button.text(), "解析视频")


if __name__ == "__main__":
    unittest.main()
