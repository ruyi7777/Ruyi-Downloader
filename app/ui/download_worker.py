"""Background worker for non-blocking single-video downloads."""
from __future__ import annotations

import time
from typing import Optional

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal, pyqtSlot

from app.core.download_models import DownloadProgress, DownloadStatus
from app.core.downloader import VideoDownloader

_PROGRESS_UPDATE_INTERVAL_SECONDS = 0.2


class DownloadWorkerSignals(QObject):
    """Signals emitted from the download worker back to the GUI thread."""

    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str, str)
    progress = pyqtSignal(object)


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
        self._last_progress_emit_at = 0.0

    @pyqtSlot()
    def run(self) -> None:
        """Execute the download without touching any Qt GUI object."""
        try:
            result = self.downloader.download(
                self.url,
                progress_callback=self._handle_progress,
            )
        except Exception as error:
            user_message = getattr(error, "user_message", str(error))
            detail = getattr(error, "detail", str(error))
            self.signals.failed.emit(user_message, detail)
            return

        self.signals.succeeded.emit(result)

    def _handle_progress(self, progress: DownloadProgress) -> None:
        """Throttle high-frequency downloading updates before crossing Qt."""
        now = time.monotonic()
        must_emit = (
            progress.status is not DownloadStatus.DOWNLOADING
            or self._last_progress_emit_at == 0.0
            or now - self._last_progress_emit_at
            >= _PROGRESS_UPDATE_INTERVAL_SECONDS
        )
        if not must_emit:
            return

        self._last_progress_emit_at = now
        try:
            self.signals.progress.emit(progress)
        except RuntimeError:
            # The Qt application may already be shutting down while yt-dlp
            # still sends the last hook; no GUI object can receive it anymore.
            return
