"""Application logging setup."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_HANDLER_MARKER = "_ruyi_handler"


def setup_logging(log_file: Path, level: str = "INFO") -> logging.Logger:
    """Configure console and rotating-file logging.

    The function is safe to call more than once. Existing handlers installed
    by this helper are replaced so repeated initialization does not duplicate
    log lines. Sensitive values such as cookies must never be passed to this
    module by callers.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)

    numeric_level = getattr(logging, str(level).upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    for handler in list(root_logger.handlers):
        if getattr(handler, _HANDLER_MARKER, False):
            root_logger.removeHandler(handler)
            handler.close()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    setattr(console_handler, _HANDLER_MARKER, True)
    root_logger.addHandler(console_handler)

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(numeric_level)
    file_handler.setFormatter(formatter)
    setattr(file_handler, _HANDLER_MARKER, True)
    root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str = "ruyi") -> logging.Logger:
    """Return a namespaced application logger."""
    return logging.getLogger(name)
