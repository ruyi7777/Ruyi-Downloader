"""Ruyi Video Downloader application entry point."""
from __future__ import annotations

import logging
import sys

from PyQt6.QtWidgets import QApplication

from app.core.settings import SettingsManager
from app.services.ffmpeg_service import FFmpegService
from app.ui.main_window import MainWindow
from app.utils.logger import setup_logging
from app.utils.paths import ensure_project_directories, get_log_file


def main() -> int:
    """Initialize the application and run the Qt event loop."""
    ensure_project_directories()

    # Configure logging before loading settings so configuration repair and
    # validation messages are captured in the log file.
    setup_logging(get_log_file())
    settings = SettingsManager()
    settings.load()

    log_level = settings.get("log_level", "INFO")
    if log_level != "INFO":
        setup_logging(get_log_file(), level=log_level)

    logger = logging.getLogger("ruyi")
    logger.info("Ruyi Video Downloader starting")
    logger.info("Configuration loaded from %s", settings.config_path)

    ffmpeg_location = FFmpegService(
        configured_path=str(settings.get("ffmpeg_path", "") or "")
    ).discover()
    if ffmpeg_location is not None:
        logger.info(
            "FFmpeg discovered at startup: source=%s, path=%s",
            ffmpeg_location.source,
            ffmpeg_location.path,
        )
    else:
        logger.warning(
            "FFmpeg was not found at startup; merging downloads may fail"
        )

    app = QApplication(sys.argv)
    app.setApplicationName("如意视频下载器")
    app.setApplicationDisplayName("如意视频下载器")
    app.setOrganizationName("Ruyi Video Downloader")

    window = MainWindow(settings=settings)
    window.show()

    exit_code = app.exec()
    logger.info("Ruyi Video Downloader stopped with exit code %s", exit_code)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
