"""Background worker for non-blocking video information parsing."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from app.core.video_info_parser import VideoInfoParser


class VideoInfoWorkerSignals(QObject):
    """Signals emitted from the parsing worker back to the GUI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str, str)


class VideoInfoWorker(QRunnable):
    """Run one URL parsing request on Qt's global thread pool."""

    def __init__(
        self,
        url: str,
        parser: Optional[VideoInfoParser] = None,
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