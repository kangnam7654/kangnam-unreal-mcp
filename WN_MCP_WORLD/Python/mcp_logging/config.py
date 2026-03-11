"""Logging configuration loader.

Reads [Logging] section from Settings.ini. Falls back to defaults if file is missing.
"""

import configparser
from pathlib import Path
from typing import Dict


SETTINGS_PATH = Path(__file__).parent.parent / "Settings.ini"

MISC = 5

_LEVEL_MAP = {
    "MISC": MISC,
    "DEBUG": 10,
    "INFO": 20,
    "WARNING": 30,
    "ERROR": 40,
    "CRITICAL": 50,
}

_DEFAULTS = {
    "log_level": "MISC",
    "log_retention_days": "7",
    "max_log_files": "2",
    "log_auto_cleanup": "true",
}


def load_settings() -> Dict[str, str]:
    """Load [Logging] section from Settings.ini."""
    config = configparser.ConfigParser()
    if SETTINGS_PATH.exists():
        config.read(SETTINGS_PATH, encoding="utf-8")
    if config.has_section("Logging"):
        merged = dict(_DEFAULTS)
        merged.update({k.lower(): v for k, v in config["Logging"].items()})
        return merged
    return dict(_DEFAULTS)


def parse_level(level_name: str) -> int:
    """Convert level name to logging level value."""
    return _LEVEL_MAP.get(level_name.upper(), 20)
