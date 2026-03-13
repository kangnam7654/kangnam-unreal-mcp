"""
Unreal Engine connection: TCP socket with retry and reconnection.
Connection is created at server startup (lifespan) and exposed via get_unreal_connection()
so tools and helpers can use it without receiving it explicitly.

Message format (JSON-RPC 2.0) is handled by kn_mcp.core.protocol; this module
only deals with transport (send/receive bytes).
"""
import json
import logging
import socket
import struct
import threading
import time
from collections.abc import Callable
from typing import Any

from kn_mcp.core import protocol as jsonrpc_protocol

logger = logging.getLogger("UnrealMCP.Connection")

# Current connection set at server startup (lifespan); used by helpers that import get_unreal_connection
_current_connection: "UnrealConnection | None" = None
_connection_lock = threading.Lock()

# UE TCP server port range (matches C++ KN_MCP_ServerThread)
UE_PORT_START = 27777
UE_PORT_END = 27787


def set_current_connection(conn: "UnrealConnection | None") -> None:
    """Set the connection used by get_unreal_connection(). Called from server lifespan."""
    global _current_connection
    with _connection_lock:
        _current_connection = conn


def get_unreal_connection() -> "UnrealConnection | None":
    """Return the current connection (set at server startup). Used by tools and helpers."""
    with _connection_lock:
        return _current_connection


def find_available_ue_ports() -> list[int]:
    """Scan UE port range (27777–27787) and return ports with active UE instances."""
    available = []
    for port in range(UE_PORT_START, UE_PORT_END + 1):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            time.sleep(0.05)
            if result == 0:
                available.append(port)
        except Exception:
            pass
    return available


def is_ue_listening(host: str = "127.0.0.1", port: int = UE_PORT_START) -> bool:
    """Quick non-blocking check whether UE is listening on the given port."""
    for attempt in range(2):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.0)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
            if result == 10061:  # WSAECONNREFUSED
                return False
            if attempt < 1:
                time.sleep(0.1)
        except Exception:
            if attempt < 1:
                time.sleep(0.1)
    return False


