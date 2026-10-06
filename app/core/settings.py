"""JSON-backed application settings."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

from app.utils.paths import get_config_path

logger = logging.getLogger(__name__)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "download_path": "",
    "quality": "1080p",
    "concurrent_tasks": 2,
    "avoid_av1": True,
    "output_format": "mp4",
    "ffmpeg_path": "",
    "cookie_file": "",
}


class SettingsManager:
    """Load, access, and persist phase-one application settings.

    The manager deliberately keeps the configuration format small. Future
    settings can be added with backward-compatible defaults without changing
    callers that use :meth:`get` or :meth:`set`.
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.config_path: Path = Path(config_path) if config_path else get_config_path()
        self._data: Dict[str, Any] = dict(DEFAULT_SETTINGS)

    @property
    def data(self) -> Dict[str, Any]:
        """Return a copy of the current settings."""
        return dict(self._data)

    def load(self) -> Dict[str, Any]:
        """Load settings, repairing missing or corrupt configuration files."""
        if not self.config_path.exists():
            logger.info("Configuration file not found; creating defaults")
            self._data = dict(DEFAULT_SETTINGS)
            self.save()
            return self.data

        try:
            with self.config_path.open("r", encoding="utf-8") as config_file:
                loaded = json.load(config_file)
        except (OSError, json.JSONDecodeError) as error:
            logger.warning("Unable to read configuration; restoring defaults: %s", error)
            self._data = dict(DEFAULT_SETTINGS)
            self.save()
            return self.data

        if not isinstance(loaded, dict):
            logger.warning("Configuration root is not an object; restoring defaults")
            self._data = dict(DEFAULT_SETTINGS)
            self.save()
            return self.data

        # Defaults first keeps newly introduced options available while
        # preserving values already written by older versions.
        self._data = {**DEFAULT_SETTINGS, **loaded}
        return self.data

    def get(self, key: str, default: Any = None) -> Any:
        """Return one setting value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any, save: bool = True) -> None:
        """Set one setting value and optionally persist it."""
        self._data[key] = value
        if save:
            self.save()

    def save(self) -> None:
        """Persist settings as UTF-8 JSON."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with self.config_path.open("w", encoding="utf-8") as config_file:
            json.dump(self._data, config_file, ensure_ascii=False, indent=4)
            config_file.write("\n")

    def update(self, values: Mapping[str, Any], save: bool = True) -> None:
        """Update several settings atomically in memory."""
        self._data.update(values)
        if save:
            self.save()
