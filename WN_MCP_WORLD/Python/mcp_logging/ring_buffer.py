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

        self._buffer.append({
            "timestamp": datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S"),
            "level": record.levelname,
            "logger": name,
            "message": record.getMessage(),
        })

    def get_entries(
        self,
        count: int = 20,
        min_level: int = logging.INFO,
        keyword: str = "",
    ) -> List[Dict[str, Any]]:
        """Get filtered entries from buffer, newest first."""
        result = []
        keyword_lower = keyword.lower() if keyword else ""
        for entry in reversed(self._buffer):
            if len(result) >= count:
                break
            entry_level = logging.getLevelName(entry["level"])
            if isinstance(entry_level, int) and entry_level < min_level:
                continue
            if keyword_lower and keyword_lower not in entry["message"].lower():
                continue
            result.append(entry)
        return result

    @property
    def total_count(self) -> int:
        return len(self._buffer)
