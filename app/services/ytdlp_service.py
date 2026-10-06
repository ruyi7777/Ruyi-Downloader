"""yt-dlp information extraction and download adapter."""
from __future__ import annotations

import logging
import re
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional
from urllib.parse import urlsplit, urlunsplit

from yt_dlp import YoutubeDL

from app.core.download_models import (
    DownloadError,
    DownloadProgress,
    DownloadResult,
    DownloadStatus,
)
from app.core.video_info import VideoFormatInfo, VideoInfo, VideoParseError

logger = logging.getLogger(__name__)

_URL_PATTERN = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
_COOKIE_FORMAT_MESSAGE = (
    "Cookie 文件格式无效，请选择 Netscape 格式的 cookies.txt。"
)
_COOKIE_MISSING_MESSAGE = (
    "Cookie 文件不存在，请重新选择 Cookie 文件。"
)


class _CookieSafeStderr:
    """Forward stderr while dropping yt-dlp's raw Cookie line warning."""

    def __init__(self, stream) -> None:
        self._stream = stream

    def write(self, message: str) -> int:
        if "skipping cookie file entry" in message:
            return len(message)
        return self._stream.write(message)

    def flush(self) -> None:
        self._stream.flush()

    def __getattr__(self, name):
        if name in {"buffer", "raw"}:
            # Do not let yt-dlp bypass write() through the wrapped stream.
            raise AttributeError(name)
        return getattr(self._stream, name)


@contextmanager
def _cookie_safe_stderr():
    """Prevent invalid Cookie lines from leaking through yt-dlp's stderr.

    This guard is intentionally process-local. The application permits only
    one parse or download worker at a time, so no concurrent yt-dlp operation
    can observe the temporary stderr replacement.
    """
    original_stderr = sys.stderr
    if original_stderr is None:
        yield
        return
    sys.stderr = _CookieSafeStderr(original_stderr)
    try:
        yield
    finally:
        sys.stderr = original_stderr


class _SafeYtDlpLogger:
    """Route yt-dlp messages without exposing Cookie file contents."""

    @staticmethod
    def debug(_message: str) -> None:
        # Raw debug messages may echo sensitive file data.
        return None

    @staticmethod
    def info(_message: str) -> None:
        return None

    @staticmethod
    def warning(message: str) -> None:
        if _is_cookie_file_error(message.lower()):
            return
        logger.warning("yt-dlp warning: %s", _sanitize_detail(message))

    @staticmethod
    def error(message: str) -> None:
        if _is_cookie_file_error(message.lower()):
            return
        logger.warning("yt-dlp error: %s", _sanitize_detail(message))


_INFO_OPTIONS: Dict[str, Any] = {
    "skip_download": True,
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "socket_timeout": 15,
    "retries": 1,
    "logger": _SafeYtDlpLogger(),
}

# Prefer a complete MP4 file first, then fall back to separate video/audio
# streams. Bilibili commonly exposes only DASH video-only and audio-only
# formats, so the fallback is required for normal non-member downloads.
_DEFAULT_FORMAT = (
    "best[ext=mp4][vcodec^=avc1]/"
    "best[ext=mp4]/"
    "bestvideo[ext=mp4][vcodec^=avc1]+bestaudio[ext=m4a]/"
    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/"
    "bestvideo[ext=mp4]+bestaudio/"
    "bestvideo+bestaudio/"
    "best"
)


