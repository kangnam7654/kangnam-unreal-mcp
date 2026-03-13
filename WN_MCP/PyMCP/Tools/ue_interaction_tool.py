import os
import sys
import json
import socket as socket_module
import threading
import time
import re
import importlib.util
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, AsyncIterator, Optional, Callable, List
from contextvars import ContextVar

from .log_tool import log_info as mcp_log, log_debug, log_misc, set_log_level, get_available_log_levels, get_current_log_level
from .params import get_mcp_params, _set_mcp_params

# ============================================================================
# EXPORTED PUBLIC API
# ============================================================================
__all__ = [
    'LAST_STATUS_CHANGE',
    'get_mcp_params',
    '_set_mcp_params',
    'ue_send_command',
    'ue_receive_response',
    'ue_connect',
    'ue_disconnect',
    'ue_reconnect',
    'is_ue_listening',
    'is_ue_connected',
    'ue_execute_simple_command',
    'get_user_tool_directories',
    'register_user_tool_directories',
    'register_connection_callback',
    'register_notification_callback',
    'register_ue_connected_callback',
    'register_ue_disconnected_callback',
    'start_auto_reconnect',
    'stop_auto_reconnect',
    'find_available_ue_ports',
    'register_tools',
]

# ============================================================================
# MCP PARAMETERS CONTEXT (imported from params.py to avoid circular imports)
# ============================================================================
from .params import get_mcp_params, _set_mcp_params

# ============================================================================
# TYPE DEFINITIONS
# ============================================================================
UE_HOST = '127.0.0.1'
UE_PORT = 27777
UE_PORT_START = 27777
UE_PORT_END = 27787

# ============================================================================
# GLOBAL STATE (Module-level variables shared across functions)
# Naming: UPPERCASE indicates global variable
# ============================================================================
UE_SOCKET: Optional[socket_module.socket] = None  # Socket connection to UE
UE_WAS_CONNECTED: Optional[bool] = None  # Track previous connection state to detect forced disconnection
AUTO_RECONNECT_ENABLED = False  # Whether auto-reconnect thread is running
AUTO_RECONNECT_THREAD: Optional[threading.Thread] = None  # Background reconnect thread
CONNECTION_CALLBACKS: list[Callable[[bool], None]] = []  # Callbacks for connection status changes
UE_WAS_LISTENING: Optional[bool] = None  # Track previous listening state (None = first check)
SHOW_NOTIFICATION_CALLBACK: Optional[Callable[[str, str, str], None]] = None  # For UI notifications
LAST_STATUS_CHANGE: Optional[Dict[str, Any]] = None  # Store last status change for Agent display
LAST_NOTIFIED_CONNECTION_STATE: Optional[bool] = None  # Track last notified state to prevent duplicate notifications

# ============================================================================
# DYNAMIC TOOL REGISTRATION (Tools discovered from UE directories)
# ============================================================================
MCP_SERVER = None  # FastMCP server reference
REGISTERED_USER_TOOLS: Dict[str, Any] = {}  # Track registered user tools for cleanup
REGISTERED_SIMPLE_COMMANDS: Dict[str, str] = {}  # Track registered simple commands: {command_name: module_name}
ON_UE_CONNECTED_CALLBACK: Optional[Callable[[], None]] = None  # Callback when UE connects
ON_UE_DISCONNECTED_CALLBACK: Optional[Callable[[], None]] = None  # Callback when UE disconnects

def find_available_ue_ports() -> List[int]:
    """Find all available UE instances in the port range (27777-27787).
    
    Returns:
        List of ports with active UE instances
    """
    available_ports = []
    
    for port in range(UE_PORT_START, UE_PORT_END + 1):
        try:
            test_socket = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
            test_socket.settimeout(1.0)  # 1 second timeout for reliable detection
            result = test_socket.connect_ex((UE_HOST, port))
            test_socket.close()
            time.sleep(0.05)  # Brief pause to ensure socket cleanup
            
            if result == 0:  # Connection successful
                available_ports.append(port)
        except Exception:
            pass
    
    return available_ports

def is_ue_listening() -> bool:
    """Check if Unreal Engine is listening on the designated port.
    
    Attempts multiple times with 1 second timeout to account for backlog issues.
    
    Returns:
        True if UE is listening, False otherwise
    """
    max_attempts = 2
    for attempt in range(max_attempts):
        try:
            test_socket = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
            test_socket.settimeout(1.0)  # Shorter timeout - fail fast
            result = test_socket.connect_ex((UE_HOST, UE_PORT))
            test_socket.close()
            
            if result == 0:
                return True  # Connection succeeded
            elif result == 10061:  # WSAECONNREFUSED - not listening
                return False
            else:
                # Other error (might be temporary) - retry
                if attempt < max_attempts - 1:
                    time.sleep(0.1)
                    continue
                else:
                    return False  # Final attempt failed
        except Exception as e:
            log_debug(f'is_ue_listening() attempt {attempt+1} error: {e}')
            if attempt < max_attempts - 1:
                time.sleep(0.1)
            else:
                return False
    
    return False


def register_connection_callback(callback: Callable[[bool], None]) -> None:
    """Register a callback to be notified of connection status changes.
    
    Args:
        callback: Function that takes a boolean (True=connected, False=disconnected)
    """
    CONNECTION_CALLBACKS.append(callback)
    log_debug(f'Registered connection callback')


def register_notification_callback(callback: Callable[[str, str, str], None]) -> None:
    """Register a callback for UI notifications.
    
    Args:
        callback: Function that takes (title: str, message: str, level: str)
    """
    global SHOW_NOTIFICATION_CALLBACK
    SHOW_NOTIFICATION_CALLBACK = callback
    log_debug(f'Registered notification callback')


def register_ue_connected_callback(callback: Callable[[], None]) -> None:
    """Register a callback to be called when UE successfully connects.
    
    Args:
        callback: Function to call with no arguments when UE connects
    """
    global ON_UE_CONNECTED_CALLBACK
    ON_UE_CONNECTED_CALLBACK = callback
    log_debug(f'Registered UE connected callback')


def register_ue_disconnected_callback(callback: Callable[[], None]) -> None:
    """Register a callback to be called when UE disconnects.
    
    Args:
        callback: Function to call with no arguments when UE disconnects
    """
    global ON_UE_DISCONNECTED_CALLBACK
    ON_UE_DISCONNECTED_CALLBACK = callback
    log_debug(f'Registered UE disconnected callback')


