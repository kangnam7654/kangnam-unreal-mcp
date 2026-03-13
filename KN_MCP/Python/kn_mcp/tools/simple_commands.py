"""
SimpleCommand auto-registration: fetch bIsSimple commands from UE and register as @mcp.tool().

C++ side registers commands with KN_MCP_REGISTER_SIMPLE_COMMAND (bIsSimple=true).
This module queries UE for the list and dynamically creates MCP tools for each one.
"""
import json
import logging
from typing import Any

from kn_mcp.connection import get_unreal_connection

logger = logging.getLogger("UnrealMCP.SimpleCommands")


def get_simple_commands() -> list[dict[str, str]]:
    """Query UE for SimpleCommand list via Application_get_simple_commands.

    Returns list of {"name": "...", "description": "..."} dicts, or empty list on error.
    """
    conn = get_unreal_connection()
    if not conn:
        logger.warning("No Unreal connection available for get_simple_commands")
        return []
    resp = conn.send_command("Application_get_simple_commands", {})
    if not resp or resp.get("status") == "error":
        logger.warning(
            "get_simple_commands failed: %s",
            resp.get("error", "no response") if resp else "no connection",
        )
        return []
    commands = resp.get("commands")
    if not isinstance(commands, list):
        logger.warning("get_simple_commands returned unexpected format: %s", type(commands))
        return []
    logger.info("Got %d simple command(s) from UE", len(commands))
    return commands


def _make_simple_tool(cmd_name: str, cmd_desc: str):
    """Create a tool function that forwards to UE via send_command."""
    def tool_fn() -> str:
        conn = get_unreal_connection()
        if conn is None:
            return json.dumps({"status": "error", "error": "Not connected to UE"})
        result = conn.send_command(cmd_name, {})
        if result is None:
            return json.dumps({"status": "error", "error": "No response from UE"})
        return json.dumps(result, indent=2, ensure_ascii=False)

    tool_fn.__name__ = cmd_name
    tool_fn.__doc__ = cmd_desc
    return tool_fn


def register_simple_commands(server: Any) -> None:
    """Fetch SimpleCommand list from UE and register each as @mcp.tool().

    Args:
        server: FastMCP server instance to register tools with.
    """
    commands = get_simple_commands()
    if not commands:
        logger.info("No simple commands from UE, skipping registration")
        return

    registered = 0
    for cmd in commands:
        name = cmd.get("name", "")
        desc = cmd.get("description", "")
        if not name:
            continue
        try:
            tool_fn = _make_simple_tool(name, desc)
            server.tool(tool_fn)
            registered += 1
            logger.info("Registered simple command as tool: %s", name)
        except Exception as e:
            logger.warning("Failed to register simple command %s: %s", name, e)

    if registered > 0:
        logger.info("Registered %d simple command(s) as MCP tools", registered)
