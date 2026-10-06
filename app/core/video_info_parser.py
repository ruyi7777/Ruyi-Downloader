"""URL validation and video information parsing coordination."""
from __future__ import annotations

import logging
from typing import Optional
from urllib.parse import urlsplit

from app.core.cookie_file import CookieFileError
from app.core.platform_policy import resolve_cookie_for_url
from app.core.settings import SettingsManager
from app.core.video_info import VideoInfo, VideoParseError
from app.services.ytdlp_service import YtDlpService

logger = logging.getLogger(__name__)


class VideoInfoParser:
    """Validate a URL and coordinate parsing through the yt-dlp service."""

    def __init__(
        self,
        service: Optional[YtDlpService] = None,
        settings: Optional[SettingsManager] = None,
    ) -> None:
        self.service = service or YtDlpService()
        self.settings = settings or SettingsManager()

    def parse(self, url: str) -> VideoInfo:
        """Parse basic video information without downloading any media."""
        normalized_url = url.strip()

        try:
            self._validate_url(normalized_url)
            cookie_file = resolve_cookie_for_url(
                self.settings.get("cookie_file", ""),
                normalized_url,
            )
            video_info = self.service.extract_video_info(
                normalized_url,
                cookie_file=cookie_file,
            )
        except CookieFileError as error:
            logger.warning(
                "Video parsing failed: %s",
                error.user_message,
            )
            raise VideoParseError(
                error.user_message,
                error.detail,
            ) from None
        except VideoParseError as error:
            logger.warning(
                "Video parsing failed: %s%s",
                error.user_message,
                f" | detail: {error.detail}" if error.detail else "",
            )
            raise
        except Exception as error:  # Defensive boundary for third-party APIs.
            detail = f"{type(error).__name__}: {error}"
            logger.exception("Unexpected video parsing error: %s", detail)
            raise VideoParseError(
                "解析失败，请检查链接后重试",
                detail,
            ) from error

        logger.info(
            "Video information parsed successfully: video_id=%s, formats=%s",
            video_info.video_id,
            len(video_info.formats),
        )
        return video_info

    @staticmethod
    def _validate_url(url: str) -> None:
        if not url:
            raise VideoParseError("请输入视频链接", "URL is empty")

        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
            raise VideoParseError(
                "请输入有效的视频链接（必须以 http:// 或 https:// 开头）",
                f"Invalid URL scheme or host: scheme={parsed.scheme!r}",
            )