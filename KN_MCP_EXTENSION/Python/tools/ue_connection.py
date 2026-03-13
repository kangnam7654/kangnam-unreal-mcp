"""UE TCP connection accessor for KN_MCP_EXTENSION tools.

Thin wrapper around kn_mcp.connection.UnrealConnection.send_command().
No error translation — returns raw response dict for tools to handle directly.
"""

import logging
from typing import Any

from kn_mcp.connection import get_unreal_connection

logger = logging.getLogger("kn_mcp_extension.ue_connection")


def send_command(command_name: str, params: dict[str, Any] | None = None, *, category_name: str = "") -> dict[str, Any]:
    """Send command to UE via shared connection.

    Args:
        command_name: C++ command name (e.g. "get_actors_in_level")
        params: Optional command parameters
        category_name: Category prefix matching C++ GetName() (e.g. "Actor", "Blueprint")

    Returns:
        Raw response dict from UE (success result or error dict with "status": "error")
    """
    conn = get_unreal_connection()
    if conn is None:
        return {"status": "error", "error": "Not connected to UE (no KN_MCP connection available)"}

    full_name = f"{category_name}_{command_name}" if category_name else command_name
    logger.info(">> %s", full_name)

    result = conn.send_command(full_name, params or {})
    if result is None:
        return {"status": "error", "error": "No response from UE"}

    return result
