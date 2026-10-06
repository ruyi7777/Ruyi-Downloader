"""Single-video download orchestration."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit

from app.core.download_models import DownloadError, DownloadResult
from app.core.settings import SettingsManager
from app.services.ytdlp_service import YtDlpService
from app.utils.paths import ensure_directory, get_project_root

logger = logging.getLogger(__name__)


class VideoDownloader:
    """Coordinate one yt-dlp download using configured application paths."""

    def __init__(
        self,
        settings: Optional[SettingsManager] = None,
        service: Optional[YtDlpService] = None,
    ) -> None:
        self.settings = settings or SettingsManager()
        self.service = service or YtDlpService()

    @property
    def download_path(self) -> Path:
        """Resolve the configured download directory without hardcoding it."""
        configured_path = str(self.settings.get("download_path", "") or "").strip()
        if not configured_path:
            return Path.home() / "Downloads" / "Ruyi Video Downloader"

        path = Path(configured_path).expanduser()
        if not path.is_absolute():
            path = get_project_root() / path
        return path

    def download(self, url: str) -> DownloadResult:
        """Download one URL and return the resulting file information."""
        normalized_url = url.strip()
        target_directory = self.download_path

        try:
            self._validate_url(normalized_url)
            ensure_directory(target_directory)
        except DownloadError:
            self._log_failure(normalized_url, None, None)
            raise
        except OSError as error:
            detail = f"{type(error).__name__}: {error}"
            download_error = DownloadError(
                "无法创建下载目录，请检查目录权限",
                detail,
            )
            self._log_failure(normalized_url, download_error.user_message, detail)
            raise download_error from error

        logger.info(
            "Video download started: host=%s, directory=%s",
            _url_host(normalized_url),
            target_directory,
        )

        try:
            result = self.service.download_video(normalized_url, target_directory)
        except DownloadError as error:
            self._log_failure(normalized_url, error.user_message, error.detail)
            raise
        except Exception as error:
            detail = type(error).__name__
            download_error = DownloadError("下载失败，请检查链接和网络后重试", detail)
            self._log_failure(
                normalized_url,
                download_error.user_message,
                detail,
            )
            raise download_error from error

        logger.info(
            "Video download completed: video_id=%s, file=%s",
            result.video_id,
            result.file_name,
        )
        return result

    @staticmethod
    def _validate_url(url: str) -> None:
        if not url:
            raise DownloadError("请输入视频链接", "URL is empty")

        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise DownloadError(
                "请输入有效的视频链接（必须以 http:// 或 https:// 开头）",
                f"Invalid URL scheme or host: scheme={parsed.scheme!r}",
            )

    @staticmethod
    def _log_failure(url: str, user_message: Optional[str], detail: Optional[str]) -> None:
        if user_message is None:
            logger.warning(
                "Video download failed: %s",
                detail or "URL validation failed",
            )
            return
        logger.warning(
            "Video download failed: %s%s",
            user_message,
            f" | detail: {detail}" if detail else "",
        )


def _url_host(url: str) -> str:
    try:
        return urlsplit(url).netloc or "unknown"
    except ValueError:
        return "unknown"