class UnrealConnection:
    """
    Robust connection to Unreal Engine with automatic retry and reconnection.
    """

    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5
    MAX_RETRY_DELAY = 5.0
    BUFFER_SIZE = 8192

    LARGE_OPERATION_COMMANDS = {
        "get_available_materials",
        # TODO: Add large operation commands here
    }

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 27777,
        connect_timeout: int = 10,
        default_recv_timeout: int = 30,
        large_op_recv_timeout: int = 300,
    ):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.default_recv_timeout = default_recv_timeout
        self.large_op_recv_timeout = large_op_recv_timeout
        self.socket: socket.socket | None = None
        self.connected = False
        self._lock = threading.RLock()
        self._last_error: str | None = None
        self._on_connected: Callable[[], None] | None = None
        self._on_disconnected: Callable[[], None] | None = None
        self._last_notified_state: bool | None = None

    def _create_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.connect_timeout)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 131072)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 131072)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack("hh", 1, 0))
        except OSError:
            pass
        return sock

    def connect(self) -> bool:
        with self._lock:
            if self.socket and self.connected:
                return True
        for attempt in range(self.MAX_RETRIES + 1):
            with self._lock:
                self._close_socket_unsafe()
                try:
                    logger.info(
                        f"Connecting to Unreal at {self.host}:{self.port} "
                        f"(attempt {attempt + 1}/{self.MAX_RETRIES + 1})..."
                    )
                    self.socket = self._create_socket()
                    self.socket.connect((self.host, self.port))
                    self.connected = True
                    self._last_error = None
                    logger.info("Successfully connected to Unreal Engine")
                    self._notify_state_change(True)
                    return True
                except socket.timeout as e:
                    self._last_error = f"Connection timeout: {e}"
                    logger.warning(f"Connection timeout (attempt {attempt + 1})")
                except ConnectionRefusedError as e:
                    self._last_error = f"Connection refused: {e}"
                    logger.warning(f"Connection refused (attempt {attempt + 1})")
                except OSError as e:
                    self._last_error = f"OS error: {e}"
                    logger.warning(f"OS error during connection: {e} (attempt {attempt + 1})")
                except Exception as e:
                    self._last_error = f"Unexpected error: {e}"
                    logger.error(f"Unexpected connection error: {e} (attempt {attempt + 1})")
                self._close_socket_unsafe()
                self.connected = False

            if attempt < self.MAX_RETRIES:
                delay = min(self.BASE_RETRY_DELAY * (2**attempt), self.MAX_RETRY_DELAY)
                logger.info(f"Retrying connection in {delay:.1f}s...")
                time.sleep(delay)

        logger.error(f"Failed to connect after {self.MAX_RETRIES + 1} attempts. Last error: {self._last_error}")
        return False

    def _close_socket_unsafe(self) -> None:
        if self.socket:
            try:
                self.socket.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None
        self.connected = False

    def disconnect(self) -> None:
        with self._lock:
            was_connected = self.connected
            self._close_socket_unsafe()
            logger.debug("Disconnected from Unreal Engine")
        if was_connected:
            self._notify_state_change(False)

    def on_connected(self, callback: Callable[[], None]) -> None:
        """Register callback invoked when connection is established."""
        self._on_connected = callback

    def on_disconnected(self, callback: Callable[[], None]) -> None:
        """Register callback invoked when connection is lost."""
        self._on_disconnected = callback

    def _notify_state_change(self, connected: bool) -> None:
        """Invoke registered callback if state actually changed."""
        if self._last_notified_state == connected:
            return
        self._last_notified_state = connected
        try:
            if connected and self._on_connected:
                self._on_connected()
            elif not connected and self._on_disconnected:
                self._on_disconnected()
        except Exception as e:
            logger.warning("Connection callback error: %s", e)

    def _get_timeout_for_command(self, command_type: str) -> int:
        if any(large_cmd in command_type for large_cmd in self.LARGE_OPERATION_COMMANDS):
            return self.large_op_recv_timeout
        return self.default_recv_timeout

    def _receive_response(self, command_type: str) -> bytes:
        timeout = self._get_timeout_for_command(command_type)
        if self.socket:
            self.socket.settimeout(timeout)
        buffer = bytearray()
        start_time = time.time()

        try:
            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise socket.timeout(f"Overall timeout after {elapsed:.1f}s")
                try:
                    chunk = self.socket.recv(self.BUFFER_SIZE) if self.socket else b""
                except socket.timeout:
                    if buffer:
                        try:
                            json.loads(buffer.decode("utf-8"))
                            logger.info(f"Got complete response after recv timeout ({len(buffer)} bytes)")
                            return bytes(buffer)
                        except json.JSONDecodeError:
                            pass
                    raise

                if not chunk:
                    if not buffer:
                        raise ConnectionError("Connection closed before receiving any data")
                    break

                buffer.extend(chunk)
                try:
                    json.loads(buffer.decode("utf-8"))
                    logger.info(f"Received complete response ({len(buffer)} bytes) for {command_type}")
                    return bytes(buffer)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue

        except socket.timeout:
            elapsed = time.time() - start_time
            if buffer:
                try:
                    json.loads(buffer.decode("utf-8"))
                    logger.warning(f"Using response received before timeout ({len(buffer)} bytes)")
                    return bytes(buffer)
                except Exception:
                    pass
            raise TimeoutError(
                f"Timeout after {elapsed:.1f}s waiting for response to {command_type} "
                f"(received {len(buffer)} bytes)"
            )

        if buffer:
            try:
                json.loads(buffer.decode("utf-8"))
                return bytes(buffer)
            except Exception:
                raise ConnectionError(f"Connection closed with incomplete data ({len(buffer)} bytes)")
        raise ConnectionError("Connection closed without response")

    def send_command(self, command: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        last_error = None
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                return self._send_command_once(command, params or {}, attempt)
            except (ConnectionError, TimeoutError, socket.error, OSError) as e:
                last_error = str(e)
                logger.warning(f"Command failed (attempt {attempt + 1}/{self.MAX_RETRIES + 1}): {e}")
                self.disconnect()
                if attempt < self.MAX_RETRIES:
                    delay = min(self.BASE_RETRY_DELAY * (2**attempt), self.MAX_RETRY_DELAY)
                    logger.info(f"Retrying command in {delay:.1f}s...")
                    time.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected error sending command: {e}")
                self.disconnect()
                return {"status": "error", "error": str(e)}
        return {"status": "error", "error": f"Command failed after {self.MAX_RETRIES + 1} attempts: {last_error}"}

    def _send_command_once(self, command: str, params: dict[str, Any], attempt: int) -> dict[str, Any]:
        # Connect outside the send lock so that connect()'s retry sleeps
        # don't block other threads from accessing the connection.
        if not self.connect():
            raise ConnectionError(f"Failed to connect to Unreal Engine: {self._last_error}")
        with self._lock:
            try:
                payload = jsonrpc_protocol.build_request(command, params)
                logger.info(f"Sending command (attempt {attempt + 1}): {command}")
                if self.socket:
                    self.socket.settimeout(10)
                    self.socket.sendall(payload)
                response_data = self._receive_response(command)
                response = jsonrpc_protocol.parse_response(response_data)
                logger.info(f"Command {command} completed successfully")
                if response.get("status") == "error":
                    logger.warning("Unreal returned error: %s", response.get("error", "Unknown error"))
                return response
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Invalid response from Unreal: %s", e)
                return {"status": "error", "error": str(e)}
