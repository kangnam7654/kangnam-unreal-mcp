"""UE TCP connection utilities.

Provides execute() for sending JSON-RPC 2.0 commands to UE C++ plugin.
"""

import json
import logging
import socket
import threading
from typing import Optional, Dict, Any

from mcp_logging.config import MISC

logger = logging.getLogger("wn_mcp_world.ue_connection")


# =============================================================================
# Configuration
# =============================================================================

UE_HOST = "127.0.0.1"
UE_PORT = 27777
UE_TIMEOUT = 30.0
MAX_RESPONSE_SIZE = 100 * 1024 * 1024  # 100 MB

_socket: Optional[socket.socket] = None
_lock = threading.Lock()


# =============================================================================
# Connection Management
# =============================================================================


def connect() -> bool:
    """Connect to UE TCP server if not already connected."""
    global _socket
    with _lock:
        if _socket is not None:
            return True
        try:
            _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _socket.settimeout(UE_TIMEOUT)
            _socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            _socket.connect((UE_HOST, UE_PORT))
            logger.info("Connected to UE at %s:%d", UE_HOST, UE_PORT)
            return True
        except Exception as e:
            _socket = None
            logger.error("Cannot connect to UE at %s:%d - %s", UE_HOST, UE_PORT, e)
            raise ConnectionError(f"Cannot connect to UE at {UE_HOST}:{UE_PORT} - {e}")


def disconnect():
    """Disconnect from UE TCP server."""
    global _socket
    with _lock:
        if _socket:
            try:
                _socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            _socket.close()
            _socket = None
            logger.info("Disconnected from UE")


def execute(command_name: str, params: Optional[Dict[str, Any]] = None, app_name: str = "") -> Dict[str, Any]:
    """Send JSON-RPC 2.0 command to UE and return result.

    Args:
        command_name: C++ command name (e.g. "get_actors_in_level")
        params: Optional command parameters
        app_name: Application name prefix (e.g. "WN_MCP_WORLD")

    Returns:
        Result dict from UE response

    Raises:
        ConnectionError: Cannot connect or communication failed
        RuntimeError: UE returned an error response
    """
    connect()

    if _socket is None:
        raise ConnectionError("Not connected to UE")

    full_name = f"{app_name}_{command_name}" if app_name else command_name
    request = {
        "jsonrpc": "2.0",
        "method": "command",
        "id": full_name,
        "params": params if params is not None else {}
    }

    logger.info(">> %s", full_name)
    logger.log(MISC, ">> %s", json.dumps(request, ensure_ascii=False))

    try:
        # Flush any leftover data in receive buffer before sending
        _socket.setblocking(False)
        try:
            while _socket.recv(65536):
                pass
        except (BlockingIOError, OSError):
            pass
        _socket.setblocking(True)
        _socket.settimeout(UE_TIMEOUT)

        _socket.send(json.dumps(request).encode("utf-8"))

        # Read until we have a complete JSON response
        chunks = []
        total_size = 0
        while True:
            chunk = _socket.recv(65536)
            if not chunk:
                disconnect()
                raise ConnectionError("UE closed connection")
            chunks.append(chunk)
            total_size += len(chunk)
            if total_size > MAX_RESPONSE_SIZE:
                disconnect()
                raise ConnectionError(f"Response exceeded {MAX_RESPONSE_SIZE} bytes limit")
            try:
                response = json.loads(b"".join(chunks).decode("utf-8"))
                break
            except json.JSONDecodeError:
                continue

        logger.log(MISC, "<< %s", json.dumps(response, ensure_ascii=False))

        if "error" in response:
            error = response["error"]
            if isinstance(error, str):
                raise RuntimeError(f"UE error: {error}")
            msg = error.get('message', 'Unknown')
            data = error.get('data')
            if data:
                msg = f"{msg}: {data}"
            raise RuntimeError(f"UE error [{error.get('code', '?')}]: {msg}")

        return response.get("result", {})

    except (socket.timeout, ConnectionError, BrokenPipeError, OSError) as e:
        logger.error("UE communication failed: %s", e)
        disconnect()
        raise ConnectionError(f"UE communication failed: {e}")
