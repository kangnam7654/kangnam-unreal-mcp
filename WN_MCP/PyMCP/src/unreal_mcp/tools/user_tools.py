"""
User tool directories: fetch from UE and register @mcp.tool functions with the MCP server.
Called when the Unreal connection is established (e.g. in server lifespan).
Command naming must match C++ (WN_MCP_CommandGroup_Application):
  - Method name uses Application_ prefix, e.g. Application_get_user_tool_directories.
"""
import importlib.util
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

import logging

from unreal_mcp.connection import get_unreal_connection

logger = logging.getLogger("UnrealMCP.UserTools")

# Project root: PyMCP (this file is src/unreal_mcp/tools/user_tools.py)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# UE command name: must match C++ Application group (Application_get_user_tool_directories)
UE_CMD_GET_USER_TOOL_DIRECTORIES = "Application_get_user_tool_directories"


def _dir_name_to_prefix(dir_name: str) -> str:
    """Use first path segment as prefix (e.g. 'MyGame/Content/Scripts' -> 'mygame')."""
    if not dir_name or not dir_name.strip():
        return "user"
    first = dir_name.strip().split("/")[0].split("\\")[0].strip()
    return first.lower() or "user"


def get_user_tool_directories() -> List[str]:
    """
    Ask Unreal Engine for the list of tool directories (via get_user_tool_directories command).
    Returns a list of directory path strings, or empty list on error.
    """
    conn = get_unreal_connection()
    if not conn:
        logger.warning("No Unreal connection available for get_user_tool_directories")
        return []
    resp = conn.send_command(UE_CMD_GET_USER_TOOL_DIRECTORIES, {})
    if not resp or resp.get("status") == "error":
        logger.warning(
            "%s command failed: %s",
            UE_CMD_GET_USER_TOOL_DIRECTORIES,
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
    # Ensure project Tools package is on path so user modules can import from Tools if needed
    tools_dir = project_root / "Tools"
    if tools_dir.exists() and str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    registered_count = 0
    tool_pattern = re.compile(r"@mcp\.tool\s+def\s+(\w+)\s*\(")

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
            has_simple_commands = "def register_simple_commands" in content
            if not matches and not has_simple_commands:
                continue

            try:
                spec = importlib.util.spec_from_file_location(py_file.stem, str(py_file))
                if not spec or not spec.loader:
                    continue
                module = importlib.util.module_from_spec(spec)
                sys.modules[py_file.stem] = module
                module.__package__ = getattr(module, "__package__", None) or "Tools"
                setattr(module, "mcp", server)

                try:
                    spec.loader.exec_module(module)
                except Exception as e:
                    logger.warning("Error loading module %s: %s", py_file.name, e)
                    sys.modules.pop(py_file.stem, None)
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

                if has_simple_commands and hasattr(module, "register_simple_commands"):
                    n = _register_simple_commands(server, module, py_file.stem, prefix)
                    registered_count += n

            except Exception as e:
                logger.warning("Error processing %s: %s", py_file, e, exc_info=True)

    if registered_count > 0:
        logger.info("Registered %d user tool(s) from UE directories", registered_count)


def _register_simple_commands(server: Any, module: Any, module_name: str, prefix: str) -> int:
    """Register tools from module.register_simple_commands() return value. Returns count registered."""
    count = 0
    try:
        register_fn = getattr(module, "register_simple_commands")
        if not callable(register_fn):
            return 0
        commands = register_fn()
        if not isinstance(commands, list) or not commands:
            return 0
        conn = get_unreal_connection()
        if not conn:
            logger.warning("No connection for simple commands from %s", module_name)
            return 0
        for cmd_info in commands:
            try:
                if isinstance(cmd_info, dict):
                    cmd_name = cmd_info.get("name", "")
                    cmd_desc = cmd_info.get("description", "Execute command from user tool")
                else:
                    cmd_name = str(cmd_info)
                    cmd_desc = f"Execute {cmd_name} command"
                if not cmd_name:
                    continue

                prefixed_cmd = f"{prefix}_{cmd_name}"

                def _make_wrapper(c: str, name: str, desc: str):
                    def _run(options: Optional[dict] = None):
                        r = conn.send_command(c, options or {})
                        return r if isinstance(r, dict) else {"result": r, "status": "ok"}

                    _run.__name__ = name
                    _run.__doc__ = desc
                    return server.tool(_run)

                _make_wrapper(cmd_name, prefixed_cmd, cmd_desc)
                count += 1
                logger.info("Registered simple command: %s", prefixed_cmd)
            except Exception as e:
                logger.warning("Error registering simple command %s: %s", cmd_info, e)
    except Exception as e:
        logger.warning("Error processing register_simple_commands in %s: %s", module_name, e)
    return count