def _notify_connection_status(connected: bool) -> None:
    """Notify all registered callbacks of connection status change.
    
    Only notifies if the connection state has actually changed to prevent duplicate notifications.
    """
    global LAST_STATUS_CHANGE, LAST_NOTIFIED_CONNECTION_STATE
    
    # Prevent duplicate notifications for the same state
    if LAST_NOTIFIED_CONNECTION_STATE == connected:
        return  # State hasn't changed, skip notification
    
    LAST_NOTIFIED_CONNECTION_STATE = connected
    
    status_str = '🔗 CONNECTED' if connected else '❌ DISCONNECTED'
    separator = '=' * 80
    
    mcp_log(separator)
    mcp_log(f'UE Connection Status: {status_str} (Port {UE_PORT})')
    mcp_log(separator)
    
    # Store status change for Agent display
    LAST_STATUS_CHANGE = {
        'status': 'CONNECTED' if connected else 'DISCONNECTED',
        'connected': connected,
        'port': UE_PORT,
        'timestamp': datetime.now().isoformat(),
        'message': f'🔗 Successfully connected to Unreal Engine on port {UE_PORT}' if connected else f'❌ Disconnected from Unreal Engine (port {UE_PORT})'
    }
    
    # Send UI notification if callback registered
    if SHOW_NOTIFICATION_CALLBACK:
        try:
            if connected:
                SHOW_NOTIFICATION_CALLBACK('🔗 Engine Connected', '✅ Successfully connected to Unreal Engine', 'success')
            else:
                SHOW_NOTIFICATION_CALLBACK('❌ Engine Disconnected', '⚠️  Disconnected from Unreal Engine', 'warning')
        except Exception as e:
            mcp_log(f'Warning - Error in notification callback: {e}')
    
    # Call connection callbacks
    for callback in CONNECTION_CALLBACKS:
        try:
            callback(connected)
        except Exception as e:
            mcp_log(f'Warning - Error in connection callback: {e}')
    
    # Call UE connected/disconnected callback for user tool management
    try:
        if connected:
            # Call UE connected callback to discover and register user tools
            if ON_UE_CONNECTED_CALLBACK:
                ON_UE_CONNECTED_CALLBACK()
        else:
            # Automatically unregister user tools when UE disconnects
            unregister_user_tool_directories()
            # Call UE disconnected callback if registered
            if ON_UE_DISCONNECTED_CALLBACK:
                ON_UE_DISCONNECTED_CALLBACK()
    except Exception as e:
        mcp_log(f'Error managing user tool directories: {e}')

def ue_connect() -> bool:
    """Connect to Unreal Engine.
    
    Returns:
        True if connection successful, False otherwise
    """
    global UE_SOCKET
    try:
        if UE_SOCKET is not None:
            mcp_log('Warning - Already connected to UE')
            return True
        
        UE_SOCKET = socket_module.socket(socket_module.AF_INET, socket_module.SOCK_STREAM)
        UE_SOCKET.settimeout(10)  # Set a timeout for connection attempts
        UE_SOCKET.setsockopt(socket_module.IPPROTO_TCP, socket_module.TCP_NODELAY, 1)  # Disable Nagle's algorithm
        UE_SOCKET.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_KEEPALIVE, 1)  # Enable TCP keep-alive
        UE_SOCKET.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_RCVBUF, 65536)  # Increase receive buffer
        UE_SOCKET.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_SNDBUF, 65536)  # Increase send buffer
        
        # SO_LINGER: Allow socket to close immediately and reuse address
        # l_onoff=1, l_linger=0 means close immediately without TIME_WAIT
        try:
            import struct
            UE_SOCKET.setsockopt(socket_module.SOL_SOCKET, socket_module.SO_LINGER, 
                               struct.pack('ii', 1, 0))
        except Exception as e:
            mcp_log(f'Note - Could not set SO_LINGER: {e}')
        
        mcp_log(f'Attempting to connect to UE at {UE_HOST}:{UE_PORT}')
        UE_SOCKET.connect((UE_HOST, UE_PORT))
        mcp_log(f'✅ Successfully connected to UE on port {UE_PORT}')
        _notify_connection_status(True)
        return True
    except Exception as e:
        mcp_log(f'❌ Failed to connect to UE: {e}')
        UE_SOCKET = None
        _notify_connection_status(False)
        return False


def ue_disconnect() -> None:
    """Disconnect from Unreal Engine and cleanly close socket."""
    global UE_SOCKET, UE_WAS_LISTENING
    
    if UE_SOCKET is not None:
        try:
            # Try graceful shutdown first (both read and write)
            try:
                UE_SOCKET.shutdown(socket_module.SHUT_RDWR)
                mcp_log(f'Socket shutdown completed (port {UE_PORT})')
            except socket_module.error as e:
                # Socket might already be closed or not connected
                mcp_log(f'Socket shutdown note: {e}')
            except Exception as e:
                mcp_log(f'Socket shutdown exception: {e}')
            
            # Force close the socket
            try:
                UE_SOCKET.close()
                mcp_log(f'✅ Socket closed cleanly (port {UE_PORT})')
            except Exception as e:
                mcp_log(f'Error closing socket: {e}')
        
        except Exception as e:
            mcp_log(f'⚠️  Warning - Error during UE disconnect: {e}')
        finally:
            UE_SOCKET = None
            UE_WAS_LISTENING = False  # Mark listening state as false after disconnect
            _notify_connection_status(False)


def ue_reconnect() -> bool:
    """Disconnect from and reconnect to Unreal Engine.
    
    Returns:
        True if reconnection successful, False otherwise
    """
    mcp_log('Attempting to reconnect to UE...')
    ue_disconnect()
    time.sleep(2)  # Wait for C++ to fully close previous connection
    return ue_connect()


