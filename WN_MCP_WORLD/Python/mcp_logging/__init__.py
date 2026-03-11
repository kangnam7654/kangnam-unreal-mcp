"""MCP Logging — file logging + in-memory ring buffer.

Usage:
    from mcp_logging import initialize, set_level, get_level, get_recent_entries

    # Server startup (once)
    initialize()

    # In any module
    import logging
    logger = logging.getLogger("wn_mcp_world.my_module")
    logger.info("message")
"""

import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional

from .config import MISC, load_settings, parse_level
from .ring_buffer import RingBufferHandler

__all__ = [
    "MISC",
    "initialize",
    "set_level",
    "get_level",
    "get_recent_entries",
]

LOG_DIR = Path(__file__).parent.parent / "logs"
RING_BUFFER_SIZE = 1000

_ring_handler: Optional[RingBufferHandler] = None
_file_handler: Optional[logging.FileHandler] = None


def initialize():
    """Initialize logging system. Call once at server startup. Idempotent."""
    logging.addLevelName(MISC, "MISC")

    root = logging.getLogger("wn_mcp_world")

    # Guard: skip if already initialized
    if root.handlers:
        return

    settings = load_settings()
    log_level = parse_level(settings.get("log_level", "MISC"))

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler (with filesystem error fallback)
    global _file_handler
    try:
        LOG_DIR.mkdir(exist_ok=True)
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = LOG_DIR / f"mcp_{today}.log"
        _file_handler = logging.FileHandler(log_file, encoding="utf-8")
        _file_handler.setLevel(MISC)
        _file_handler.setFormatter(formatter)
        root.addHandler(_file_handler)
    except OSError as e:
        # Fallback: stderr if file creation fails
        fallback = logging.StreamHandler(sys.stderr)
        fallback.setLevel(MISC)
        fallback.setFormatter(formatter)
        root.addHandler(fallback)
        log_file = None
        print(f"[WARNING] Log file creation failed, using stderr: {e}", file=sys.stderr)

    # Ring buffer handler
    global _ring_handler
    _ring_handler = RingBufferHandler(maxlen=RING_BUFFER_SIZE)
    _ring_handler.setLevel(MISC)
    root.addHandler(_ring_handler)

    root.setLevel(log_level)

    # Auto cleanup
    if log_file and settings.get("log_auto_cleanup", "true").lower() == "true":
        cleanup_old_logs(settings)

    root.info("Logging initialized (level=%s, file=%s)",
              logging.getLevelName(log_level),
              log_file.name if log_file else "stderr")


def set_level(level_name: str) -> str:
    """Change log level at runtime. Returns the new level name."""
    level = parse_level(level_name)
    logger = logging.getLogger("wn_mcp_world")
    logger.setLevel(level)
    return logging.getLevelName(level)


def get_level() -> str:
    """Get current log level name."""
    return logging.getLevelName(logging.getLogger("wn_mcp_world").level)


def get_recent_entries(
    count: int = 20,
    level: str = "INFO",
    keyword: str = "",
) -> Dict[str, Any]:
    """Get filtered log entries from the ring buffer."""
    if _ring_handler is None:
        return {"total_in_buffer": 0, "returned": 0, "filter": {}, "entries": []}

    min_level = parse_level(level)
    entries = _ring_handler.get_entries(
        count=max(1, min(count, 200)),
        min_level=min_level,
        keyword=keyword,
    )
    return {
        "total_in_buffer": _ring_handler.total_count,
        "returned": len(entries),
        "filter": {"level": level, "keyword": keyword},
        "entries": entries,
    }


def cleanup_old_logs(settings: Dict[str, str]):
    """Delete old log files based on retention policy."""
    retention_days = int(settings.get("log_retention_days", "7"))
    max_files = int(settings.get("max_log_files", "2"))
    today = datetime.now().strftime("%Y-%m-%d")

    log_files = sorted(LOG_DIR.glob("mcp_*.log"))

    # Delete by retention days
    cutoff = datetime.now() - timedelta(days=retention_days)
    for f in log_files:
        date_str = f.stem.replace("mcp_", "")
        try:
            file_date = datetime.strptime(date_str, "%Y-%m-%d")
            if file_date < cutoff and date_str != today:
                f.unlink()
        except ValueError:
            continue

    # Delete by max file count (0 = unlimited)
    if max_files > 0:
        remaining = sorted(LOG_DIR.glob("mcp_*.log"))
        if len(remaining) > max_files:
            for f in remaining[:-max_files]:
                date_str = f.stem.replace("mcp_", "")
                if date_str != today:
                    f.unlink()
