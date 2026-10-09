"""Video information models and parsing errors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


class VideoParseError(RuntimeError):
    """A parsing error with a user-facing Chinese message."""

    def __init__(self, user_message: str, detail: str = "") -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail


class VideoParseCancelled(VideoParseError):
    """A cooperative parsing cancellation, distinct from a normal failure."""

    def __init__(self, detail: str = "Parsing cancelled by user") -> None:
        super().__init__("解析已取消", detail)


@dataclass(frozen=True)
class VideoFormatInfo:
    """One available media format returned by yt-dlp."""

    format_id: str
    extension: str = ""
    resolution: str = ""
    fps: Optional[float] = None
    video_codec: str = ""
    audio_codec: str = ""
    filesize: Optional[int] = None
    note: str = ""

    def describe(self) -> str:
        """Return a compact human-readable format description."""
        parts = [f"格式 {self.format_id}"]
        if self.extension:
            parts.append(self.extension)
        if self.resolution:
            parts.append(self.resolution)
        if self.fps:
            fps_value = int(self.fps) if float(self.fps).is_integer() else self.fps
            parts.append(f"{fps_value} FPS")
        if self.video_codec and self.video_codec != "none":
            parts.append(f"视频 {self.video_codec}")
        if self.audio_codec and self.audio_codec != "none":
            parts.append(f"音频 {self.audio_codec}")
        if self.note:
            parts.append(self.note)
        if self.filesize:
            parts.append(format_filesize(self.filesize))
        return " | ".join(parts)


@dataclass(frozen=True)
class VideoInfo:
    """Basic video information required by the first parsing feature."""

    video_id: str
    title: str
    uploader: str
    duration_seconds: Optional[float]
    webpage_url: str
    formats: tuple[VideoFormatInfo, ...] = ()

    @property
    def duration_display(self) -> str:
        """Return the duration in a compact Chinese UI format."""
        return format_duration(self.duration_seconds)


def format_duration(seconds: Optional[float]) -> str:
    """Format seconds as hours/minutes/seconds without external helpers."""
    if seconds is None or seconds < 0:
        return "未知"
    total_seconds = int(seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_filesize(size: int) -> str:
    """Format a byte count using common binary units."""
    value = float(size)
    units = ("B", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} B"