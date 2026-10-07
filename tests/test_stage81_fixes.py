"""Regression tests for Stage 8.1 acceptance fixes."""
from __future__ import annotations

import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt6.QtWidgets import QApplication, QGroupBox, QScrollArea

from app.core.settings import SettingsManager
from app.core.video_info import VideoInfo
from app.services.ytdlp_service import (
    _build_download_options,
    _INFO_OPTIONS,
    _apply_js_runtime,
)
from app.ui.main_window import MainWindow


class _ImmediateParser:
    def parse(self, url: str) -> VideoInfo:
        return VideoInfo(
            video_id=url.rsplit("/", 1)[-1],
            title="测试标题",
            uploader="测试作者",
            duration_seconds=1,
            webpage_url=url,
        )


def _rects_overlap(first, second) -> bool:
    return not (
        first.right() <= second.left()
        or second.right() <= first.left()
        or first.bottom() <= second.top()
        or second.bottom() <= first.top()
    )


class Stage81FixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        settings = SettingsManager()
        settings.load()
        self.window = MainWindow(settings=settings, parser=_ImmediateParser())
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

    def _wait_for_parse(self) -> None:
        deadline = time.monotonic() + 3
        while self.window._is_parsing and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(0.005)
        self.assertFalse(self.window._is_parsing)

    def test_parse_rewrites_input_to_clean_url_list(self) -> None:
        self.window.url_input.setPlainText(
            "视频：https://youtu.be/aaa，请观看\n"
            "B站：https://www.bilibili.com/video/BV123。\n"
            "重复：https://youtu.be/aaa\n"
            "参数：https://www.youtube.com/watch?v=abc123&t=30"
        )

        self.window._start_parse()

        self.assertEqual(
            self.window.url_input.toPlainText(),
            "\n".join(
                (
                    "https://youtu.be/aaa",
                    "https://www.bilibili.com/video/BV123",
                    "https://www.youtube.com/watch?v=abc123&t=30",
                )
            ),
        )
        self._wait_for_parse()
        self.assertEqual(self.window.parse_results_table.rowCount(), 3)

    def test_parse_without_url_keeps_original_text(self) -> None:
        original = "这是一段普通文字，没有任何视频地址。"
        self.window.url_input.setPlainText(original)

        self.window._start_parse()

        self.assertEqual(self.window.url_input.toPlainText(), original)
        self.assertIn("未找到", self.window.parse_status.text())
        self.assertFalse(self.window._is_parsing)

    def _assert_layout_is_separated(self) -> None:
        table = self.window.parse_results_table.geometry()
        formats = self.window.formats_view.geometry()
        self.assertFalse(_rects_overlap(table, formats))

        info_group = next(
            group
            for group in self.window.findChildren(QGroupBox)
            if group.objectName() == "videoInfoGroup"
        )
        task_group = next(
            group
            for group in self.window.findChildren(QGroupBox)
            if group.objectName() == "taskGroup"
        )
        self.assertFalse(_rects_overlap(info_group.geometry(), task_group.geometry()))
        self.assertIsNotNone(self.window.findChild(QScrollArea))

    def test_normal_maximized_and_restored_layout_do_not_overlap(self) -> None:
        self._assert_layout_is_separated()

        self.window.resize(1200, 800)
        self.app.processEvents()
        self._assert_layout_is_separated()

        self.window.showMaximized()
        self.app.processEvents()
        self._assert_layout_is_separated()

        self.window.showNormal()
        self.window.resize(880, 760)
        self.app.processEvents()
        self._assert_layout_is_separated()

    def test_js_runtime_options_remain_enabled(self) -> None:
        info_options = dict(_INFO_OPTIONS)
        _apply_js_runtime(info_options)
        self.assertEqual(info_options["js_runtimes"], {"node": {}})

        download_options = _build_download_options(Path("downloads"))
        self.assertEqual(download_options["js_runtimes"], {"node": {}})


if __name__ == "__main__":
    unittest.main()
