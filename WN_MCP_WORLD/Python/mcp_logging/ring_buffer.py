"""In-memory ring buffer handler for Agent log queries.

Stores recent log entries in a deque for fast filtered retrieval via get_recent_logs tool.
"""

import logging
from collections import deque
from datetime import datetime
from typing import List, Dict, Any


class RingBufferHandler(logging.Handler):
    """Logging handler that stores entries in a fixed-size ring buffer."""

    def __init__(self, maxlen: int = 1000):
        super().__init__()
        self._buffer: deque = deque(maxlen=maxlen)

    def emit(self, record: logging.LogRecord):
        name = record.name
        if name.startswith("wn_mcp_world."):
            name = name[len("wn_mcp_world."):]
        elif name == "wn_mcp_world":
            name = "server"

        entry = {
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": name,
            "message": record.getMessage(),
        }
        self.acquire()
        try:
            self._buffer.append(entry)
        finally:
            self.release()

    def _filter_entries(
        self,
        snapshot: list,
        count: int,
        min_level: int,
        keyword: str,
    ) -> List[Dict[str, Any]]:
        """Filter snapshot entries by level and keyword, newest first."""
        result = []
        keyword_lower = keyword.lower() if keyword else ""
        for entry in reversed(snapshot):
            if len(result) >= count:
                break
            entry_level = logging.getLevelName(entry["level"])
            if isinstance(entry_level, int) and entry_level < min_level:
                continue
            if keyword_lower and keyword_lower not in entry["message"].lower():
                continue
            result.append(entry)
        return result

    def get_entries(
        self,
        count: int = 20,
        min_level: int = logging.INFO,
        keyword: str = "",
    ) -> List[Dict[str, Any]]:
        """Get filtered entries from buffer, newest first."""
        self.acquire()
        try:
            snapshot = list(self._buffer)
        finally:
            self.release()
        return self._filter_entries(snapshot, count, min_level, keyword)

    def get_entries_with_total(
        self,
        count: int = 20,
        min_level: int = logging.INFO,
        keyword: str = "",
    ) -> tuple:
        """Get filtered entries and total buffer count atomically."""
        self.acquire()
        try:
            snapshot = list(self._buffer)
            total = len(self._buffer)
        finally:
            self.release()
        return self._filter_entries(snapshot, count, min_level, keyword), total

    @property
    def total_count(self) -> int:
        return len(self._buffer)
