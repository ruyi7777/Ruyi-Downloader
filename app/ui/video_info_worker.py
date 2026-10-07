"""Background workers for non-blocking video information parsing."""
from __future__ import annotations

import logging
from typing import Sequence

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from app.core.video_info_parser import VideoInfoParser

logger = logging.getLogger(__name__)


class VideoInfoWorkerSignals(QObject):
    """Signals emitted from a single parsing worker back to the GUI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str, str)


class VideoInfoWorker(QRunnable):
    """Run one URL parsing request on Qt's global thread pool."""

    def __init__(
        self,
        url: str,
        parser: VideoInfoParser | None = None,
    ) -> None:
        super().__init__()
        self.url = url
        self.parser = parser or VideoInfoParser()
        self.signals = VideoInfoWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Execute parsing without touching any Qt GUI object."""
        try:
            video_info = self.parser.parse(self.url)
        except Exception as error:
            user_message = getattr(error, "user_message", str(error))
            detail = getattr(error, "detail", str(error))
            self.signals.failed.emit(user_message, detail)
            return

        self.signals.succeeded.emit(video_info)


class VideoInfoBatchWorkerSignals(QObject):
    """Signals emitted while one URL after another is parsed sequentially."""

    started = pyqtSignal(int)
    succeeded = pyqtSignal(int, object)
    failed = pyqtSignal(int, str, str)
    finished = pyqtSignal(int, int)


class VideoInfoBatchWorker(QRunnable):
    """Parse multiple URLs sequentially without blocking the GUI thread."""

    def __init__(
        self,
        urls: Sequence[str],
        parser: VideoInfoParser | None = None,
    ) -> None:
        super().__init__()
        self.urls = tuple(urls)
        self.parser = parser or VideoInfoParser()
        self.signals = VideoInfoBatchWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Continue through every URL even when an individual URL fails."""
        success_count = 0
        failure_count = 0

        for index, url in enumerate(self.urls):
            self.signals.started.emit(index)
            try:
                video_info = self.parser.parse(url)
            except Exception as error:
                failure_count += 1
                user_message = getattr(error, "user_message", str(error))
                detail = getattr(error, "detail", str(error))
                self.signals.failed.emit(index, user_message, detail)
                continue

            success_count += 1
            self.signals.succeeded.emit(index, video_info)

        logger.info(
            "Batch parsing finished: total=%s, success=%s, failure=%s",
            len(self.urls),
            success_count,
            failure_count,
        )
        self.signals.finished.emit(success_count, failure_count)
