"""Log management tools.

Tools: set_log_level, get_recent_logs
"""

import json
from fastmcp import FastMCP
from mcp_logging import set_level, get_level, get_recent_entries


def register_tools(mcp: FastMCP):
    """Register log management tools with the MCP server."""

    @mcp.tool
    def set_log_level(level: str) -> str:
        """Change the MCP server log level at runtime.

        Args:
            level: Log level - ERROR, WARNING, INFO, DEBUG, MISC.
                ERROR: Only errors.
                WARNING: Errors and warnings.
                INFO: General info (default).
                DEBUG: All messages.
                MISC: JSON request/response payloads (most verbose).

        Returns current log level after change.
        """
        new_level = set_level(level)
        return json.dumps({"log_level": new_level})

    @mcp.tool
    def get_recent_logs(
        count: int = 20,
        level: str = "INFO",
        keyword: str = "",
    ) -> str:
        """Get recent log entries from the MCP server.

        Reads from in-memory ring buffer (last 1000 entries).
        Useful for debugging - check what happened recently without opening log files.

        Args:
            count: Number of entries to return (default: 20, max: 200)
            level: Minimum log level filter (default: INFO)
            keyword: Optional text to filter log messages (case-insensitive)

        Returns filtered log entries, newest first.
        """
        result = get_recent_entries(
            count=count,
            level=level,
            keyword=keyword,
        )
        return json.dumps(result, indent=2, ensure_ascii=False)