def is_ue_connected() -> bool:
    """Check if currently connected to Unreal Engine.
    
    Uses multiple checks for reliability:
    1. Socket exists
    2. getpeername() succeeds  
    3. Socket doesn't have pending recv (which would indicate closed connection)
    
    Returns:
        True if connected and socket is valid, False otherwise
    """
    if UE_SOCKET is None:
        return False
    
    try:
        # Check 1: Get peer address (fails if socket is closed)
        UE_SOCKET.getpeername()
        
        # Check 2: Try a non-blocking recv with zero bytes to detect closed connection
        # If connection is closed, recv will not raise but return empty data
        try:
            # Save original timeout
            original_timeout = UE_SOCKET.gettimeout()
            original_blocking = UE_SOCKET.getblocking()
            
            try:
                UE_SOCKET.setblocking(False)
                # Try to recv 1 byte without consuming it
                # This will immediately return if socket is ready/closed
                data = UE_SOCKET.recv(1, socket_module.MSG_PEEK)
                
                # If we get here without exception, connection is valid
                # (MSG_PEEK means data isn't consumed, we're just peeking)
                return True
            except BlockingIOError:
                # Socket would block = connection is still active
                return True
            except (ConnectionResetError, BrokenPipeError, OSError) as e:
                # Connection is broken
                log_debug(f'recv check detected broken connection: {type(e).__name__}')
                return False
            finally:
                # CRITICAL: Always restore original socket state
                try:
                    if original_blocking:
                        UE_SOCKET.setblocking(True)
                    if original_timeout is not None:
                        UE_SOCKET.settimeout(original_timeout)
                except Exception as restore_err:
                    log_debug(f'Warning: Could not restore socket state: {restore_err}')
        except Exception as e:
            log_debug(f'setblocking error during connection check: {type(e).__name__}: {e}')
            return False
    except (OSError, socket_module.error) as e:
        # getpeername() failed = socket is not connected
        log_debug(f'getpeername failed: {type(e).__name__}: {e}')
        return False


def _auto_reconnect_worker() -> None:
    """Background worker thread for auto-reconnection.
    
    Periodically checks if UE is listening and attempts connection/reconnection.
    Detects when UE instance closes unexpectedly and logs disconnect event.
    Automatically switches to alternative available instances if the current one disconnects.
    NOTE: This should not be used with stdio transport as it interferes with MCP communication.
    """
    global UE_WAS_LISTENING, UE_WAS_CONNECTED, UE_SOCKET, UE_PORT
    
    mcp_log('Auto-reconnect worker started')
    check_cycle = 0
    last_disconnect_log = None
    
    while AUTO_RECONNECT_ENABLED:
        try:
            check_cycle += 1
            
            # Check if we're currently connected
            currently_connected = is_ue_connected()
            
            # Log connection status every 2 cycles (every 2 seconds - diagnostic only)
            # COMMENTED OUT: Generates too much noise in logs
            # if check_cycle % 2 == 0:
            #     log_debug(f'[AutoReconnect-Cycle{check_cycle}] Connected={currently_connected}, WasConnected={UE_WAS_CONNECTED}, Port={UE_PORT}')
            
            # Detect ANY connection state change
            if UE_WAS_CONNECTED != currently_connected:
                if UE_WAS_CONNECTED is True and currently_connected is False:
                    # Connected → Disconnected (IMPORTANT!)
                    current_time = datetime.now().isoformat()
                    
                    # Only log once per disconnect (avoid duplicate logs)
                    if last_disconnect_log != current_time:
                        last_disconnect_log = current_time
                        
                        mcp_log('='*80)
                        mcp_log(f'❌ UE instance DISCONNECTED UNEXPECTEDLY (port {UE_PORT})')
                        mcp_log(f'   Reason: Engine instance was closed or crashed')
                        mcp_log(f'   Time: {current_time}')
                        mcp_log('='*80)
                        UE_SOCKET = None  # Ensure socket is cleared
                        
                        try:
                            _notify_connection_status(False)
                        except Exception as e:
                            mcp_log(f'Error in disconnect callback: {e}')
                        
                        # Try to auto-switch to another available UE instance
                        available_ports = find_available_ue_ports()
                        other_ports = [p for p in available_ports if p != UE_PORT]
                        
                        if other_ports:
                            new_port = other_ports[0]  # Use first available alternative
                            mcp_log(f'🔄 Auto-switching to alternative UE instance on port {new_port}')
                            UE_PORT = new_port
                            UE_WAS_LISTENING = None  # Reset listening state for new port
                        else:
                            mcp_log(f'⚠️  No alternative UE instances available')
                elif UE_WAS_CONNECTED is False and currently_connected is True:
                    # Disconnected → Connected
                    mcp_log(f'✅ NEW CONNECTION DETECTED on port {UE_PORT}')
                elif UE_WAS_CONNECTED is None:
                    # Initial state
                    mcp_log(f'ℹ️  Initial state check: connected={currently_connected}, port={UE_PORT}')
            
            # Update connection state tracking
            UE_WAS_CONNECTED = currently_connected
            
            if currently_connected:
                # If already connected, check connection status frequently
                # to detect unexpected disconnection quickly
                time.sleep(1)  # Check every 1 second while connected
                continue
            
            # Not connected - check if UE is listening
            currently_listening = is_ue_listening()
            
            # Event-based logging: log when UE listening state changes
            if UE_WAS_LISTENING is None or currently_listening != UE_WAS_LISTENING:
                if UE_WAS_LISTENING is False and currently_listening is True:
                    mcp_log(f'✅ UE came back online and is now listening on port {UE_PORT}')
                elif UE_WAS_LISTENING is True and currently_listening is False:
                    mcp_log(f'⚠️  UE went offline (port {UE_PORT} - stopped listening)')
                
                UE_WAS_LISTENING = currently_listening
            
            if currently_listening:
                mcp_log(f'🔄 Attempting to connect to UE on port {UE_PORT}...')
                if ue_connect():
                    mcp_log(f'✅ Connection to UE established (port {UE_PORT})')
                else:
                    mcp_log(f'⚠️  Connection attempt failed on port {UE_PORT}, will retry')
                    time.sleep(2)  # Reduced wait time after failed connection attempt
            else:
                # Check more frequently when UE is not listening
                time.sleep(2)
        
        except Exception as e:
            mcp_log(f'Error in auto-reconnect worker: {e}')
            time.sleep(2)
    
    log_debug('Auto-reconnect worker stopped')


def start_auto_reconnect() -> None:
    """Start the automatic reconnection service.
    
    This spawns a background thread that monitors the connection to UE
    and automatically reconnects if the connection is lost or if UE becomes available.
    """
    global AUTO_RECONNECT_ENABLED, AUTO_RECONNECT_THREAD
    
    if AUTO_RECONNECT_ENABLED:
        mcp_log('Warning - Auto-reconnect is already running')
        return
    
    AUTO_RECONNECT_ENABLED = True
    AUTO_RECONNECT_THREAD = threading.Thread(
        target=_auto_reconnect_worker,
        daemon=True,
        name='UE_AutoReconnect'
    )
    AUTO_RECONNECT_THREAD.start()
    log_debug('Auto-reconnect service started')


def stop_auto_reconnect() -> None:
    """Stop the automatic reconnection service."""
    global AUTO_RECONNECT_ENABLED
    
    if not AUTO_RECONNECT_ENABLED:
        log_debug('Warning - Auto-reconnect is not running')
        return
    
    AUTO_RECONNECT_ENABLED = False
    
    # Wait for thread to finish (max 2 seconds)
    if AUTO_RECONNECT_THREAD and AUTO_RECONNECT_THREAD.is_alive():
        AUTO_RECONNECT_THREAD.join(timeout=2)
    
    mcp_log('Auto-reconnect service stopped')

