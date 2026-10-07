"""Offscreen GUI test for sequential multi-URL parsing."""
from __future__ import annotations

import os
import time
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from app.core.settings import SettingsManager
from app.core.video_info import VideoInfo, VideoParseError
from app.ui.main_window import MainWindow


class _DelayedParser:
    def parse(self, url: str) -> VideoInfo:
        time.sleep(0.04)
        if "example.com" in url:
            raise VideoParseError("测试链接无效", "test failure")
        return VideoInfo(
            video_id=url.rsplit("/", 1)[-1],
            title="测试标题",
            uploader="测试作者",
            duration_seconds=63,
            webpage_url=url,
        )


class MainWindowBatchParsingTests(unittest.TestCase):
    def test_multi_url_parse_updates_each_row_without_blocking_gui(self) -> None:
        app = QApplication.instance() or QApplication([])
        settings = SettingsManager()
        settings.load()
        window = MainWindow(settings=settings, parser=_DelayedParser())
        window.show()
        try:
            window.url_input.setPlainText(
                "文字 [https://www.bilibili.com/video/BV123]，"
                "失败 https://example.com/bad；"
                "成功 'https://youtu.be/abc123'"
            )

            ticks = 0

            def on_tick() -> None:
                nonlocal ticks
                ticks += 1

            timer = QTimer()
            timer.setInterval(20)
            timer.timeout.connect(on_tick)
            timer.start()
            window._start_parse()

            deadline = time.monotonic() + 5
            saw_disabled_controls = False
            while window._is_parsing and time.monotonic() < deadline:
                app.processEvents()
                saw_disabled_controls = (
                    saw_disabled_controls or not window.download_button.isEnabled()
                )
                time.sleep(0.005)
            timer.stop()

            statuses = [
                window.parse_results_table.item(row, 1).text()
                for row in range(window.parse_results_table.rowCount())
            ]
            self.assertFalse(window._is_parsing)
            self.assertEqual(window.parse_results_table.rowCount(), 3)
            self.assertTrue(statuses[0].startswith("成功"), statuses)
            self.assertTrue(statuses[1].startswith("失败"), statuses)
            self.assertTrue(statuses[2].startswith("成功"), statuses)
            self.assertIn("成功 2 个", window.parse_status.text())
            self.assertGreater(ticks, 0)
            self.assertTrue(saw_disabled_controls)
            self.assertTrue(window.download_button.isEnabled())
            window._set_interaction_state("idle")
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
