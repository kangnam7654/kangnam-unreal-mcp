"""
User tool directories: fetch from UE and register @mcp.tool functions with the MCP server.
Called when the Unreal connection is established (e.g. in server lifespan).
"""
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

import logging

from kn_mcp.connection import get_unreal_connection

logger = logging.getLogger("UnrealMCP.UserTools")

# Project root: Python (this file is kn_mcp/tools/user_tools.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _dir_name_to_prefix(dir_name: str) -> str:
    """Use first path segment as prefix (e.g. 'MyGame/Content/Scripts' -> 'mygame')."""
    if not dir_name or not dir_name.strip():
        return "user"
    first = dir_name.strip().split("/")[0].split("\\")[0].strip()
    return first.lower() or "user"


def get_user_tool_directories() -> list[str]:
    """
    Ask Unreal Engine for the list of tool directories (via get_user_tool_directories command).
    Returns a list of directory path strings, or empty list on error.
    """
    conn = get_unreal_connection()
    if not conn:
        logger.warning("No Unreal connection available for get_user_tool_directories")
        return []
    resp = conn.send_command("Application_get_user_tool_directories", {})
    if not resp or resp.get("status") == "error":
        logger.warning(
            "get_user_tool_directories failed: %s",
            resp.get("error", "no response") if resp else "no connection",
        )
        return []
    directories = resp.get("directories") if isinstance(resp.get("directories"), list) else []
    logger.info("Got %d user tool directory/directories from UE: %s", len(directories), directories)
    return directories


def register_user_tool_directories(server: Any) -> None:
    """
    Discover and register @mcp.tool functions from user tool directories reported by UE.
    Call this when the Unreal connection is established (e.g. in server lifespan).

    Args:
        server: FastMCP server instance to register tools with.
    """
    directories = get_user_tool_directories()
    if not directories:
        logger.info("No user tool directories from UE, skipping registration")
        return

    project_root = _PROJECT_ROOT

    registered_count = 0
    tool_pattern = re.compile(r"@mcp\.tool\(\)[^\n]*\n\s*(?:async\s+)?def\s+(\w+)\s*\(")

    for dir_name in directories:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            logger.warning("User tool directory not found: %s", dir_path)
            continue
        if str(dir_path) not in sys.path:
            sys.path.insert(0, str(dir_path))

        prefix = _dir_name_to_prefix(dir_name)
        logger.info("Scanning user tool directory: %s (prefix: %s)", dir_name, prefix)
        for py_file in dir_path.glob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("Could not read %s: %s", py_file, e)
                continue

            matches = tool_pattern.findall(content)
            if not matches:
                continue

            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, str(py_file))
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                module_key = f"kn_mcp.user_tools.{prefix}.{py_file.stem}"
                module.__name__ = module_key
                sys.modules[module_key] = module
                module.__package__ = getattr(module, "__package__", None) or "user_tools"
                setattr(module, "mcp", server)

                try:
                    spec.loader.exec_module(module)
                except Exception as e:
                    logger.warning("Error loading module %s: %s", py_file.name, e)
                    sys.modules.pop(module_key, None)
                    continue

                for func_name in matches:
                    if hasattr(module, func_name):
                        func = getattr(module, func_name)
                        prefixed_name = f"{prefix}_{func_name}"

                        def _wrap(fn: Any, name: str):
                            def _wrapped(*args: Any, **kwargs: Any) -> Any:
                                return fn(*args, **kwargs)

                            _wrapped.__name__ = name
                            _wrapped.__doc__ = getattr(fn, "__doc__", None) or f"User tool from {dir_name}."
                            return _wrapped

                        server.tool(_wrap(func, prefixed_name))
                        registered_count += 1
                        logger.info("Registered user tool: %s (from %s in %s)", prefixed_name, py_file.name, dir_name)

            except Exception as e:
                logger.warning("Error processing %s: %s", py_file, e, exc_info=True)

    if registered_count > 0:
        logger.info("Registered %d user tool(s) from UE directories", registered_count)


