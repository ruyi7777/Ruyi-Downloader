"""Shared data models for single-video downloads."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class DownloadError(RuntimeError):
    """A download error with a user-facing Chinese message."""

    def __init__(self, user_message: str, detail: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail


class DownloadStatus(str, Enum):
    """User-facing states for one single-video download."""

    WAITING = "waiting"
    DOWNLOADING = "downloading"
    PARTIAL_FINISHED = "partial_finished"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class DownloadProgress:
    """Normalized progress emitted by yt-dlp and passed through the worker."""

    status: DownloadStatus
    percent: Optional[float] = None
    downloaded_bytes: Optional[int] = None
    total_bytes: Optional[int] = None
    total_is_estimate: bool = False
    speed: Optional[float] = None
    eta: Optional[int] = None


@dataclass(frozen=True)
class DownloadResult:
    """Successful single-video download result."""

    video_id: str
    title: str
    file_path: Path

    @property
    def file_name(self) -> str:
        """Return the output file name for user-facing messages."""
        return self.file_path.name