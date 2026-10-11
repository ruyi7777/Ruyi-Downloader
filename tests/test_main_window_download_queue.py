"""Offscreen GUI tests for Stage 8.2 sequential download queue integration."""
from __future__ import annotations

import os
import time
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.core.download_models import DownloadError, DownloadProgress, DownloadResult, DownloadStatus
from app.core.settings import SettingsManager
from app.core.video_info import VideoInfo, VideoParseError
from app.ui.main_window import MainWindow


class _QueueParser:
    def parse(self, url: str) -> VideoInfo:
        if "bad" in url:
            raise VideoParseError("解析失败", "bad parse")
        return VideoInfo(
            video_id=url.rsplit("/", 1)[-1],
            title=f"标题-{url.rsplit('/', 1)[-1]}",
            uploader="测试作者",
            duration_seconds=10,
            webpage_url=url,
        )


class _QueueDownloader:
    def __init__(self) -> None:
        self.calls: list[str] = []

    @property
    def download_path(self) -> Path:
        return Path("downloads")

    def download(self, url: str, progress_callback=None) -> DownloadResult:
        self.calls.append(url)
        if progress_callback is not None:
            progress_callback(
                DownloadProgress(
                    status=DownloadStatus.DOWNLOADING,
                    percent=40.0,
                    downloaded_bytes=40,
                    total_bytes=100,
                )
            )
        if "fail" in url:
            raise DownloadError("模拟下载失败", "fake failure")
        if progress_callback is not None:
            progress_callback(
                DownloadProgress(
                    status=DownloadStatus.PARTIAL_FINISHED,
                    percent=100.0,
                    downloaded_bytes=100,
                    total_bytes=100,
                )
            )
        return DownloadResult(
            video_id=url.rsplit("/", 1)[-1],
            title=f"标题-{url.rsplit('/', 1)[-1]}",
            file_path=Path(f"{url.rsplit('/', 1)[-1]}.mp4"),
        )


class MainWindowDownloadQueueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.settings = SettingsManager()
        self.settings.load()
        self.parser = _QueueParser()
        self.downloader = _QueueDownloader()
        self.window = MainWindow(
            settings=self.settings,
            parser=self.parser,
            downloader=self.downloader,
        )
        self.window.resize(1000, 900)
        self.window.show()
        self.app.processEvents()

    def tearDown(self) -> None:
        if self.window._is_parsing or self.window._is_downloading:
            deadline = time.monotonic() + 2
            while (
                self.window._is_parsing or self.window._is_downloading
            ) and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.005)
        self.window.close()
        self.app.processEvents()

    def _process_until(self, predicate, timeout: float = 4.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return True
            time.sleep(0.005)
        return predicate()

    def _parse(self, text: str) -> None:
        self.window.url_input.setPlainText(text)
        self.window._start_parse()
        self.assertTrue(
            self._process_until(lambda: not self.window._is_parsing)
        )

    def _queue_statuses(self) -> list[str]:
        return [
            self.window.download_queue_table.item(row, 2).text()
            for row in range(self.window.download_queue_table.rowCount())
        ]

    def test_successful_rows_queue_in_order_and_failure_continues(self) -> None:
        ticks = 0

        def on_tick() -> None:
            nonlocal ticks
            ticks += 1

        timer = QTimer()
        timer.setInterval(1)
        timer.timeout.connect(on_tick)
        timer.start()

        self._parse(
            "https://example.com/ok1\n"
            "https://example.com/bad\n"
            "https://example.com/fail\n"
            "https://example.com/ok2"
        )
        self.assertEqual(
            [
                self.window.parse_results_table.item(row, 1).text()
                for row in range(4)
            ],
            ["成功", "失败：解析失败", "成功", "成功"],
        )

        self.window._start_download()
        self.assertTrue(self.window._is_downloading)
        self.assertFalse(self.window.parse_button.isEnabled())
        self.assertFalse(self.window.url_input.isEnabled())
        self.assertTrue(
            self._process_until(lambda: not self.window._is_downloading)
        )
        timer.stop()

        self.assertEqual(
            self.downloader.calls,
            [
                "https://example.com/ok1",
                "https://example.com/fail",
                "https://example.com/ok2",
            ],
        )
        self.assertEqual(
            self._queue_statuses(),
            ["完成", "失败", "完成"],
        )
        self.assertIn(
            "模拟下载失败",
            self.window.download_queue_table.item(1, 3).text(),
        )
        self.assertIn(
            "成功 2 个，失败 1 个",
            self.window.download_status.text(),
        )
        self.assertTrue(self.window.parse_button.isEnabled())
        self.assertTrue(self.window.download_button.isEnabled())
        self.assertTrue(self.window.url_input.isEnabled())
        self.assertEqual(self.window.download_progress_bar.format(), "队列结束")
        self.assertGreater(ticks, 0)

    def test_multiple_unparsed_urls_prompt_before_download(self) -> None:
        self.window.url_input.setPlainText(
            "https://example.com/one\nhttps://example.com/two"
        )
        self.window._start_download()

        self.assertFalse(self.window._is_downloading)
        self.assertFalse(
            self.window._download_queue_controller.is_running
        )
        self.assertIn("请先解析", self.window.download_status.text())
        self.assertEqual(self.downloader.calls, [])

    def test_single_unparsed_url_uses_same_queue_path(self) -> None:
        self.window.url_input.setPlainText("https://example.com/single")
        self.window._start_download()

        self.assertTrue(
            self._process_until(lambda: not self.window._is_downloading)
        )
        self.assertEqual(self.downloader.calls, ["https://example.com/single"])
        self.assertEqual(self._queue_statuses(), ["完成"])
        self.assertIn(
            "成功 1 个，失败 0 个",
            self.window.download_status.text(),
        )
        self.assertTrue(self.window.download_button.isEnabled())


if __name__ == "__main__":
    unittest.main()
