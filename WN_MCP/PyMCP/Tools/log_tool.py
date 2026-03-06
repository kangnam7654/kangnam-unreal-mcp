"""
Logging Tool for MCP
Centralized logging utility for MCP server and tools
All logging to stderr and log file, including FastMCP logs
"""

import sys
import os
import logging
import configparser
from datetime import datetime, timedelta
from typing import Optional


# Custom logging level for detailed diagnostics
MISC_LEVEL = 5
logging.addLevelName(MISC_LEVEL, 'MISC')


# Global log file handle
_log_file = None
_logger = None
_file_handler = None


def _load_config():
    """Load configuration from settings.ini."""
    config = configparser.ConfigParser()
    
    # Try to load settings.ini from project root
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.ini')
    
    if os.path.exists(settings_path):
        config.read(settings_path)
    
    return config


def _get_log_retention_days() -> int:
    """Get log retention days from settings.ini."""
    config = _load_config()
    
    try:
        return int(config.get('Logging', 'LOG_RETENTION_DAYS', fallback=7))
    except (ValueError, configparser.Error):
        return 7


def _is_auto_cleanup_enabled() -> bool:
    """Check if auto cleanup is enabled in settings.ini."""
    config = _load_config()
    
    try:
        value = config.get('Logging', 'LOG_AUTO_CLEANUP', fallback='true').lower()
        return value == 'true'
    except configparser.Error:
        return True


def _get_max_log_files() -> int:
    """Get maximum number of log files from settings.ini."""
    config = _load_config()
    
    try:
        return int(config.get('Logging', 'MAX_LOG_FILES', fallback=2))
    except (ValueError, configparser.Error):
        return 2


def _get_log_level() -> int:
    """Get log level from settings.ini (ERROR, WARNING, INFO, DEBUG)."""
    config = _load_config()
    
    try:
        level_str = config.get('Logging', 'LOG_LEVEL', fallback='INFO').strip().upper()
        level_map = {
            'ERROR': logging.ERROR,      # 40
            'WARNING': logging.WARNING,  # 30
            'INFO': logging.INFO,        # 20
            'DEBUG': logging.DEBUG,      # 10
            'MISC': MISC_LEVEL           # 5
        }
        return level_map.get(level_str, logging.INFO)
    except (ValueError, configparser.Error):
        return logging.INFO


def _cleanup_old_logs(logs_dir: str) -> None:
    """Delete log files older than retention period and enforce max file count.
    
    Args:
        logs_dir: Path to logs directory
    """
    max_log_files = _get_max_log_files()
    _cleanup_old_logs_with_limit(logs_dir, max_log_files)


