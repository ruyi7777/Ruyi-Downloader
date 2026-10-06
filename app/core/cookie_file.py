"""Cookie file path validation for Ruyi Video Downloader."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.utils.paths import get_project_root


class CookieFileError(Exception):
    """Raised when a configured Cookie file cannot be used safely."""

    def __init__(self, user_message: str, detail: str) -> None:
        super().__init__(user_message)
        self.user_message = user_message
        self.detail = detail


def resolve_cookie_file(configured_path: Optional[str]) -> Optional[Path]:
    """Return a valid Cookie file path, or `None` when no file is configured.

    The file is never read here. yt-dlp receives only the path and reads the
    Netscape cookies file itself, keeping Cookie values out of application
    logs, settings, and UI text.
    """
    configured = str(configured_path or "").strip()
    if not configured:
        return None

    cookie_path = Path(configured).expanduser()
    if not cookie_path.is_absolute():
        cookie_path = get_project_root() / cookie_path

    if not cookie_path.exists():
        raise CookieFileError(
            "Cookie 文件不存在，请重新选择 Cookie 文件。",
            "Cookie file is missing",
        )
    if not cookie_path.is_file():
        raise CookieFileError(
            "Cookie 路径不是有效的文件。",
            "Cookie path is not a file",
        )
    return cookie_path.resolve()
