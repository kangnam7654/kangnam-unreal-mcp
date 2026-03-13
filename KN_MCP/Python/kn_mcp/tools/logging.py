"""
Logging for Unreal MCP: settings.ini (LOG_LEVEL, retention, cleanup), file + stderr.
Exposes register_tools(mcp, get_connection) for set_log_level MCP tool.
"""
import configparser
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.logging")

# Custom logging level for detailed diagnostics (below DEBUG=10)
MISC_LEVEL = 5
logging.addLevelName(MISC_LEVEL, "MISC")

# Base dir: Python (parent of kn_mcp/tools)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent
_SETTINGS_PATH = _BASE_DIR / "settings.ini"
_LOGS_DIR = _BASE_DIR / "logs"

_file_handler = None


def _load_config() -> configparser.ConfigParser:
    """Load configuration from settings.ini."""
    config = configparser.ConfigParser()
    if _SETTINGS_PATH.exists():
        config.read(_SETTINGS_PATH, encoding="utf-8")
    return config


def _get_log_retention_days() -> int:
    """Get log retention days from settings.ini."""
    config = _load_config()
    try:
        return int(config.get("Logging", "LOG_RETENTION_DAYS", fallback=7))
    except (ValueError, configparser.Error):
        return 7


def _is_auto_cleanup_enabled() -> bool:
    """Check if auto cleanup is enabled in settings.ini."""
    config = _load_config()
    try:
        value = config.get("Logging", "LOG_AUTO_CLEANUP", fallback="true").lower()
        return value == "true"
    except configparser.Error:
        return True


def _get_max_log_files() -> int:
    """Get maximum number of log files from settings.ini."""
    config = _load_config()
    try:
        return int(config.get("Logging", "MAX_LOG_FILES", fallback=2))
    except (ValueError, configparser.Error):
        return 2


def _get_log_level() -> int:
    """Get log level from settings.ini (ERROR, WARNING, INFO, DEBUG, MISC)."""
    config = _load_config()
    try:
        level_str = config.get("Logging", "LOG_LEVEL", fallback="INFO").strip().upper()
        level_map = {
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
            "MISC": MISC_LEVEL,
        }
        return level_map.get(level_str, logging.INFO)
    except (ValueError, configparser.Error):
        return logging.INFO


def _cleanup_old_logs_with_limit(logs_dir: Path, max_files_limit: int) -> None:
    """Delete old log files by retention and max count."""
    try:
        if not _is_auto_cleanup_enabled():
            return
        retention_days = _get_log_retention_days()
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        log_files: list[tuple] = []
        for p in logs_dir.iterdir():
            if p.suffix != ".log":
                continue
            try:
                mtime = p.stat().st_mtime
                log_files.append((p, p.name, mtime))
            except OSError:
                pass
        log_files.sort(key=lambda x: x[2])
        deleted_count = 0
        deleted_paths: set = set()
        for filepath, filename, mtime in log_files:
            if datetime.fromtimestamp(mtime) < cutoff_date:
                try:
                    filepath.unlink()
                    deleted_count += 1
                    deleted_paths.add(filepath)
                    print(f"[INFO] Deleted old log (retention): {filename}", file=sys.stderr, flush=True)
                except OSError as e:
                    print(f"[WARNING] Failed to delete log {filename}: {e}", file=sys.stderr, flush=True)
        remaining = [(p, n, m) for p, n, m in log_files if p not in deleted_paths]
        if max_files_limit > 0 and len(remaining) > max_files_limit:
            for filepath, filename, _ in remaining[: len(remaining) - max_files_limit]:
                try:
                    filepath.unlink()
                    deleted_count += 1
                    print(f"[INFO] Deleted old log (max count): {filename}", file=sys.stderr, flush=True)
                except OSError as e:
                    print(f"[WARNING] Failed to delete log {filename}: {e}", file=sys.stderr, flush=True)
        if deleted_count > 0:
            print(f"[INFO] Cleaned up {deleted_count} old log file(s)", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[ERROR] Error during log cleanup: {e}", file=sys.stderr, flush=True)


def _log(level: int, message: str) -> None:
    if level < _get_log_level():
        return
    level_names = {MISC_LEVEL: "MISC", logging.DEBUG: "DEBUG", logging.INFO: "INFO", logging.WARNING: "WARNING", logging.ERROR: "ERROR"}
    level_name = level_names.get(level, "INFO")
    log_line = f"[{level_name}] {message}"
    print(log_line, file=sys.stderr, flush=True)


def log_info(message: str) -> None:
    _log(logging.INFO, message)


def log_warning(message: str) -> None:
    _log(logging.WARNING, message)


def log_error(message: str) -> None:
    _log(logging.ERROR, message)


def log_debug(message: str) -> None:
    _log(logging.DEBUG, message)


def log_misc(message: str) -> None:
    _log(MISC_LEVEL, message)


def set_log_level(level_str: str) -> bool:
    """Set log level and update settings.ini. Returns True on success."""
    global _file_handler
    level_str = level_str.strip().upper()
    level_map = {"ERROR": logging.ERROR, "WARNING": logging.WARNING, "INFO": logging.INFO, "DEBUG": logging.DEBUG, "MISC": MISC_LEVEL}
    if level_str not in level_map:
        return False
    config = _load_config()
    if "Logging" not in config:
        config.add_section("Logging")
    config.set("Logging", "LOG_LEVEL", level_str)
    try:
        _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(_SETTINGS_PATH, "w", encoding="utf-8") as f:
            config.write(f)
    except Exception as e:
        log_error(f"Failed to save log level to settings.ini: {e}")
        return False
    log_level = level_map[level_str]
    root = logging.getLogger()
    root.setLevel(log_level)
    if _file_handler is not None:
        _file_handler.setLevel(log_level)
    for name in ("UnrealMCP.Tools.general", "UnrealMCP.Tools.agent", "UnrealMCP.Tools.logging", "UnrealMCP.Server", "UnrealMCP.Connection"):
        logging.getLogger(name).setLevel(log_level)
    return True


def get_available_log_levels() -> list[str]:
    return ["ERROR", "WARNING", "INFO", "DEBUG", "MISC"]


def get_current_log_level() -> str:
    level_int = _get_log_level()
    level_names = {logging.ERROR: "ERROR", logging.WARNING: "WARNING", logging.INFO: "INFO", logging.DEBUG: "DEBUG", MISC_LEVEL: "MISC"}
    return level_names.get(level_int, "INFO")


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    """Register log-related MCP tools (set_log_level)."""
    apply_log_level = set_log_level

    @mcp.tool()
    def set_log_level_tool(level: str | None = None) -> dict[str, Any]:
        """Get available log levels / current level, or set log level (saved to settings.ini).

        Call with no argument to see available levels and current level.
        Call with level=MISC|DEBUG|INFO|WARNING|ERROR to change level (persisted to settings.ini).
        """
        levels = get_available_log_levels()
        if level is None:
            current = get_current_log_level()
            return {
                "success": True,
                "available_levels": levels,
                "current_level": current,
                "message": f"Available: {', '.join(levels)}. Current: {current}. Set 'level' to change (saved to settings.ini).",
            }
        level_upper = level.strip().upper()
        if level_upper not in levels:
            return {
                "success": False,
                "error": f"Invalid level '{level}'. Use one of: {', '.join(levels)}",
            }
        if apply_log_level(level_upper):
            return {
                "success": True,
                "new_level": level_upper,
                "message": f"✅ Log level set to {level_upper} (saved to settings.ini)",
            }
        return {
            "success": False,
            "error": "Failed to save log level to settings.ini",
        }

    logger.info("Logging tools registered")