def ue_receive_response(buffer_size: int = 4096) -> Optional[Dict[str, Any]]:
    """Receive and parse JSON-RPC 2.0 format response from UE socket.
    
    Args:
        buffer_size: Size of buffer to receive (default 4096)
    
    Returns:
        Parsed JSON-RPC 2.0 response dictionary, or None if not connected or error
        
    JSON-RPC 2.0 responses:
        Success: {"jsonrpc": "2.0", "result": {...}, "id": ...}
        Error: {"jsonrpc": "2.0", "error": {"code": int, "message": str}, "id": ...}
    """
    if not is_ue_connected():
        mcp_log('Warning - Not connected to UE')
        return None
    
    try:
        # Explicitly ensure socket timeout is set before recv
        if not UE_SOCKET:
            mcp_log('Error - UE_SOCKET is None')
            return None
        
        UE_SOCKET.settimeout(10)
        
        mcp_log('DEBUG: ue_receive_response() starting recv...')
        # Receive raw data from socket
        data = UE_SOCKET.recv(buffer_size)
        mcp_log(f'DEBUG: ue_receive_response() received {len(data)} bytes')
        
        if not data:
            mcp_log('Warning - No data received from UE (connection closed by peer)')
            # Connection was actually closed by peer - mark as disconnected
            ue_disconnect()
            return None
        
        # Decode UTF-8
        response_str = data.decode('utf-8')
        
        # Parse JSON
        response = json.loads(response_str)
        
        # Extract command ID for logging
        cmd_id = response.get('id', 'unknown') if isinstance(response, dict) else 'unknown'
        
        # Validate JSON-RPC 2.0 structure
        if not isinstance(response, dict):
            mcp_log(f'Error - Response is not a dictionary: {type(response)}')
            return None
        
        # Check for jsonrpc field
        if response.get('jsonrpc') != '2.0':
            mcp_log(f'Warning - jsonrpc field is not "2.0": {response.get("jsonrpc")}')
        
        # Check for result or error field
        if 'result' not in response and 'error' not in response:
            mcp_log(f'Error - Response missing both "result" and "error" fields: {response}')
            return None
        
        # Handle error responses
        if 'error' in response:
            error = response.get('error', {})
            if isinstance(error, dict):
                error_code = error.get('code', -32603)
                error_msg = error.get('message', 'Unknown error')
                mcp_log(f'Error from UE ({cmd_id}): Code {error_code} - {error_msg}')
                # Log full response for errors
                mcp_log(f'Full response: {response_str}')
            # Log JSON object at MISC level
            log_misc(f'[RECV] Response JSON from UE (id={cmd_id}): {json.dumps(response, indent=2)}')
            return response
        
        # Success response
        mcp_log(f'Received from UE ({cmd_id})')
        # Log JSON object at MISC level for successful responses
        log_misc(f'[RECV] Response JSON from UE (id={cmd_id}): {json.dumps(response, indent=2)}')
        return response
    
    except socket_module.timeout:
        mcp_log('ERROR - Socket timeout waiting for UE response (10 second timeout)')
        return None
    except json.JSONDecodeError as e:
        mcp_log(f'Error - JSON parse error: {e}')
        return None
    except UnicodeDecodeError as e:
        mcp_log(f'Error - UTF-8 decode error: {e}')
        return None
    except Exception as e:
        mcp_log(f'Error - Error receiving from UE: {type(e).__name__}: {e}')
        # Socket error while receiving - likely connection issue
        # Only disconnect if it's a socket-specific error
        if isinstance(e, (ConnectionError, BrokenPipeError, OSError)):
            ue_disconnect()
        return None


def ue_send_command(command_name: str, params: Optional[Dict[str, Any]] = None, category_name: str = "") -> Optional[bool]:
    """Send a command to UE in JSON-RPC 2.0 format.

    Args:
        command_name: Command name (becomes 'id' in JSON-RPC 2.0)
        params: Command parameters (optional)
        category_name: Category prefix matching C++ GetApplicationName() (e.g. "Actor", "Blueprint").
                       Prepended as "{category_name}_{command_name}" for routing.

    Returns:
        True if command sent successfully, False otherwise

    JSON-RPC 2.0 request format sent to UE:
        {
            "jsonrpc": "2.0",
            "method": "full_name",
            "params": {...},
            "id": "full_name"
        }
    """
    if not is_ue_connected():
        mcp_log('Warning - Not connected to UE')
        return False

    full_name = f"{category_name}_{command_name}" if category_name else command_name

    try:
        # Create JSON-RPC 2.0 request message
        message = {
            "jsonrpc": "2.0",
            "method": full_name,  # JSON-RPC 2.0: method is the remote procedure name
            "id": full_name,  # Use full name as ID for request tracking
            "params": params if params is not None else {}  # Always include params (empty dict if not provided)
        }
        
        # Log JSON object at MISC level before sending
        log_misc(f'[SEND] Request JSON to UE (id={full_name}): {json.dumps(message, indent=2)}')

        # Send as JSON
        command_str = json.dumps(message)
        if not UE_SOCKET:
            mcp_log('Error - UE_SOCKET is None, cannot send command')
            return False
        UE_SOCKET.send(command_str.encode('utf-8'))

        mcp_log(f'Sent to UE ({full_name})')
    except Exception as e:
        mcp_log(f'Error - Error sending command to UE: {e}')
        # Don't disconnect on send error - connection may still be valid
        return False
    return True # ue_send_command()

