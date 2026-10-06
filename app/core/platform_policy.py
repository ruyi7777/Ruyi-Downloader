"""Platform detection and Cookie usage policy."""
from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlsplit

from app.core.cookie_file import CookieFileError, resolve_cookie_file

logger = logging.getLogger(__name__)


class CookieMode(str, Enum):
    """Internal Cookie usage modes reserved for future settings support."""

    AUTO = "auto"
    ALWAYS = "always"
    NEVER = "never"


# Host suffix matching keeps short links and subdomains working without
# scattering URL string checks through the parser and downloader.
_PLATFORM_HOST_SUFFIXES: Tuple[Tuple[str, str], ...] = (
    ("youtube.com", "youtube"),
    ("youtu.be", "youtube"),
    ("youtube-nocookie.com", "youtube"),
    ("bilibili.com", "bilibili"),
    ("b23.tv", "bilibili"),
    ("tiktok.com", "tiktok"),
    ("twitter.com", "x"),
    ("x.com", "x"),
    ("douyin.com", "douyin"),
    ("iesdouyin.com", "douyin"),
)

# Douyin is currently the only platform that should receive an already
# configured Cookie file automatically. Other known platforms retain their
# previously verified no-Cookie behavior. This table is the extension point
# for later policy settings.
_DEFAULT_COOKIE_MODES: Dict[str, CookieMode] = {
    "youtube": CookieMode.NEVER,
    "bilibili": CookieMode.NEVER,
    "tiktok": CookieMode.NEVER,
    "x": CookieMode.NEVER,
    "douyin": CookieMode.AUTO,
}


def detect_platform(url: str) -> str:
    """Return a stable internal platform identifier for an HTTP(S) URL."""
    try:
        hostname = urlsplit(url).hostname
    except ValueError:
        return "unknown"

    if not hostname:
        return "unknown"

    host = hostname.rstrip(".").lower()
    for suffix, platform in _PLATFORM_HOST_SUFFIXES:
        if host == suffix or host.endswith(f".{suffix}"):
            return platform
    return "unknown"


def cookie_mode_for_platform(platform: str) -> CookieMode:
    """Return the current internal Cookie mode for a platform."""
    return _DEFAULT_COOKIE_MODES.get(platform, CookieMode.NEVER)


def resolve_cookie_for_url(
    configured_path: Optional[str],
    url: str,
    mode: Optional[CookieMode] = None,
) -> Optional[Path]:
    """Resolve a Cookie file only when platform policy allows its use."""
    platform = detect_platform(url)
    effective_mode = mode or cookie_mode_for_platform(platform)
    configured = str(configured_path or "").strip()
    wants_cookie = bool(configured) and effective_mode in {
        CookieMode.AUTO,
        CookieMode.ALWAYS,
    }

    if not wants_cookie:
        logger.info(
            "Cookie policy: platform=%s, enabled=false",
            platform,
        )
        return None

    # Validation happens only for platforms that actually need Cookie use.
    # A missing or invalid configured file therefore cannot break platforms
    # such as YouTube that intentionally run without Cookie files.
    try:
        cookie_file = resolve_cookie_file(configured)
    except CookieFileError:
        logger.warning(
            "Cookie policy: platform=%s, enabled=false, file invalid",
            platform,
        )
        raise

    enabled = cookie_file is not None
    logger.info(
        "Cookie policy: platform=%s, enabled=%s",
        platform,
        str(enabled).lower(),
    )
    return cookie_file
