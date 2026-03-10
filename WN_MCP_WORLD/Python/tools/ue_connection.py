"""UE TCP connection utilities.

Provides execute() for sending JSON-RPC 2.0 commands to UE C++ plugin.
"""

import json
import socket
from typing import Optional, Dict, Any


# =============================================================================
# Configuration
# =============================================================================

UE_HOST = "127.0.0.1"
UE_PORT = 27777
UE_TIMEOUT = 30.0

_socket: Optional[socket.socket] = None


# =============================================================================
# Connection Management
# =============================================================================


def connect() -> bool:
    """Connect to UE TCP server if not already connected."""
    global _socket
    if _socket is not None:
        return True
    try:
        _socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _socket.settimeout(UE_TIMEOUT)
        _socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        _socket.connect((UE_HOST, UE_PORT))
        return True
    except Exception as e:
        _socket = None
        raise ConnectionError(f"Cannot connect to UE at {UE_HOST}:{UE_PORT} - {e}")


def disconnect():
    """Disconnect from UE TCP server."""
    global _socket
    if _socket:
        try:
            _socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        _socket.close()
        _socket = None


def execute(command_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send JSON-RPC 2.0 command to UE and return result.

    Args:
        command_name: C++ command name (e.g. "get_actors_in_level")
        params: Optional command parameters

    Returns:
        Result dict from UE response

    Raises:
        ConnectionError: Cannot connect or communication failed
        RuntimeError: UE returned an error response
    """
    connect()

    request = {
        "jsonrpc": "2.0",
        "method": "command",
        "id": command_name,
        "params": params if params is not None else {}
    }

    try:
        _socket.send(json.dumps(request).encode("utf-8"))

        # Read until we have a complete JSON response
        chunks = []
        while True:
            chunk = _socket.recv(65536)
            if not chunk:
                disconnect()
                raise ConnectionError("UE closed connection")
            chunks.append(chunk)
            try:
                response = json.loads(b"".join(chunks).decode("utf-8"))
                break
            except json.JSONDecodeError:
                continue

        if "error" in response:
            error = response["error"]
            if isinstance(error, str):
                raise RuntimeError(f"UE error: {error}")
            raise RuntimeError(f"UE error [{error.get('code', '?')}]: {error.get('message', 'Unknown')}")

        return response.get("result", {})

    except (socket.timeout, ConnectionError, BrokenPipeError, OSError) as e:
        disconnect()
        raise ConnectionError(f"UE communication failed: {e}")