class YtDlpService:
    """Access yt-dlp metadata and download capabilities through its Python API."""

    def extract_video_info(
        self,
        url: str,
        cookie_file: Optional[Path] = None,
    ) -> VideoInfo:
        """Return normalized metadata without invoking media download."""
        options = dict(_INFO_OPTIONS)
        _apply_cookie_option(options, cookie_file)

        try:
            with _cookie_safe_stderr(), YoutubeDL(options) as ydl:
                raw_info = ydl.extract_info(url, download=False)
        except VideoParseError:
            raise
        except Exception as error:
            raw_detail = f"{type(error).__name__}: {error}"
            if _is_cookie_file_error(raw_detail.lower()):
                logger.warning(
                    "yt-dlp extraction failed: Cookie file load failed"
                )
                raise VideoParseError(
                    _cookie_failure_message(raw_detail.lower()),
                    "Cookie file load failed",
                ) from None
            detail = _sanitize_detail(raw_detail)
            logger.warning("yt-dlp extraction failed: %s", detail)
            raise VideoParseError(_friendly_parse_error(detail), detail) from error

        selected_info = _select_video_entry(raw_info)
        if selected_info is None:
            detail = "yt-dlp returned no video entry"
            logger.warning("yt-dlp extraction failed: %s", detail)
            raise VideoParseError("没有找到可解析的视频信息", detail)

        return _map_video_info(selected_info, url)

    def download_video(
        self,
        url: str,
        download_dir: Path,
        progress_callback: Optional[
            Callable[[DownloadProgress], None]
        ] = None,
        ffmpeg_path: Optional[Path] = None,
        cookie_file: Optional[Path] = None,
    ) -> DownloadResult:
        """Download one video to the configured directory."""
        options = _build_download_options(
            download_dir,
            progress_callback,
            ffmpeg_path,
            cookie_file,
        )

        try:
            with _cookie_safe_stderr(), YoutubeDL(options) as ydl:
                raw_info = ydl.extract_info(url, download=True)
                selected_info = _select_video_entry(raw_info)
                if selected_info is None:
                    detail = "yt-dlp returned no downloadable video entry"
                    logger.warning("yt-dlp download failed: %s", detail)
                    raise DownloadError("没有找到可下载的视频信息", detail)

                file_path = _resolve_downloaded_path(
                    ydl,
                    selected_info,
                    download_dir,
                )
        except DownloadError:
            raise
        except Exception as error:
            raw_detail = f"{type(error).__name__}: {error}"
            if _is_cookie_file_error(raw_detail.lower()):
                logger.warning(
                    "yt-dlp download failed: Cookie file load failed"
                )
                raise DownloadError(
                    _cookie_failure_message(raw_detail.lower()),
                    "Cookie file load failed",
                ) from None
            detail = _sanitize_detail(raw_detail)
            logger.warning("yt-dlp download failed: %s", detail)
            raise DownloadError(_friendly_download_error(detail), detail) from error

        video_id = str(selected_info.get("id") or "未知")
        title = str(selected_info.get("title") or file_path.stem)
        return DownloadResult(
            video_id=video_id,
            title=title,
            file_path=file_path,
        )


def _build_download_options(
    download_dir: Path,
    progress_callback: Optional[Callable[[DownloadProgress], None]] = None,
    ffmpeg_path: Optional[Path] = None,
    cookie_file: Optional[Path] = None,
) -> Dict[str, Any]:
    options: Dict[str, Any] = {
        "format": _DEFAULT_FORMAT,
        "outtmpl": "%(title)s [%(id)s].%(ext)s",
        "paths": {"home": str(download_dir)},
        "noplaylist": True,
        "skip_download": False,
        "continuedl": True,
        "concurrent_fragment_downloads": 1,
        "windowsfilenames": True,
        "noprogress": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 15,
        "retries": 2,
        "fragment_retries": 2,
        "logger": _SafeYtDlpLogger(),
    }

    if ffmpeg_path is not None:
        options["ffmpeg_location"] = str(ffmpeg_path)

    _apply_cookie_option(options, cookie_file)

    if progress_callback is not None:
        options["progress_hooks"] = [
            lambda hook_data: _emit_progress(progress_callback, hook_data)
        ]
    return options


def _apply_cookie_option(
    options: Dict[str, Any],
    cookie_file: Optional[Path],
) -> None:
    """Let yt-dlp read a Netscape cookie file without exposing its values."""
    if cookie_file is not None:
        options["cookiefile"] = str(cookie_file)