def ue_execute_simple_command(command_name: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """
    Execute simple command for Unreal Engine.
    
    Args:
        command_name: Name of the command to execute
        params: Optional parameters to pass to the command
    
    Returns:
        Optional[dict]: The JSON-RPC 2.0 response object from Unreal Engine, or None if error
    """
    try:
        ue_send_command(command_name, params)
        response = ue_receive_response()
        return response
    except Exception as e:
        raise Exception(f"{command_name} failed: {str(e)}")

# Track if tools have been registered (per module import)
UE_TOOLS_REGISTERED = False


def get_user_tool_directories() -> Dict[str, Any]:
    """Get list of directories containing @mcp.tool decorated functions from Unreal Engine.
    
    Communicates with UE to discover tool directories and returns structured JSON-RPC 2.0 response.
    
    Returns:
        JSON-RPC 2.0 format response:
        Success: {"jsonrpc": "2.0", "result": {"count": int, "directories": list[str], "message": str}}
        Error: {"jsonrpc": "2.0", "error": {"code": int, "message": str}}
    """
    
    try:
        # Send command to UE to get tool directories
        mcp_log('Requesting tool directories from UE...')
        success = ue_send_command('Application_get_user_tool_directories')
        
        if not success:
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Failed to send command to UE"
                }
            }
        
        # Receive response from UE (returns parsed Dict[str, Any])
        # Note: This will wait up to 10 seconds for response
        response_data = ue_receive_response()
        
        if not response_data:
            mcp_log('ERROR: get_user_tool_directories() - No response received from UE (timeout or disconnection)')
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "No response received from UE (timeout)"
                }
            }
        
        # Check if error response from UE
        if 'error' in response_data:
            error = response_data.get('error', {})
            mcp_log(f'Error response from UE: {error}')
            return {
                "jsonrpc": "2.0",
                "error": error
            }
        
        # Extract directories from result field
        result = response_data.get('result', {})
        directories = result.get('directories', []) if isinstance(result, dict) else []
        
        # Create JSON-RPC 2.0 response
        return {
            "jsonrpc": "2.0",
            "result": {
                "count": len(directories),
                "directories": directories,
                "message": f"Successfully retrieved {len(directories)} tool directories from UE"
            }
        }
    except socket_module.timeout as e:
        mcp_log(f'ERROR: get_user_tool_directories() - Socket timeout: {e}')
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Socket timeout while getting tool directories: {str(e)}"
            }
        }
    except Exception as e:
        mcp_log(f'ERROR: get_user_tool_directories() - Exception: {type(e).__name__}: {e}')
        import traceback
        mcp_log(f'Traceback: {traceback.format_exc()}')
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Exception while getting tool directories: {str(e)}"
            }
        }


