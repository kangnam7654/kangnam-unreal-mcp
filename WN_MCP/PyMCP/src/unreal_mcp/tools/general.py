"""
General Unreal MCP tools: engine status, connection check, reconnect, log level.
Uses get_unreal_connection() from server lifespan; no separate socket management.
"""
import logging
import socket
import time
from typing import Any, Callable, Dict, List, Optional

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.general")

# Default port range for listing UE instances (when not from config)
DEFAULT_PORT_START = 55550
DEFAULT_PORT_END = 55570


def _is_listening(host: str, port: int, timeout: float = 2.0) -> bool:
    """Check if a host:port is accepting TCP connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


def _find_available_ports(host: str, port_start: int, port_end: int) -> List[int]:
    """Find ports in range that accept connections (UE instances)."""
    available: List[int] = []
    for port in range(port_start, port_end + 1):
        if _is_listening(host, port, timeout=1.0):
            available.append(port)
        time.sleep(0.02)
    return available


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    """Register general tools: UE status, connection check, reconnect, log level."""

    @mcp.tool()
    def check_ue_listening() -> Dict[str, Any]:
        """Check if Unreal Engine is listening on the configured host and port."""
        conn = get_connection()
        if not conn:
            return {
                "success": False,
                "listening": False,
                "message": "No connection configured",
            }
        host = getattr(conn, "host", "127.0.0.1")
        port = getattr(conn, "port", 55557)
        listening = _is_listening(host, port)
        msg = f"UE is listening on {host}:{port}" if listening else f"UE is not listening on {host}:{port}"
        return {
            "success": True,
            "listening": listening,
            "host": host,
            "port": port,
            "message": f"✅ {msg}" if listening else f"❌ {msg}",
        }

    @mcp.tool()
    def check_ue_connection() -> Dict[str, Any]:
        """Check current connection status to Unreal Engine."""
        conn = get_connection()
        if not conn:
            return {
                "success": False,
                "connected": False,
                "message": "No connection configured",
            }
        connected = getattr(conn, "connected", False)
        host = getattr(conn, "host", "127.0.0.1")
        port = getattr(conn, "port", 55557)
        listening = _is_listening(host, port)

        if connected:
            status = "CONNECTED"
            display = (
                "🔗 **CONNECTED**\n"
                "================================\n"
                f"✅ Successfully connected to Unreal Engine\n"
                f"- Host: {host}\n"
                f"- Port: {port}\n"
                "- Status: Active\n"
            )
            message = "✅ Connected to UE"
        elif listening:
            status = "LISTENING"
            display = (
                "📡 **LISTENING (Not Connected)**\n"
                "================================\n"
                f"⚠️ Unreal Engine is listening but not connected yet\n"
                f"- Host: {host}\n"
                f"- Port: {port}\n"
                "- Status: Waiting for connection...\n"
            )
            message = "⚠️ UE is listening but not connected"
        else:
            status = "OFFLINE"
            display = (
                "❌ **OFFLINE**\n"
                "================================\n"
                "Unreal Engine is not running or not listening\n"
                f"- Host: {host}\n"
                f"- Port: {port}\n"
                "- Status: Offline\n"
            )
            message = "❌ UE is offline"

        return {
            "success": True,
            "connected": connected,
            "listening": listening,
            "host": host,
            "port": port,
            "connection_status": status,
            "display": display,
            "message": message,
        }

    @mcp.tool()
    def list_ue_instances(
        host: Optional[str] = None,
        port_start: Optional[int] = None,
        port_end: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List Unreal Engine instances listening in a port range.

        Args:
            host: Host to scan (default: from current connection config).
            port_start: Start of port range (default: 55550).
            port_end: End of port range (default: 55570).

        Returns:
            List of ports where UE is listening and current connection port if any.
        """
        conn = get_connection()
        h = host or (getattr(conn, "host", None) if conn else None) or "127.0.0.1"
        current_port = getattr(conn, "port", None) if conn else None
        start = port_start if port_start is not None else DEFAULT_PORT_START
        end = port_end if port_end is not None else DEFAULT_PORT_END
        if start > end:
            start, end = end, start

        available = _find_available_ports(h, start, end)
        if not available:
            return {
                "success": True,
                "total_instances": 0,
                "current_port": current_port,
                "instances": [],
                "message": "No Unreal Engine instances detected in the given port range.",
            }

        instances = [
            {
                "port": p,
                "host": h,
                "current": p == current_port,
                "status": "🔗 Current" if p == current_port else "✅ Available",
            }
            for p in available
        ]
        return {
            "success": True,
            "total_instances": len(available),
            "current_port": current_port,
            "host": h,
            "port_range": [start, end],
            "instances": instances,
            "message": f"Found {len(available)} instance(s). Current port: {current_port}",
        }

    @mcp.tool()
    def reconnect_ue() -> Dict[str, Any]:
        """Disconnect and reconnect to Unreal Engine. Use to reset connection state."""
        conn = get_connection()
        if not conn:
            return {"success": False, "message": "No connection configured"}
        try:
            conn.disconnect()
            time.sleep(0.3)
            ok = conn.connect()
            if ok:
                logger.info("Reconnected to Unreal Engine")
                return {"success": True, "message": "🔗 Successfully reconnected to Unreal Engine"}
            return {"success": False, "message": "Failed to reconnect to Unreal Engine"}
        except Exception as e:
            logger.exception("Reconnect error: %s", e)
            return {"success": False, "message": str(e)}
