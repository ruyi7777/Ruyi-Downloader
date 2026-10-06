"""Shared data models for single-video downloads."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class DownloadError(RuntimeError):
    """A download error with a user-facing Chinese message."""

    def __init__(self, user_message: str, detail: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail


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