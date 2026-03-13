"""
WN_MCP Tools Package
Provides tools for Unreal Engine interaction, logging, and agent communication.
"""

# Import required modules (params first to avoid circular dependencies)
from . import params
from . import log_tool
from . import agent_interaction_tool

# Export params module functions at package level
from .params import get_mcp_params, _set_mcp_params

# Lazy import ue_interaction_tool to avoid circular dependencies
def __getattr__(name: str):
    """Dynamic attribute access to lazy-load ue_interaction_tool functions."""
    # List of functions that should be lazily imported from ue_interaction_tool
    ue_tool_functions = {
        'LAST_STATUS_CHANGE',
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
    }
    
    if name in ue_tool_functions:
        # Lazy import ue_interaction_tool only when needed
        from . import ue_interaction_tool
        return getattr(ue_interaction_tool, name)
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    'params',
    'log_tool',
    'agent_interaction_tool',
    'get_mcp_params',
    '_set_mcp_params',
]
