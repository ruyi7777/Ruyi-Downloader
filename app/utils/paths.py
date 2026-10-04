"""Shared path helpers for Ruyi Video Downloader."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable


def get_project_root() -> Path:
    """Return the project root directory.

    ``paths.py`` lives at ``app/utils/paths.py``, so the project root is
    three levels above this file. This works both in a source checkout and
    in a PyInstaller build where the file is bundled with the package.
    """
    return Path(__file__).resolve().parents[2]


def get_config_path() -> Path:
    """Return the path of the JSON configuration file."""
    return get_project_root() / "config" / "settings.json"


def get_logs_dir() -> Path:
    """Return the directory used for application logs."""
    return get_project_root() / "logs"


def get_log_file() -> Path:
    """Return the path of the application log file."""
    return get_logs_dir() / "ruyi.log"


def ensure_directory(path: Path) -> Path:
    """Create a directory when it does not exist and return its path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def ensure_project_directories() -> None:
    """Create directories required by the phase-one application skeleton."""
    directories: Iterable[Path] = (
        get_project_root() / "app" / "ui" / "widgets",
        get_project_root() / "app" / "core",
        get_project_root() / "app" / "services",
        get_project_root() / "app" / "utils",
        get_project_root() / "assets" / "icons",
        get_project_root() / "assets" / "images",
        get_project_root() / "config",
        get_logs_dir(),
        get_project_root() / "tests",
        get_project_root() / "build",
    )
    for directory in directories:
        ensure_directory(directory)
