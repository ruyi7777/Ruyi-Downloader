"""Background worker for non-blocking single-video downloads."""
from __future__ import annotations

from typing import Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from app.core.downloader import VideoDownloader


class DownloadWorkerSignals(QObject):
    """Signals emitted from the download worker back to the GUI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str, str)


class DownloadWorker(QRunnable):
    """Run one single-video download on Qt's global thread pool."""

    def __init__(
        self,
        url: str,
        downloader: Optional[VideoDownloader] = None,
    ) -> None:
        super().__init__()
        self.url = url
        self.downloader = downloader or VideoDownloader()
        self.signals = DownloadWorkerSignals()

    @pyqtSlot()
    def run(self) -> None:
        """Execute the download without touching any Qt GUI object."""
        try:
            result = self.downloader.download(self.url)
        except Exception as error:
            user_message = getattr(error, "user_message", str(error))
            detail = getattr(error, "detail", str(error))
            self.signals.failed.emit(user_message, detail)
            return

        self.signals.succeeded.emit(result)