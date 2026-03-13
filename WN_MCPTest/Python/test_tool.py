"""
WN_MCPTest test tool module.

Demonstrates how to use get_mcp_params() to access agent parameters
and interact with Unreal Engine through the MCP server.
"""

from Tools import get_mcp_params
from Tools import ue_interaction_tool as ue

_CATEGORY = "Test"

## get_hello_message is registered as WN_MCP_REGISTER_SIMPLE_COMMAND in C++
## PyMCP auto-registers it via _register_simple_commands_from_ue()

# @mcp.tool decorator is injected by PyMCP when this module is dynamically loaded
@mcp.tool
def get_hello_message_array() -> dict:
    """
    Retrieve a Hello message array from Unreal Engine.

    Returns:
        dict: The JSON-RPC 2.0 response object from Unreal Engine
    """
    try:
        params = get_mcp_params() or {}
        ue.ue_send_command("get_hello_message_array", params, category_name=_CATEGORY)
        return ue.ue_receive_response()
    except Exception as e:
        raise Exception(f"get_hello_message_array failed: {str(e)}")