def register_user_tool_directories(mcp: Any) -> None:
    """Discover and register @mcp.tool functions from user tool directories.
    
    Called when UE connection is established.
    
    Args:
        mcp: FastMCP server instance
    """
    global MCP_SERVER, REGISTERED_USER_TOOLS, REGISTERED_SIMPLE_COMMANDS
    
    MCP_SERVER = mcp
    mcp_log('='*80)
    mcp_log('🔄 Registering user tool directories from Unreal Engine...')
    
    try:
        # Get directories from UE (returns JSON-RPC 2.0 response)
        mcp_log('DEBUG: Calling get_user_tool_directories()...')
        result = get_user_tool_directories()
        mcp_log(f'DEBUG: get_user_tool_directories() returned: {result}')
        
        # Check if error response
        if 'error' in result:
            error_msg = result["error"].get("message", "Unknown error")
            mcp_log(f'❌ Failed to get tool directories: {error_msg}')
            mcp_log('='*80)
            return
        
        directories = result.get('result', {}).get('directories', [])
        mcp_log(f'DEBUG: directories = {directories}')
        if not directories:
            mcp_log('ℹ️  No tool directories found from UE')
            mcp_log('='*80)
            return
        
        mcp_log(f'✅ Found {result["result"]["count"]} tool directory/directories: {directories}')
        
        project_root = Path(__file__).parent.parent
        # Add main WN_MCP Tools directory to sys.path so all modules can be imported
        tools_dir = project_root / "Tools"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        
        # Ensure Tools package is registered in sys.modules
        # This allows "from Tools.ue_interaction_tool import ..." to work
        if 'Tools' not in sys.modules:
            tools_package_spec = importlib.util.spec_from_file_location(
                'Tools',
                tools_dir / '__init__.py',
                submodule_search_locations=[str(tools_dir)]
            )
            if tools_package_spec and tools_package_spec.loader:
                tools_package = importlib.util.module_from_spec(tools_package_spec)
                sys.modules['Tools'] = tools_package
                tools_package_spec.loader.exec_module(tools_package)
        
        # CRITICAL: Register this module under Tools namespace so user tools can import it
        # This MUST be done before user tools are loaded
        import sys as _sys_compat
        current_module = _sys_compat.modules.get(__name__)
        if current_module and 'Tools.ue_interaction_tool' not in _sys_compat.modules:
            _sys_compat.modules['Tools.ue_interaction_tool'] = current_module
        
        registered_count = 0
        
        # Process each directory
        for dir_name in directories:
            dir_path = project_root / dir_name
            
            if not dir_path.exists():
                mcp_log(f'⚠️  Tool directory not found: {dir_path}')
                continue
            
            # Add directory to sys.path for module imports
            if str(dir_path) not in sys.path:
                sys.path.insert(0, str(dir_path))
            
            mcp_log(f'📁 Scanning directory: {dir_name}')
            
            # Find all .py files
            py_files = list(dir_path.glob('*.py'))
            mcp_log(f'  Found {len(py_files)} Python file(s)')
            
            # Check each file for @mcp.tool
            for py_file in py_files:
                try:
                    with open(py_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Find functions with @mcp.tool decorator
                    # Pattern: @mcp.tool followed by def function_name (use raw string for regex)
                    tool_pattern = r'@mcp\.tool\s+def\s+(\w+)\s*\('
                    matches = re.findall(tool_pattern, content)
                    
                    if matches:
                        mcp_log(f'  File: {py_file.name}')
                        mcp_log(f'    Found {len(matches)} @mcp.tool functions: {matches}')
                        
                        # Dynamically load module and get functions
                        try:
                            spec = importlib.util.spec_from_file_location(
                                py_file.stem,
                                str(py_file)  # Convert to string to handle Path objects properly
                            )
                            if spec and spec.loader:
                                module = importlib.util.module_from_spec(spec)
                                
                                # Register module in sys.modules BEFORE executing
                                # This allows imports within the module to resolve correctly
                                sys.modules[py_file.stem] = module
                                
                                # ENSURE Tools.ue_interaction_tool is in sys.modules
                                # This MUST be done before executing user tool module
                                # as user tools often import from Tools.ue_interaction_tool
                                if 'Tools.ue_interaction_tool' not in sys.modules:
                                    current_module = sys.modules.get(__name__)
                                    if current_module:
                                        sys.modules['Tools.ue_interaction_tool'] = current_module
                                        mcp_log(f'DEBUG: Registered current module as Tools.ue_interaction_tool')
                                
                                # Set __package__ to allow relative imports to work
                                # This is needed when the module does "from .something import"
                                module.__package__ = 'Tools'
                                
                                # Inject MCP server instance into module's namespace
                                # This allows @mcp.tool decorator to work
                                setattr(module, 'mcp', mcp)
                                
                                try:
                                    spec.loader.exec_module(module)
                                except ImportError as e:
                                    # ImportError might be caused by missing module
                                    # Log it and continue
                                    if "attempted relative import" in str(e):
                                        mcp_log(f'Note: {py_file.name} uses relative imports. Make sure dependencies are in sys.path.')
                                    # Remove from sys.modules if load failed
                                    sys.modules.pop(py_file.stem, None)
                                    raise
                                except Exception as e:
                                    # Remove from sys.modules if load failed
                                    sys.modules.pop(py_file.stem, None)
                                    raise
                                
                                # Register each tool function
                                for func_name in matches:
                                    if hasattr(module, func_name):
                                        func = getattr(module, func_name)
                                        tool_key = '{}/{}/{}'.format(dir_name, py_file.stem, func_name)
                                        REGISTERED_USER_TOOLS[tool_key] = func
                                        mcp_log(f'      ✅ Registered: {func_name}')
                                        registered_count += 1
                                
                        except Exception as e:
                            mcp_log(f'⚠️  Error loading module from {py_file.name}: {e}')
                            import traceback
                            tb = traceback.format_exc()
                            mcp_log(f'Traceback: {tb}')
                
                except Exception as e:
                    mcp_log(f'⚠️  Error processing {py_file}: {e}')
                    # Log full traceback for debugging
                    import traceback
                    tb = traceback.format_exc()
                    mcp_log(f'Full traceback: {tb}')
        
        mcp_log(f'{"="*80}')
        if registered_count > 0:
            mcp_log(f'✅ Successfully registered {registered_count} user tool function(s)')
        else:
            mcp_log(f'ℹ️  No user tool functions found to register')
        mcp_log(f'{"="*80}')

        # Auto-register simple commands from C++
        _register_simple_commands_from_ue(mcp, registered_count)

    except Exception as e:
        mcp_log(f'❌ Error registering user tool directories: {e}')
        mcp_log('='*80)


def _register_simple_commands_from_ue(mcp: Any, already_registered: int) -> None:
    """Auto-register simple commands from C++ using get_simple_commands.

    Fetches bIsSimple=true commands from UE and creates Tool wrappers automatically.
    Skips commands whose names are already registered (duplicate check).

    Args:
        mcp: FastMCP server instance
        already_registered: count of already registered tools (for logging)
    """
    global REGISTERED_SIMPLE_COMMANDS

    mcp_log('='*80)
    mcp_log('🔄 Auto-registering simple commands from C++...')

    try:
        success = ue_send_command('Application_get_simple_commands')
        if not success:
            mcp_log('❌ Failed to send get_simple_commands to UE')
            mcp_log('='*80)
            return

        response_data = ue_receive_response()
        if not response_data or 'error' in response_data:
            error_msg = response_data.get('error', {}).get('message', 'Unknown') if response_data else 'No response'
            mcp_log(f'❌ get_simple_commands failed: {error_msg}')
            mcp_log('='*80)
            return

        commands = response_data.get('result', {}).get('commands', [])
        if not commands:
            mcp_log('ℹ️  No simple commands found from C++')
            mcp_log('='*80)
            return

        mcp_log(f'Found {len(commands)} simple command(s) from C++')

        registered_count = 0
        skipped_count = 0

        for cmd in commands:
            cmd_name = cmd.get('name', '')
            cmd_desc = cmd.get('description', '')

            if not cmd_name:
                continue

            # Duplicate check
            if cmd_name in REGISTERED_SIMPLE_COMMANDS:
                mcp_log(f'  ⏭️  Skipped (already registered): {cmd_name}')
                skipped_count += 1
                continue

            # Check if tool name already exists in MCP server
            existing_tools = {t.name for t in mcp._tool_manager.list_tools()} if hasattr(mcp, '_tool_manager') else set()
            if cmd_name in existing_tools:
                mcp_log(f'  ⏭️  Skipped (tool already exists): {cmd_name}')
                skipped_count += 1
                continue

            try:
                def create_simple_wrapper(command: str, description: str):
                    def command_wrapper(options: Optional[dict] = None) -> Dict[str, Any]:
                        """Execute a simple command from C++."""
                        try:
                            params = get_mcp_params() or {}
                            result = ue_execute_simple_command(command, params)
                            mcp_log(f'Tool: Executed simple command: {command}')
                            return {
                                'jsonrpc': '2.0',
                                'result': {
                                    'command': command,
                                    'params': params,
                                    'success': True,
                                    'response': result
                                }
                            }
                        except Exception as e:
                            mcp_log(f'Tool: Error executing simple command {command}: {e}')
                            return {
                                'jsonrpc': '2.0',
                                'error': {
                                    'code': -32603,
                                    'message': f'Failed to execute command {command}: {str(e)}'
                                }
                            }

                    command_wrapper.__name__ = command
                    command_wrapper.__doc__ = description
                    return mcp.tool(command_wrapper)

                create_simple_wrapper(cmd_name, cmd_desc)
                REGISTERED_SIMPLE_COMMANDS[cmd_name] = 'auto'
                mcp_log(f'  ✅ Auto-registered: {cmd_name}')
                registered_count += 1
            except Exception as e:
                mcp_log(f'  ⚠️  Error registering {cmd_name}: {e}')

        mcp_log(f'{"="*80}')
        mcp_log(f'✅ Auto-registered {registered_count} simple command(s), skipped {skipped_count}')
        mcp_log(f'{"="*80}')

    except Exception as e:
        mcp_log(f'❌ Error auto-registering simple commands: {e}')
        mcp_log('='*80)


def unregister_user_tool_directories() -> Dict[str, Any]:
    """Unregister all user tool directories.
    
    Called when UE connection is lost.
    
    Returns:
        JSON-RPC 2.0 format response
    """
    global REGISTERED_USER_TOOLS, REGISTERED_SIMPLE_COMMANDS
    
    mcp_log('='*80)
    mcp_log('🔄 Unregistering user tool directories from Unreal Engine...')
    
    try:
        total_count = len(REGISTERED_USER_TOOLS) + len(REGISTERED_SIMPLE_COMMANDS)
        
        if total_count == 0:
            mcp_log('ℹ️  No user tools currently registered')
            mcp_log('='*80)
            return {
                "jsonrpc": "2.0",
                "result": {
                    "count": 0,
                    "unregistered_tools": [],
                    "unregistered_commands": [],
                    "message": "No user tools registered"
                }
            }
        
        count = len(REGISTERED_USER_TOOLS)
        unregistered_tools = list(REGISTERED_USER_TOOLS.keys())
        unregistered_commands = list(REGISTERED_SIMPLE_COMMANDS.keys())
        
        mcp_log(f'Found {count} registered user tool(s) and {len(unregistered_commands)} simple command(s) to unregister:')
        
        # Remove tools from FastMCP server
        removed_count = 0
        if MCP_SERVER:
            for tool_key in unregistered_tools:
                func_name = tool_key.rsplit('/', 1)[-1]
                try:
                    MCP_SERVER.remove_tool(func_name)
                    mcp_log(f'  ✓ Removed tool from MCP: {func_name}')
                    removed_count += 1
                except Exception as e:
                    mcp_log(f'  ⚠️  Failed to remove tool {func_name}: {e}')

            for cmd_name in unregistered_commands:
                try:
                    MCP_SERVER.remove_tool(cmd_name)
                    mcp_log(f'  ✓ Removed simple command from MCP: {cmd_name}')
                    removed_count += 1
                except Exception as e:
                    mcp_log(f'  ⚠️  Failed to remove command {cmd_name}: {e}')
        else:
            mcp_log('  ⚠️  MCP_SERVER not available, clearing tracking only')

        REGISTERED_USER_TOOLS.clear()
        REGISTERED_SIMPLE_COMMANDS.clear()
        
        mcp_log(f'✅ Successfully unregistered {count} user tool functions and {len(unregistered_commands)} simple commands')
        mcp_log('='*80)
        
        return {
            "jsonrpc": "2.0",
            "result": {
                "count": total_count,
                "unregistered_tools": unregistered_tools,
                "unregistered_commands": unregistered_commands,
                "message": f"✅ Unregistered {count} user tool functions and {len(unregistered_commands)} simple commands"
            }
        }
    
    except Exception as e:
        mcp_log(f'❌ Error unregistering user tool directories: {e}')
        mcp_log('='*80)
        return {
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": f"Error unregistering user tool directories: {str(e)}"
            }
        }


