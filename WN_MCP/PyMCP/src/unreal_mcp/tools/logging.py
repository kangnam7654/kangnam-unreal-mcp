"""
Logging for Unreal MCP: settings.ini (LOG_LEVEL, retention, cleanup), file + stderr.
Exposes register_tools(mcp, get_connection) for set_log_level MCP tool.
"""
import configparser
import logging
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.logging")

# Base dir: PyMCP (parent of src/unreal_mcp/tools)
_BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
_SETTINGS_PATH = _BASE_DIR / "settings.ini"
_LOGS_DIR = _BASE_DIR / "logs"

_log_file = None
_logger = None
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
    """Get log level from settings.ini (ERROR, WARNING, INFO, DEBUG)."""
    config = _load_config()
    try:
        level_str = config.get("Logging", "LOG_LEVEL", fallback="INFO").strip().upper()
        level_map = {
            "ERROR": logging.ERROR,
            "WARNING": logging.WARNING,
            "INFO": logging.INFO,
            "DEBUG": logging.DEBUG,
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
        log_files: List[tuple] = []
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
        for filepath, filename, mtime in log_files:
            if datetime.fromtimestamp(mtime) < cutoff_date:
                try:
                    filepath.unlink()
                    deleted_count += 1
                    print(f"[INFO] Deleted old log (retention): {filename}", file=sys.stderr, flush=True)
                except OSError as e:
                    print(f"[WARNING] Failed to delete log {filename}: {e}", file=sys.stderr, flush=True)
        remaining = [(p, p.name, p.stat().st_mtime) for p in logs_dir.iterdir() if p.suffix == ".log"]
        remaining.sort(key=lambda x: x[2])
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


def initialize_logging() -> None:
    """Initialize logging: logs dir, file handler, stderr, level from settings.ini."""
    global _log_file, _logger, _file_handler
    try:
        _LOGS_DIR.mkdir(parents=True, exist_ok=True)
        max_log_files = _get_max_log_files()
        _cleanup_old_logs_with_limit(_LOGS_DIR, max(1, max_log_files - 1))
        log_filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S.log")
        log_filepath = _LOGS_DIR / log_filename
        _log_file = open(log_filepath, "a", encoding="utf-8")
        _log_file.write(f"\n{'='*80}\n")
        _log_file.write(f"MCP Server Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
        level_name = {logging.ERROR: "ERROR", logging.WARNING: "WARNING", logging.INFO: "INFO", logging.DEBUG: "DEBUG"}.get(
            _get_log_level(), "INFO"
        )
        _log_file.write(f"Log Level: {level_name} | Retention: {_get_log_retention_days()} days | Max Files: {_get_max_log_files()}\n")
        _log_file.write(f"{'='*80}\n")
        _log_file.flush()

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[],
        )
        _logger = logging.getLogger()
        log_level = _get_log_level()
        _logger.setLevel(log_level)
        for h in _logger.handlers[:]:
            _logger.removeHandler(h)

        _file_handler = logging.FileHandler(log_filepath, mode="a", encoding="utf-8")
        _file_handler.setLevel(log_level)
        _file_handler.setFormatter(
            logging.Formatter("%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        )

        class FastMCPFileFilter(logging.Filter):
            def filter(self, record):
                if _get_log_level() <= logging.DEBUG:
                    return True
                if record.name.startswith("mcp.") or record.name == "fastmcp":
                    return False
                return True

        _file_handler.addFilter(FastMCPFileFilter())
        _logger.addHandler(_file_handler)

        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(log_level)
        stderr_handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        _logger.addHandler(stderr_handler)

        for name in ("mcp.server.lowlevel.server", "fastmcp"):
            logging.getLogger(name).setLevel(logging.DEBUG)

        print(f"[INFO] Logging initialized: {log_filepath}", file=sys.stderr, flush=True)
        _log_file.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]} [INFO] Logging initialized: {log_filepath}\n")
        _log_file.flush()
    except Exception as e:
        print(f"[ERROR] Failed to initialize logging: {e}", file=sys.stderr, flush=True)


def close_logging() -> None:
    """Close log file and shutdown logging."""
    global _log_file, _logger, _file_handler
    if _log_file is not None:
        try:
            _log_file.write(f"\n{'='*80}\n")
            _log_file.write(f"MCP Server Stopped: {datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}\n")
            _log_file.write(f"{'='*80}\n")
            _log_file.close()
            _log_file = None
        except Exception as e:
            print(f"[ERROR] Failed to close log file: {e}", file=sys.stderr, flush=True)
    if _logger is not None:
        try:
            logging.shutdown()
        except Exception as e:
            print(f"[ERROR] Failed to shutdown logging: {e}", file=sys.stderr, flush=True)


def _log(level: int, message: str, write_to_file: bool = True) -> None:
    if level < _get_log_level():
        return
    level_names = {logging.DEBUG: "DEBUG", logging.INFO: "INFO", logging.WARNING: "WARNING", logging.ERROR: "ERROR"}
    level_name = level_names.get(level, "INFO")
    log_line = f"[{level_name}] {message}"
    print(log_line, file=sys.stderr, flush=True)
    if write_to_file and _log_file is not None:
        try:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            _log_file.write(f"{ts} {log_line}\n")
            _log_file.flush()
        except Exception as e:
            print(f"[ERROR] Failed to write to log file: {e}", file=sys.stderr, flush=True)


def log_info(message: str, write_to_file: bool = True) -> None:
    _log(logging.INFO, message, write_to_file)


def log_warning(message: str, write_to_file: bool = True) -> None:
    _log(logging.WARNING, message, write_to_file)


def log_error(message: str, write_to_file: bool = True) -> None:
    _log(logging.ERROR, message, write_to_file)


def log_debug(message: str, write_to_file: bool = False) -> None:
    _log(logging.DEBUG, message, write_to_file)


def set_log_level(level_str: str) -> bool:
    """Set log level and update settings.ini. Returns True on success."""
    global _logger, _file_handler
    level_str = level_str.strip().upper()
    level_map = {"ERROR": logging.ERROR, "WARNING": logging.WARNING, "INFO": logging.INFO, "DEBUG": logging.DEBUG}
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
        log_error(f"Failed to save log level to settings.ini: {e}", write_to_file=True)
        return False
    log_level = level_map[level_str]
    root = logging.getLogger()
    root.setLevel(log_level)
    if _logger is not None:
        _logger.setLevel(log_level)
    if _file_handler is not None:
        _file_handler.setLevel(log_level)
    for name in ("UnrealMCP.Tools.general", "UnrealMCP.Tools.agent", "UnrealMCP.Tools.logging", "UnrealMCP.Server", "UnrealMCP.Connection"):
        logging.getLogger(name).setLevel(log_level)
    return True


def get_available_log_levels() -> List[str]:
    return ["ERROR", "WARNING", "INFO", "DEBUG"]


def get_current_log_level() -> str:
    level_int = _get_log_level()
    level_names = {logging.ERROR: "ERROR", logging.WARNING: "WARNING", logging.INFO: "INFO", logging.DEBUG: "DEBUG"}
    return level_names.get(level_int, "INFO")


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    """Register log-related MCP tools (set_log_level)."""
    apply_log_level = set_log_level

    @mcp.tool()
    def set_log_level_tool(level: Optional[str] = None) -> Dict[str, Any]:
        """Get available log levels / current level, or set log level (saved to settings.ini).

        Call with no argument to see available levels and current level.
        Call with level=DEBUG|INFO|WARNING|ERROR to change level (persisted to settings.ini).
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