def _cleanup_old_logs_with_limit(logs_dir: str, max_files_limit: int) -> None:
    """Delete log files older than retention period and enforce custom file count limit.
    
    Args:
        logs_dir: Path to logs directory
        max_files_limit: Maximum number of log files to keep (overrides config)
    """
    try:
        if not _is_auto_cleanup_enabled():
            return
        
        retention_days = _get_log_retention_days()
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        
        # Get all log files with their modification times
        log_files = []
        for filename in os.listdir(logs_dir):
            if not filename.endswith('.log'):
                continue
            
            filepath = os.path.join(logs_dir, filename)
            try:
                mtime = os.path.getmtime(filepath)
                log_files.append((filepath, filename, mtime))
            except Exception:
                pass
        
        # Sort by modification time (oldest first)
        log_files.sort(key=lambda x: x[2])
        
        deleted_count = 0
        
        # First pass: Delete files older than retention period
        for filepath, filename, mtime in log_files:
            file_date = datetime.fromtimestamp(mtime)
            if file_date < cutoff_date:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    print(f'[INFO] Deleted old log (retention): {filename}', file=sys.stderr, flush=True)
                except Exception as e:
                    print(f'[WARNING] Failed to delete log {filename}: {e}', file=sys.stderr, flush=True)
        
        # Second pass: If still more than max files, delete oldest ones
        remaining_files = []
        for filename in os.listdir(logs_dir):
            if filename.endswith('.log'):
                filepath = os.path.join(logs_dir, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                    remaining_files.append((filepath, filename, mtime))
                except Exception:
                    pass
        
        # Sort by modification time (oldest first)
        remaining_files.sort(key=lambda x: x[2])
        
        # Delete excess files (only if max_files_limit > 0)
        if max_files_limit > 0 and len(remaining_files) > max_files_limit:
            files_to_delete = len(remaining_files) - max_files_limit
            for filepath, filename, _ in remaining_files[:files_to_delete]:
                try:
                    os.remove(filepath)
                    deleted_count += 1
                    print(f'[INFO] Deleted old log (max count): {filename}', file=sys.stderr, flush=True)
                except Exception as e:
                    print(f'[WARNING] Failed to delete log {filename}: {e}', file=sys.stderr, flush=True)
        
        if deleted_count > 0:
            print(f'[INFO] Cleaned up {deleted_count} old log file(s)', file=sys.stderr, flush=True)
    
    except Exception as e:
        print(f'[ERROR] Error during log cleanup: {e}', file=sys.stderr, flush=True)


def initialize_logging():
    """Initialize logging system and create log file."""
    global _log_file, _logger, _file_handler
    
    try:
        # Create logs directory if it doesn't exist
        logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        # First cleanup with max_log_files - 1 to make room for new log file
        # This ensures max_log_files count is respected after new file creation
        max_log_files = _get_max_log_files()
        _cleanup_old_logs_with_limit(logs_dir, max(1, max_log_files - 1))
        
        # Create log file with datetime format
        log_filename = datetime.now().strftime('%Y-%m-%d_%H-%M-%S.log')
        log_filepath = os.path.join(logs_dir, log_filename)
        
        # Open log file in append mode
        _log_file = open(log_filepath, 'a', encoding='utf-8')
        _log_file.write(f'\n{"="*80}\n')
        _log_file.write(f'MCP Server Started: {datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}\n')
        
        # Get log level name
        log_level_name = {logging.ERROR: 'ERROR', logging.WARNING: 'WARNING', logging.INFO: 'INFO', logging.DEBUG: 'DEBUG'}.get(_get_log_level(), 'INFO')
        _log_file.write(f'Log Level: {log_level_name} | Retention: {_get_log_retention_days()} days | Max Files: {_get_max_log_files()}\n')
        _log_file.write(f'{"="*80}\n')
        _log_file.flush()
        
        # Configure Python logging to capture all logs including FastMCP
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S',
            handlers=[]  # We'll add handlers manually
        )
        
        # Get root logger and set level from config
        _logger = logging.getLogger()
        log_level = _get_log_level()
        _logger.setLevel(log_level)
        
        # Remove existing handlers
        for handler in _logger.handlers[:]:
            _logger.removeHandler(handler)
        
        # Create file handler for logging to file
        _file_handler = logging.FileHandler(log_filepath, mode='a', encoding='utf-8')
        _file_handler.setLevel(log_level)
        file_formatter = logging.Formatter(
            '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        _file_handler.setFormatter(file_formatter)
        
        # Add filter to conditionally exclude FastMCP logs from file handler
        # - If log_level = DEBUG: FastMCP logs appear in both stderr and file
        # - If log_level >= INFO: FastMCP logs appear in stderr only (excluded from file)
        class FastMCPFileFilter(logging.Filter):
            def filter(self, record):
                # If log_level is DEBUG, allow everything including FastMCP logs
                if _get_log_level() <= logging.DEBUG:
                    return True
                
                # Otherwise, exclude FastMCP logs from file output
                if record.name.startswith('mcp.') or record.name == 'fastmcp':
                    return False
                return True
        
        _file_handler.addFilter(FastMCPFileFilter())
        _logger.addHandler(_file_handler)
        
        # Create stderr handler for console output (debug mode)
        stderr_handler = logging.StreamHandler(sys.stderr)
        stderr_handler.setLevel(log_level)
        stderr_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        stderr_handler.setFormatter(stderr_formatter)
        _logger.addHandler(stderr_handler)
        
        # Configure FastMCP loggers as DEBUG level
        # When log_level = INFO:
        #   - FastMCP logs won't appear (DEBUG < INFO)
        #   - When needed, set log_level = DEBUG to see FastMCP logs in debug console
        # FastMCP logs never appear in file (excluded by filter above)
        mcp_logger = logging.getLogger('mcp.server.lowlevel.server')
        mcp_logger.setLevel(logging.DEBUG)
        
        fastmcp_logger = logging.getLogger('fastmcp')
        fastmcp_logger.setLevel(logging.DEBUG)
        
        # Log initialization
        print(f'[INFO] Logging initialized: {log_filepath}', file=sys.stderr, flush=True)
        _log_file.write(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} [INFO] Logging initialized: {log_filepath}\n')
        _log_file.flush()
        
    except Exception as e:
        print(f'[ERROR] Failed to initialize logging: {e}', file=sys.stderr, flush=True)


def _log(level: int, message: str, write_to_file: bool = True):
    """Log a message at the specified level.
    
    Args:
        level: Log level (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
        message: Message to log
        write_to_file: Whether to write this message to file (default: True)
                      
    Filtering logic:
        1. First, log_level (config) filters whether the log appears at all
           - If level < configured log_level, the log is not shown anywhere
        2. If log passes log_level filter, write_to_file parameter controls file output
           - write_to_file=True: log appears in both stderr and file
           - write_to_file=False: log appears in stderr only
                      
    Examples (assuming log_level = INFO):
        - log_error("msg", False) → stderr ✓, file ✗
        - log_error("msg", True) → stderr ✓, file ✓
        - log_debug("msg", True) → stderr ✗, file ✗ (filtered by log_level)
        - log_debug("msg", False) → stderr ✗, file ✗ (filtered by log_level)
    """
    global _log_file
    
    # First pass: Check if this log level should appear at all
    if level < _get_log_level():
        return  # This log is filtered by configured log level
    
    # Map level to name
    level_names = {
        MISC_LEVEL: 'MISC',
        logging.DEBUG: 'DEBUG',
        logging.INFO: 'INFO',
        logging.WARNING: 'WARNING',
        logging.ERROR: 'ERROR'
    }
    level_name = level_names.get(level, 'INFO')
    log_line = f'[{level_name}] {message}'
    
    # Second pass: Log passed log_level filter, so print to stderr
    print(log_line, file=sys.stderr, flush=True)
    
    # Third pass: Check write_to_file flag for file output
    # (log_level filtering is already done above)
    if write_to_file and _log_file is not None:
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            _log_file.write(f'{timestamp} {log_line}\n')
            _log_file.flush()
        except Exception as e:
            print(f'[ERROR] Failed to write to log file: {e}', file=sys.stderr, flush=True)


def log_info(message: str, write_to_file: bool = True):
    """Log an info message to stderr and optionally to file.
    
    Args:
        message: Message to log
        write_to_file: Whether to write to file (default: True)
    """
    _log(logging.INFO, message, write_to_file)


def log_warning(message: str, write_to_file: bool = True):
    """Log a warning message to stderr and optionally to file.
    
    Args:
        message: Message to log
        write_to_file: Whether to write to file (default: True)
    """
    _log(logging.WARNING, message, write_to_file)


def log_error(message: str, write_to_file: bool = True):
    """Log an error message to stderr and optionally to file.
    
    Args:
        message: Message to log
        write_to_file: Whether to write to file (default: True)
    """
    _log(logging.ERROR, message, write_to_file)


def log_debug(message: str, write_to_file: bool = False):
    """Log a debug message to stderr and optionally to file.
    
    Args:
        message: Message to log
        write_to_file: Whether to write to file (default: False, debugging only)
    """
    _log(logging.DEBUG, message, write_to_file)


def log_misc(message: str, write_to_file: bool = True):
    """Log a miscellaneous message at MISC level (5) to stderr and optionally to file.
    
    Used for detailed logging of JSON objects, detailed diagnostics, etc.
    
    Args:
        message: Message to log
        write_to_file: Whether to write to file (default: True)
    """
    _log(MISC_LEVEL, message, write_to_file)


def close_logging():
    """Close log file and shutdown logging."""
    global _log_file, _logger, _file_handler
    
    if _log_file is not None:
        try:
            _log_file.write(f'\n{"="*80}\n')
            _log_file.write(f'MCP Server Stopped: {datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]}\n')
            _log_file.write(f'{"="*80}\n')
            _log_file.close()
            _log_file = None
        except Exception as e:
            print(f'[ERROR] Failed to close log file: {e}', file=sys.stderr, flush=True)
    
    # Shutdown logging handlers
    if _logger is not None:
        try:
            logging.shutdown()
        except Exception as e:
            print(f'[ERROR] Failed to shutdown logging: {e}', file=sys.stderr, flush=True)


def set_log_level(level_str: str) -> bool:
    """Set log level dynamically and update settings.ini.
    
    Args:
        level_str: Log level name (ERROR, WARNING, INFO, DEBUG, MISC)
    
    Returns:
        True if successfully set, False if invalid level
    """
    global _logger, _file_handler
    
    level_str = level_str.strip().upper()
    level_map = {
        'ERROR': logging.ERROR,      # 40
        'WARNING': logging.WARNING,  # 30
        'INFO': logging.INFO,        # 20
        'DEBUG': logging.DEBUG,      # 10
        'MISC': MISC_LEVEL           # 5
    }
    
    if level_str not in level_map:
        return False
    
    # Update settings.ini
    config = _load_config()
    if 'Logging' not in config:
        config.add_section('Logging')
    
    config.set('Logging', 'LOG_LEVEL', level_str)
    
    # Write back to settings.ini
    settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.ini')
    try:
        with open(settings_path, 'w') as f:
            config.write(f)
    except Exception as e:
        log_error(f'Failed to save log level to settings.ini: {e}', write_to_file=True)
        return False
    
    # Update logger and handlers if they exist
    log_level = level_map[level_str]
    if _logger is not None:
        _logger.setLevel(log_level)
    
    if _file_handler is not None:
        _file_handler.setLevel(log_level)
    
    return True


def get_available_log_levels() -> list:
    """Get list of available log levels.
    
    Returns:
        List of available log level names
    """
    return ['ERROR', 'WARNING', 'INFO', 'DEBUG', 'MISC']


def get_current_log_level() -> str:
    """Get current log level name.
    
    Returns:
        Current log level name (ERROR, WARNING, INFO, DEBUG)
    """
    level_int = _get_log_level()
    level_names = {
        logging.ERROR: 'ERROR',
        logging.WARNING: 'WARNING',
        logging.INFO: 'INFO',
        logging.DEBUG: 'DEBUG',
        MISC_LEVEL: 'MISC'
    }
    return level_names.get(level_int, 'INFO')


__all__ = ['initialize_logging', 'close_logging', 'log_info', 'log_warning', 'log_error', 'log_debug', 'log_misc', 'set_log_level', 'get_available_log_levels', 'get_current_log_level']