def register_tools(mcp) -> None:
    """Register UE interaction tools with MCP server.
    
    This function should only be called once per server instance.
    """
    global UE_TOOLS_REGISTERED, MCP_SERVER
    
    # Store mcp reference for dynamic user tool registration
    MCP_SERVER = mcp
    
    if UE_TOOLS_REGISTERED:
        mcp_log('UE tools already registered, skipping')
        return
    
    try:
        @mcp.tool
        def check_ue_listening() -> Dict[str, Any]:
            """Check if Unreal Engine is listening on the connection port."""
            mcp_log(f'Tool: check_ue_listening() called')
            listening = is_ue_listening()
            mcp_log(f'Tool: UE listening status = {listening}')
            return {
                "jsonrpc": "2.0",
                "result": {
                    "listening": listening,
                    "host": UE_HOST,
                    "port": UE_PORT,
                    "message": f'✅ UE is listening on {UE_HOST}:{UE_PORT}' if listening else f'❌ UE is not listening on {UE_HOST}:{UE_PORT}'
                }
            }
        
        @mcp.tool
        def check_ue_connection() -> Dict[str, Any]:
            """Check current connection status to Unreal Engine."""
            mcp_log(f'Tool: check_ue_connection() called')
            connected = is_ue_connected()
            listening = is_ue_listening()
            mcp_log(f'Tool: UE connection status = {connected}, listening = {listening}')
            
            if connected:
                status_display = """
🔗 **CONNECTED**
================================
✅ Successfully connected to Unreal Engine
- Host: 127.0.0.1
- Port: 27777
- Status: Active
"""
            elif listening:
                status_display = """
📡 **LISTENING (Not Connected)**
================================
⚠️ Unreal Engine is listening but not connected yet
- Host: 127.0.0.1
- Port: 27777
- Status: Waiting for connection...
"""
            else:
                status_display = """
❌ **OFFLINE**
================================
Unreal Engine is not running or not listening
- Host: 127.0.0.1
- Port: 27777
- Status: Offline
"""
            
            result = {
                "jsonrpc": "2.0",
                "result": {
                    "connected": connected,
                    "listening": listening,
                    "host": UE_HOST,
                    "port": UE_PORT,
                    "connection_status": 'CONNECTED' if connected else ('LISTENING' if listening else 'OFFLINE'),
                    "display": status_display,
                    "message": f'✅ Connected to UE' if connected else (f'⚠️  UE is listening but not connected' if listening else f'❌ UE is offline')
                }
            }
            
            # Include latest status change if available
            if LAST_STATUS_CHANGE:
                result['result']['status_change'] = LAST_STATUS_CHANGE
            
            return result
        
        @mcp.tool
        def list_ue_instances() -> Dict[str, Any]:
            """List all available connected Unreal Engine instances.
            
            Shows all Unreal Engine instances currently running and listening on ports 27777-27787.
            Displays which instance is currently active and which are available to connect to.
            
            Use this to see all available Unreal Engine engines before switching instances.
            
            Returns:
                List of active instances with their ports and current status
            """
            mcp_log(f'Tool: list_ue_instances() called')
            available_ports = find_available_ue_ports()
            
            # Check if any instances are available
            if not available_ports:
                mcp_log('Tool: No UE instances found')
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": 1,
                        "message": "❌ No Unreal Engine instances detected. Please start Unreal Engine before using this tool."
                    }
                }
            
            instances_list = []
            for port in available_ports:
                instances_list.append({
                    "port": port,
                    "host": UE_HOST,
                    "current": (port == UE_PORT),
                    "status": "🔗 Current" if (port == UE_PORT) else "✅ Available"
                })
            
            mcp_log(f'Tool: Found {len(available_ports)} available UE instance(s)')
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "total_instances": len(available_ports),
                    "current_port": UE_PORT,
                    "instances": instances_list,
                    "message": f"Found {len(available_ports)} active UE instance(s). Current: Port {UE_PORT}"
                }
            }
        
        @mcp.tool
        def switch_ue_instance() -> Dict[str, Any]:
            """Switch connection to a different Unreal Engine instance.
            
            Changes the MCP server's connection from the current Unreal Engine instance
            to another instance running on the specified port (27777-27787).
            
            Automatically disconnects from the current instance and connects to the new one.
            
            Expects params (via get_mcp_params()):
                port: Port number of the target Unreal Engine instance (27777-27787)
            
            Returns:
                Success/error message with new port information
            """
            global UE_PORT
            
            params = get_mcp_params()
            port = params.get('port')
            
            # Validate port is provided and is int
            if port is None:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": f"❌ Port parameter is required"
                    }
                }
            
            try:
                port = int(port)
            except (ValueError, TypeError):
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": f"❌ Port must be a number, got {port}"
                    }
                }
            
            mcp_log(f'Tool: switch_ue_instance({port}) called')
            
            # Validate port range
            if port < UE_PORT_START or port > UE_PORT_END:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": f"❌ Invalid port {port}. Port must be between {UE_PORT_START} and {UE_PORT_END}."
                    }
                }
            
            # Check if port is available
            available_ports = find_available_ue_ports()
            if not available_ports:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": 2,
                        "message": "❌ No Unreal Engine instances detected. Please start Unreal Engine on port(s) 27777-27787 before switching."
                    }
                }
            
            if port not in available_ports:
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": 3,
                        "message": f"❌ No UE instance listening on port {port}. Available ports: {available_ports}"
                    }
                }
            
            prev_port = UE_PORT
            
            # Disconnect from current port if connected
            if is_ue_connected():
                ue_disconnect()
                time.sleep(0.3)  # Brief pause for clean disconnect
            
            # Update port and connect to new port
            UE_PORT = port
            mcp_log(f'Tool: Switched UE port from {prev_port} to {port}')
            
            if ue_connect():
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "success": True,
                        "previous_port": prev_port,
                        "current_port": port,
                        "message": f"✅ Successfully switched to UE instance on port {port}"
                    }
                }
            else:
                # Restore previous port since new connection failed
                UE_PORT = prev_port
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": 4,
                        "message": f"❌ Failed to connect to UE instance on port {port}. Please verify the instance is running."
                    }
                }
        
        @mcp.tool
        def enable_auto_reconnect() -> Dict[str, Any]:
            """Enable automatic reconnection to UE.
            
            WARNING: Auto-reconnect spawns a background thread that may interfere
            with stdio-based MCP communication. Use with caution.
            """
            mcp_log(f'Tool: enable_auto_reconnect() called')
            try:
                start_auto_reconnect()
                mcp_log(f'Tool: Auto-reconnect enabled successfully')
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "message": '✅ Auto-reconnect enabled (WARNING: may interfere with MCP stdio)'
                    }
                }
            except Exception as e:
                mcp_log(f'Tool: Error enabling auto-reconnect: {e}')
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Error enabling auto-reconnect: {str(e)}"
                    }
                }
        
        @mcp.tool
        def disable_auto_reconnect() -> Dict[str, Any]:
            """Disable automatic reconnection to UE."""
            mcp_log(f'Tool: disable_auto_reconnect() called')
            try:
                stop_auto_reconnect()
                mcp_log(f'Tool: Auto-reconnect disabled successfully')
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "message": '✅ Auto-reconnect disabled'
                    }
                }
            except Exception as e:
                mcp_log(f'Tool: Error disabling auto-reconnect: {e}')
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Error disabling auto-reconnect: {str(e)}"
                    }
                }
        
        @mcp.tool
        def reconnect_ue() -> Dict[str, Any]:
            """Reconnect to Unreal Engine (disconnect and reconnect).
            
            Useful for testing connection stability or resetting the connection state.
            """
            mcp_log(f'Tool: reconnect_ue() called')
            try:
                success = ue_reconnect()
                if success:
                    mcp_log(f'Tool: Reconnection successful')
                    return {
                        "jsonrpc": "2.0",
                        "result": {
                            "success": True,
                            "message": '🔗 Successfully reconnected to Unreal Engine'
                        }
                    }
                else:
                    mcp_log(f'Tool: Reconnection failed')
                    return {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32603,
                            "message": "Failed to reconnect to Unreal Engine"
                        }
                    }
            except Exception as e:
                mcp_log(f'Tool: Error during reconnection: {e}')
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"Error during reconnection: {str(e)}"
                    }
                }
        
        @mcp.tool
        def set_log_level_tool(level: Optional[str] = None) -> Dict[str, Any]:
            """Set or show available log levels.
            
            If no level is specified, shows available log levels for user selection.
            If level is specified, changes log level immediately.
            
            Args:
                level: Log level to set (ERROR, WARNING, INFO, DEBUG) - optional
            
            Returns:
                Current/new log level and available levels, or list of available levels for selection
            """
            mcp_log(f'Tool: set_log_level_tool(level={level}) called')
            
            # If no level specified, show available levels for selection
            if level is None:
                available = get_available_log_levels()
                current = get_current_log_level()
                mcp_log(f'Tool: Showing available log levels. Current: {current}')
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "available_levels": available,
                        "current_level": current,
                        "message": f"Current log level: {current}. Available levels: {', '.join(available)}. Please select a level to continue."
                    }
                }
            
            # Level specified - change it
            level = level.strip().upper()
            available = get_available_log_levels()
            
            if level not in available:
                mcp_log(f'Tool: Invalid log level requested: {level}')
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32602,
                        "message": f"❌ Invalid log level '{level}'. Available levels: {', '.join(available)}"
                    }
                }
            
            # Attempt to set the log level
            if set_log_level(level):
                mcp_log(f'✅ Log level changed to {level}')
                return {
                    "jsonrpc": "2.0",
                    "result": {
                        "success": True,
                        "previous_level": get_current_log_level(),
                        "new_level": level,
                        "message": f"✅ Log level successfully changed to {level}"
                    }
                }
            else:
                mcp_log(f'Tool: Failed to set log level to {level}')
                return {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": f"❌ Failed to change log level to {level}. Please try again."
                    }
                }
        
        UE_TOOLS_REGISTERED = True
        
        # Start auto-reconnect service to monitor connection status
        mcp_log('Starting auto-reconnect service for connection monitoring...')
        start_auto_reconnect()
    
    except Exception as e:
        mcp_log(f'Error registering UE tools: {e}')
        
# ============================================================================
# REGISTER THIS MODULE IN sys.modules FOR USER TOOL IMPORTS
# ============================================================================
# When user tools are dynamically loaded, they may try to import from this module
# using "from Tools.ue_interaction_tool import ...". We need to ensure this module
# is available in sys.modules so those imports succeed.
if __name__ != '__main__':
    # Only register if we're being imported (not run directly)
    import sys as _sys_for_registration
    _current_module = _sys_for_registration.modules[__name__]
    
    # Register under both possible import paths
    if 'Tools.ue_interaction_tool' not in _sys_for_registration.modules:
        _sys_for_registration.modules['Tools.ue_interaction_tool'] = _current_module
    if 'ue_interaction_tool' not in _sys_for_registration.modules:
        _sys_for_registration.modules['ue_interaction_tool'] = _current_module
    
    # Clean up temporary variable
    del _sys_for_registration, _current_module