def _emit_progress(
    progress_callback: Callable[[DownloadProgress], None],
    hook_data: Mapping[str, Any],
) -> None:
    """Translate yt-dlp's progress hook without logging every update."""
    try:
        progress_callback(_map_progress(hook_data))
    except Exception:
        # A UI callback failure must not abort an otherwise valid download.
        logger.exception("Download progress callback failed")


def _map_progress(hook_data: Mapping[str, Any]) -> DownloadProgress:
    raw_status = str(hook_data.get("status") or "").lower()
    if raw_status == "downloading":
        status = DownloadStatus.DOWNLOADING
    elif raw_status == "finished":
        # yt-dlp reports each stream independently. A separate video/audio
        # format is not fully complete until the worker receives success.
        status = DownloadStatus.PARTIAL_FINISHED
    else:
        status = DownloadStatus.FAILED

    downloaded_bytes = _optional_nonnegative_int(
        hook_data.get("downloaded_bytes")
    )
    total_bytes = _optional_nonnegative_int(hook_data.get("total_bytes"))
    total_is_estimate = False
    if total_bytes is None:
        total_bytes = _optional_nonnegative_int(
            hook_data.get("total_bytes_estimate")
        )
        total_is_estimate = total_bytes is not None

    percent: Optional[float] = None
    if downloaded_bytes is not None and total_bytes and total_bytes > 0:
        percent = max(0.0, min(100.0, downloaded_bytes * 100.0 / total_bytes))

    speed = _nonnegative_float(hook_data.get("speed"))
    eta = _nonnegative_int(hook_data.get("eta"))

    return DownloadProgress(
        status=status,
        percent=percent,
        downloaded_bytes=downloaded_bytes,
        total_bytes=total_bytes,
        total_is_estimate=total_is_estimate,
        speed=speed,
        eta=eta,
    )


def _optional_nonnegative_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return parsed if parsed >= 0 else None


def _nonnegative_int(value: Any) -> Optional[int]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError, OverflowError):
        return None
    # yt-dlp uses -1 for unknown ETA, which the UI can safely show as zero.
    return max(0, parsed)


