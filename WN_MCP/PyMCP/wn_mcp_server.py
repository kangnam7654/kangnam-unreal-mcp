import os
import sys
import time
import threading
import signal
import atexit
from datetime import datetime
from typing import AsyncIterator, Dict, Any
from fastmcp import FastMCP
from fastmcp.server.lifespan import lifespan
from pathlib import Path

# Configure the Tools package in sys.path (BEFORE any Tools imports)
_project_root = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# Import all Tools functions directly (no lazy import)
from Tools.log_tool import log_info as _log, initialize_logging, close_logging
from Tools.params import get_mcp_params, _set_mcp_params, enable_mcp_params_capture
from Tools.ue_interaction_tool import (
    ue_disconnect, is_ue_connected, is_ue_listening,
    start_auto_reconnect, stop_auto_reconnect,
    register_connection_callback, register_notification_callback, register_ue_connected_callback,
    register_ue_disconnected_callback, register_user_tool_directories, register_tools as register_ue_tools,
    LAST_STATUS_CHANGE,
)
from Tools.agent_interaction_tool import register_tools as register_agent_tools

# Make _set_mcp_params and get_mcp_params available at module level for convenience
setattr(sys.modules['__main__'], '_set_mcp_params', _set_mcp_params)
setattr(sys.modules['__main__'], 'get_mcp_params', get_mcp_params)

# Lifespan manager
@lifespan
async def server_lifespan(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
    # Initialize logging first
    initialize_logging()
    _log('MCP Server starting up')
    
    try:
        # 1. Register static MCP tools (once at startup)
        _log('Registering static MCP tools...')
        _register_tools(server)
        _log('✅ Static MCP tools registered')
        
        # 2. Register callback for user tool discovery when UE connects
        def on_ue_connected():
            """Called when UE connection is established."""
            _log('UE connected - discovering and registering user tools from Unreal Engine...')
            try:
                register_user_tool_directories(server)
            except Exception as e:
                _log(f'ERROR in user tool registration: {type(e).__name__}: {e}')
                import traceback
                _log(f'Traceback: {traceback.format_exc()}')
        
        register_ue_connected_callback(on_ue_connected)
        # Callback registration is a DEBUG-level detail
        from Tools.log_tool import log_debug
        log_debug('UE connection callback registered')
        
        # 3. Check initial UE status and start monitoring
        listening = is_ue_listening()
        connected = is_ue_connected()
        _log(f'UE Status - Listening: {listening}, Connected: {connected}')
        
        # 4. Start automatic UE connection management
        start_auto_reconnect()
        _log('Auto-reconnect service activated')
        
        yield {}  # Server is running
    except Exception as e:
        _log(f'Error during server operation: {e}')
    finally:
        try:
            stop_auto_reconnect()
            ue_disconnect()
            _log('WN_MCP_Server is shutting down.')
        except Exception as e:
            _log(f'Error during shutdown: {e}')
        finally:
            close_logging()


# Create MCP instance at module level (only once per process)
mcp = FastMCP(
    'WN_MCP_Server',
    lifespan=server_lifespan)

# Enable automatic parameter capture for all @mcp.tool decorated functions
enable_mcp_params_capture(mcp)


# Register all tools (called after UE connection is established)
def _register_tools(mcp: FastMCP):
    """Register all MCP tools after UE connection is established.
    
    Args:
        mcp: FastMCP server instance
    """
    try:
        # Register UE interaction tools
        register_ue_tools(mcp)
        
        # Register Agent interaction tools
        register_agent_tools(mcp)
        
        # Create notification display function
        def show_ue_status_notification(title: str, message: str, level: str):
            """Internal notification handler for UE connection status."""
            try:
                pass  # Status is already logged via _notify_connection_status()
            except Exception as e:
                _log(f'Error in notification handler: {e}')
        
        # Register the notification callback with UE connection system
        register_notification_callback(show_ue_status_notification)
        
    except Exception as e:
        _log(f'Error registering tools: {e}')

    # Add resource for connection status
    @mcp.resource('ue://status')
    def ue_status() -> str:
        """Get current Unreal Engine connection status."""
        connected = is_ue_connected()
        listening = is_ue_listening()
        status_text = 'CONNECTED' if connected else ('LISTENING' if listening else 'OFFLINE')
        
        return f"""# Unreal Engine Status

**Current Status:** `{status_text}`

- Connected: {'✅ Yes' if connected else '❌ No'}
- Listening: {'✅ Yes' if listening else '❌ No'}
- Host: 127.0.0.1
- Port: 27777

---
*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    
    # Add prompt for Agent status awareness
    try:
        @mcp.prompt
        def check_engine_status() -> str:
            """Check current Unreal Engine connection status.
            
            Use this prompt to be aware of the engine's connection state before performing operations.
            """
            if LAST_STATUS_CHANGE:
                change = LAST_STATUS_CHANGE
                status_info = f"""**Unreal Engine Current Status:**
- Status: {change['status']}
- {'✅ Connected' if change['connected'] else '❌ Disconnected'}
- Message: {change['message']}

*Use the `get_engine_status_update()` tool anytime to get the latest status.*
"""
            else:
                # Fallback: check current status
                connected = is_ue_connected()
                listening = is_ue_listening()
                status = 'CONNECTED' if connected else ('LISTENING' if listening else 'OFFLINE')
                status_info = f"""**Unreal Engine Current Status:** {status}
- Connected: {'✅ Yes' if connected else '❌ No'}
- Listening: {'✅ Yes' if listening else '❌ No'}

*Use the `get_engine_status_update()` tool anytime to get the latest status.*
"""
            
            return status_info
    except Exception as e:
        _log(f'Error registering prompt: {e}')
    
    print('All MCP tools registered successfully')


# MCP Server instance
# Note: _register_tools() will be called after successful UE connection in lifespan
# Do NOT call _register_tools() at module load time
def _cleanup_and_exit(signum=None, frame=None):
    """Handle graceful shutdown and cleanup."""
    try:
        _log('Received shutdown signal - cleaning up resources...')
    except Exception:
        pass
    
    try:
        stop_auto_reconnect()
    except Exception as e:
        try:
            _log(f'Error stopping auto-reconnect: {e}')
        except Exception:
            pass
    
    try:
        ue_disconnect()
    except Exception as e:
        try:
            _log(f'Error disconnecting from UE: {e}')
        except Exception:
            pass
    
    try:
        close_logging()
    except Exception:
        pass
    
    sys.exit(0)

# Register atexit handler to ensure cleanup on any exit
atexit.register(_cleanup_and_exit)

if __name__ == '__main__':
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, _cleanup_and_exit)
    signal.signal(signal.SIGTERM, _cleanup_and_exit)
    
    try:
        mcp.run(transport='stdio')
    except KeyboardInterrupt:
        _cleanup_and_exit()
    except Exception as e:
        try:
            _log(f'Unexpected error: {e}')
        except Exception:
            pass
        finally:
            _cleanup_and_exit()
