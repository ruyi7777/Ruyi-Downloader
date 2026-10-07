"""Tests for sequential multi-URL parsing worker behavior."""
from __future__ import annotations

import unittest

from PyQt6.QtCore import QCoreApplication

from app.core.video_info import VideoInfo, VideoParseError
from app.ui.video_info_worker import VideoInfoBatchWorker


class _FakeParser:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def parse(self, url: str) -> VideoInfo:
        self.calls.append(url)
        if "bad" in url:
            raise VideoParseError("链接无效", "test detail")
        return VideoInfo(
            video_id=url.rsplit("/", 1)[-1],
            title="测试视频",
            uploader="测试作者",
            duration_seconds=60,
            webpage_url=url,
        )


class VideoInfoBatchWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_sequential_order_and_failure_isolation(self) -> None:
        parser = _FakeParser()
        urls = [
            "https://example.com/one",
            "https://example.com/bad",
            "https://example.com/three",
        ]
        worker = VideoInfoBatchWorker(urls, parser=parser)

        started: list[int] = []
        succeeded: list[tuple[int, str]] = []
        failed: list[tuple[int, str]] = []
        finished: list[tuple[int, int]] = []
        worker.signals.started.connect(started.append)
        worker.signals.succeeded.connect(
            lambda index, info: succeeded.append((index, info.video_id))
        )
        worker.signals.failed.connect(
            lambda index, message, _detail: failed.append((index, message))
        )
        worker.signals.finished.connect(
            lambda success, failure: finished.append((success, failure))
        )

        worker.run()

        self.assertEqual(parser.calls, urls)
        self.assertEqual(started, [0, 1, 2])
        self.assertEqual(
            succeeded,
            [(0, "one"), (2, "three")],
        )
        self.assertEqual(failed, [(1, "链接无效")])
        self.assertEqual(finished, [(2, 1)])


if __name__ == "__main__":
    unittest.main()