def _nonnegative_float(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed != parsed or parsed in (float("inf"), float("-inf")):
        return None
    return max(0.0, parsed)


def _resolve_downloaded_path(
    ydl: YoutubeDL,
    raw_info: Mapping[str, Any],
    download_dir: Path,
) -> Path:
    candidates: List[Any] = []

    requested_downloads = raw_info.get("requested_downloads")
    if isinstance(requested_downloads, (list, tuple)):
        for requested in requested_downloads:
            if isinstance(requested, Mapping):
                candidates.extend(
                    (
                        requested.get("filepath"),
                        requested.get("_filename"),
                        requested.get("filename"),
                    )
                )

    candidates.extend(
        (
            raw_info.get("filepath"),
            raw_info.get("_filename"),
            raw_info.get("filename"),
            ydl.prepare_filename(raw_info),
        )
    )

    for candidate in candidates:
        if not candidate:
            continue
        file_path = Path(candidate)
        if not file_path.is_absolute():
            file_path = download_dir / file_path
        if file_path.is_file():
            return file_path.resolve()

    detail = "yt-dlp completed without a readable output file"
    logger.warning("yt-dlp download failed: %s", detail)
    raise DownloadError("下载完成，但未找到输出文件", detail)


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


def _friendly_parse_error(detail: str) -> str:
    message = detail.lower()

    if _is_cookie_file_error(message):
        return _cookie_failure_message(message)

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

    if _requires_login(message):
        return "该视频可能需要登录或 Cookie 才能解析"

    if _is_region_restricted(message):
        return "该视频可能受地区限制，暂时无法解析"

    if _is_format_unavailable(message):
        return "没有找到当前可用的视频格式，请更换视频或稍后重试"

    if _is_unavailable(message):
        return "视频不存在、已下架或无法访问"

    if _is_network_error(message):
        return "网络连接失败，请检查网络后重试"

    return "解析失败，请检查链接后重试"


def _friendly_download_error(detail: str) -> str:
    message = detail.lower()

    if _is_cookie_file_error(message):
        return _cookie_failure_message(message)

    if _is_ffmpeg_missing(message):
        return "未找到 FFmpeg，请安装 FFmpeg 或在设置中配置 FFmpeg 路径。"

    if "ffmpeg" in message or "ffprobe" in message:
        return "FFmpeg 处理失败，请检查 FFmpeg 安装和路径"

    if any(
        marker in message
        for marker in (
            "no space left",
            "disk full",
            "not enough disk space",
            "there is not enough space",
        )
    ):
        return "磁盘空间不足，请清理后重试"

    if any(
        marker in message
        for marker in (
            "permission denied",
            "access is denied",
            "winerror 5",
            "read-only file system",
        )
    ):
        return "没有权限写入下载目录，请检查目录权限"

    if _requires_login(message):
        return "该视频可能需要登录或 Cookie 才能下载"

    if _is_region_restricted(message):
        return "该视频可能受地区限制，暂时无法下载"

    if _is_format_unavailable(message):
        return "没有找到当前可用的视频格式，请更换视频或稍后重试"

    if _is_unavailable(message):
        return "视频不存在、已下架或无法访问"

    if any(
        marker in message
        for marker in ("http error 404", "http error 410")
    ):
        return "下载地址无效或视频不存在"

    if _is_network_error(message):
        return "网络连接失败，请检查网络后重试"

    if "video unavailable" in message:
        return "视频不存在、已下架或无法访问"

    return "下载失败，请检查链接和网络后重试"


def _is_cookie_file_error(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "cookie file",
            "cookies file",
            "unable to load cookies",
            "failed to load cookies",
            "cookies could not be loaded",
            "cannot load cookies",
            "netscape http cookie file",
            "http.cookiejar",
        )
    )


def _cookie_failure_message(message: str) -> str:
    if any(
        marker in message
        for marker in ("not found", "does not exist", "no such file")
    ):
        return _COOKIE_MISSING_MESSAGE
    return _COOKIE_FORMAT_MESSAGE


def _is_ffmpeg_missing(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "ffmpeg not found",
            "ffprobe not found",
            "ffmpeg-location",
            "ffmpeg not available",
            "unable to find ffmpeg",
            "cannot find ffmpeg",
            "ffmpeg not installed",
            "no ffmpeg",
        )
    )


def _requires_login(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "sign in",
            "login required",
            "cookies",
            "authentication",
            "confirm your age",
            "not a bot",
        )
    )


def _is_format_unavailable(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "requested format is not available",
            "requested formats are not available",
            "format is not available",
            "no video formats found",
        )
    )


def _is_region_restricted(message: str) -> bool:
    return any(
        marker in message
        for marker in ("country", "region", "geo restricted", "not available in your")
    )


def _is_unavailable(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "video unavailable",
            "private video",
            "has been removed",
            "video has been deleted",
            "not available",
        )
    )


def _is_network_error(message: str) -> bool:
    return any(
        marker in message
        for marker in (
            "unable to download webpage",
            "unable to download video data",
            "network is unreachable",
            "connection refused",
            "connection reset",
            "timed out",
            "timeout",
            "getaddrinfo failed",
            "urlopen error",
        )
    )


def _sanitize_detail(detail: str) -> str:
    """Remove URL query strings so tokens are not written to logs."""

    def replace_url(match: re.Match[str]) -> str:
        value = match.group(0).rstrip("),.;]")
        parts = urlsplit(value)
        if not parts.query and not parts.fragment:
            return value
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "<query>", ""))

    return _URL_PATTERN.sub(replace_url, detail)
