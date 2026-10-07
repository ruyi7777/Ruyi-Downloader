"""Extract and validate HTTP(S) URLs from arbitrary user-provided text."""
from __future__ import annotations

import re
from typing import List
from urllib.parse import urlsplit

# RFC 3986 characters are accepted inside a URL. Chinese text and punctuation
# naturally terminate the match, while ASCII wrappers are removed afterwards.
_URL_PATTERN = re.compile(
    r"https?://[A-Za-z0-9\-._~:/?#\[\]@!$&'()*+,;=%]+",
    re.IGNORECASE,
)

# These characters are commonly pasted as surrounding punctuation rather than
# part of the URL. Query separators such as ?, &, =, %, #, /, -, _ . and : are
# preserved whenever they occur before the final wrapper characters.
_TRAILING_WRAPPER_CHARS = "'.,;:!?)]}"

__all__ = ["extract_http_urls", "is_valid_http_url"]


def extract_http_urls(text: str) -> List[str]:
    """Return unique valid HTTP(S) URLs in their original appearance order."""
    if not text:
        return []

    seen = set()
    urls: List[str] = []
    for match in _URL_PATTERN.finditer(text):
        candidate = _trim_wrappers(match.group(0))
        if not candidate or not is_valid_http_url(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        urls.append(candidate)
    return urls


def is_valid_http_url(url: str) -> bool:
    """Perform basic HTTP(S) scheme and host validation."""
    if not url:
        return False

    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
    except ValueError:
        return False

    return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc) and bool(hostname)


def _trim_wrappers(candidate: str) -> str:
    """Remove only punctuation outside the URL, never its internal syntax."""
    stripped = candidate.lstrip("\"'([{<“‘（【《")
    while stripped and stripped[-1] in _TRAILING_WRAPPER_CHARS:
        stripped = stripped[:-1]
    return stripped
