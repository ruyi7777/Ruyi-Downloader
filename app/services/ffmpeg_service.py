"""FFmpeg discovery service for Ruyi Video Downloader."""
from __future__ import annotations

import logging
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional, Union

from app.utils.paths import get_project_root

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FFmpegLocation:
    """A discovered FFmpeg executable and the source that provided it."""

    path: Path
    source: str


class FFmpegService:
    """Find FFmpeg without changing the Windows PATH."""

    def __init__(
        self,
        configured_path: Optional[Union[str, Path]] = None,
        search_path: Optional[str] = None,
        common_roots: Optional[Iterable[Path]] = None,
    ) -> None:
        self.configured_path = str(configured_path or "").strip()
        self.search_path = (
            os.environ.get("PATH", "")
            if search_path is None
            else str(search_path)
        )
        self.common_roots = (
            tuple(common_roots)
            if common_roots is not None
            else tuple(_default_common_roots())
        )

    def discover(self) -> Optional[FFmpegLocation]:
        """Return the first valid FFmpeg location, or `None`."""
        if self.configured_path:
            configured = self._normalize_configured_path()
            found = _find_executable(configured)
            if found is not None:
                return FFmpegLocation(found, "config")
            logger.warning(
                "Configured FFmpeg path is unavailable; trying automatic discovery"
            )

        from_path = shutil.which("ffmpeg", path=self.search_path or None)
        if from_path:
            found = _find_executable(Path(from_path))
            if found is not None:
                return FFmpegLocation(found, "path")

        for root in self.common_roots:
            found = _find_in_root(root)
            if found is not None:
                return FFmpegLocation(found, "common")

        logger.warning("FFmpeg executable was not found")
        return None

    def _normalize_configured_path(self) -> Path:
        configured = Path(self.configured_path).expanduser()
        if not configured.is_absolute():
            configured = get_project_root() / configured
        return configured


def _executable_names() -> tuple[str, ...]:
    if os.name == "nt":
        return ("ffmpeg.exe", "ffmpeg")
    return ("ffmpeg",)


def _find_executable(candidate: Path) -> Optional[Path]:
    candidate = candidate.expanduser()
    if candidate.is_dir():
        for name in _executable_names():
            executable = candidate / name
            if executable.is_file():
                return executable.resolve()
        return None
    if candidate.is_file():
        return candidate.resolve()
    return None


def _find_in_root(root: Path) -> Optional[Path]:
    """Search a small external-tools root without scanning the whole disk."""
    if not root.is_dir():
        return None

    direct = _find_executable(root)
    if direct is not None:
        return direct

    bin_dir = root / "bin"
    in_bin = _find_executable(bin_dir)
    if in_bin is not None:
        return in_bin

    try:
        children = [child for child in root.iterdir() if child.is_dir()]
    except OSError:
        return None

    for child in children:
        direct_child = _find_executable(child)
        if direct_child is not None:
            return direct_child
        child_bin = _find_executable(child / "bin")
        if child_bin is not None:
            return child_bin
    return None


def _default_common_roots() -> tuple[Path, ...]:
    """Return extensible tool locations suitable for dev and PyInstaller builds."""
    project_root = get_project_root()
    roots = [
        project_root / "tools",
        project_root.parent / "tools",
        Path.home() / "tools",
        Path.home() / "scoop" / "apps" / "ffmpeg" / "current" / "bin",
        Path.home() / "scoop" / "shims",
    ]

    executable_dir = Path(sys.executable).resolve().parent
    roots.extend(
        (
            executable_dir,
            executable_dir / "tools",
            executable_dir / "bin",
        )
    )

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        roots.append(Path(local_app_data) / "Microsoft" / "WinGet" / "Links")

    unique: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        resolved = root.expanduser()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(resolved)
    return tuple(unique)
