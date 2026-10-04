"""yt-dlp information extraction adapter."""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

from yt_dlp import YoutubeDL

from app.core.video_info import VideoFormatInfo, VideoInfo, VideoParseError

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)

_YDL_OPTIONS: Dict[str, Any] = {
    "skip_download": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 15,
    "retries": 1,
}


class YtDlpService:
    """Extract video metadata using the official yt-dlp Python API."""

    def extract_video_info(self, url: str) -> VideoInfo:
        """Return normalized metadata without invoking media download."""
        try:
            with YoutubeDL(dict(_YDL_OPTIONS)) as ydl:
                raw_info = ydl.extract_info(url, download=False)
        except VideoParseError:
            raise
        except Exception as error:
            detail = _sanitize_detail(f"{type(error).__name__}: {error}")
            logger.warning("yt-dlp extraction failed: %s", detail)
            raise VideoParseError(_friendly_error(detail), detail) from error

        selected_info = _select_video_entry(raw_info)
        if selected_info is None:
            detail = "yt-dlp returned no video entry"
            logger.warning("yt-dlp extraction failed: %s", detail)
            raise VideoParseError("没有找到可解析的视频信息", detail)

        return _map_video_info(selected_info, url)


def _select_video_entry(raw_info: Any) -> Optional[Mapping[str, Any]]:
    if not isinstance(raw_info, Mapping):
        return None

    entries = raw_info.get("entries")
    if entries is None:
        return raw_info

    if isinstance(entries, (list, tuple)):
        for entry in entries:
            if isinstance(entry, Mapping):
                return entry
    return None


def _map_video_info(raw_info: Mapping[str, Any], source_url: str) -> VideoInfo:
    video_id = str(raw_info.get("id") or "未知")
    title = str(raw_info.get("title") or raw_info.get("fulltitle") or "未知标题")
    uploader = str(
        raw_info.get("uploader")
        or raw_info.get("channel")
        or raw_info.get("creator")
        or raw_info.get("artist")
        or "未知作者"
    )
    webpage_url = str(
        raw_info.get("webpage_url")
        or raw_info.get("original_url")
        or source_url
    )

    duration_value = raw_info.get("duration")
    duration_seconds: Optional[float]
    try:
        duration_seconds = float(duration_value) if duration_value is not None else None
    except (TypeError, ValueError):
        duration_seconds = None

    raw_formats = raw_info.get("formats")
    formats: List[VideoFormatInfo] = []
    if isinstance(raw_formats, (list, tuple)):
        for raw_format in raw_formats:
            if isinstance(raw_format, Mapping):
                formats.append(_map_format(raw_format))

    return VideoInfo(
        video_id=video_id,
        title=title,
        uploader=uploader,
        duration_seconds=duration_seconds,
        webpage_url=webpage_url,
        formats=tuple(formats),
    )


def _map_format(raw_format: Mapping[str, Any]) -> VideoFormatInfo:
    resolution = str(raw_format.get("resolution") or "")
    if not resolution:
        width = raw_format.get("width")
        height = raw_format.get("height")
        if width and height:
            resolution = f"{width}x{height}"
        elif height:
            resolution = f"{height}p"
        elif raw_format.get("vcodec") in (None, "none"):
            resolution = "仅音频"

    fps_value = raw_format.get("fps")
    try:
        fps = float(fps_value) if fps_value is not None else None
    except (TypeError, ValueError):
        fps = None

    filesize_value = raw_format.get("filesize")
    if filesize_value is None:
        filesize_value = raw_format.get("filesize_approx")
    try:
        filesize = int(filesize_value) if filesize_value is not None else None
    except (TypeError, ValueError):
        filesize = None

    return VideoFormatInfo(
        format_id=str(raw_format.get("format_id") or "未知"),
        extension=str(raw_format.get("ext") or ""),
        resolution=resolution,
        fps=fps,
        video_codec=str(raw_format.get("vcodec") or ""),
        audio_codec=str(raw_format.get("acodec") or ""),
        filesize=filesize,
        note=str(raw_format.get("format_note") or ""),
    )


def _friendly_error(detail: str) -> str:
    message = detail.lower()

    if any(
        marker in message
        for marker in (
            "unsupported url",
            "no suitable extractor",
            "not a valid url",
            "invalid url",
        )
    ):
        return "暂不支持此链接，请检查 URL 是否正确"

    if any(
        marker in message
        for marker in (
            "sign in",
            "login required",
            "cookies",
            "authentication",
            "confirm your age",
        )
    ):
        return "该视频可能需要登录或 Cookie 才能解析"

    if any(
        marker in message
        for marker in ("country", "region", "geo restricted", "not available in your")
    ):
        return "该视频可能受地区限制，暂时无法解析"

    if any(
        marker in message
        for marker in (
            "video unavailable",
            "private video",
            "has been removed",
            "video has been deleted",
            "not available",
        )
    ):
        return "视频不存在、已下架或无法访问"

    if any(
        marker in message
        for marker in (
            "unable to download webpage",
            "network is unreachable",
            "connection refused",
            "connection reset",
            "timed out",
            "timeout",
            "getaddrinfo failed",
            "urlopen error",
        )
    ):
        return "网络连接失败，请检查网络后重试"

    return "解析失败，请检查链接后重试"


def _sanitize_detail(detail: str) -> str:
    """Remove URL query strings so tokens are not written to logs."""

    def replace_url(match: re.Match[str]) -> str:
        value = match.group(0).rstrip("),.;]")
        parts = urlsplit(value)
        if not parts.query and not parts.fragment:
            return value
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "<query>", ""))

    return _URL_PATTERN.sub(replace_url, detail)