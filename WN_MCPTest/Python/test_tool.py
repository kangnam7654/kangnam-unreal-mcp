"""
WN_MCPTest test tool module.

Demonstrates how to use get_mcp_params() to access agent parameters
and interact with Unreal Engine through the MCP server.
"""

# Import functions directly from Tools package (no lazy imports)
from Tools import get_mcp_params
from Tools.ue_interaction_tool import ue_send_command, ue_receive_response

def register_simple_commands() -> list[dict]:
    """
    Register simple commands that can be executed on Unreal Engine.
    
    This function is auto-detected by the MCP server. Each command dict should contain:
    - 'name': str - The command name to execute on UE (e.g., 'get_hello_message')
    - 'description': str - Human-readable description for the Agent's LLM context
    
    Returns:
        list[dict]: List of SimpleCommand dicts with 'name' (str) and 'description' (str)
    """
    return [
        {
            'name': 'get_hello_message',
            'description': 'Retrieve a hello message from Unreal Engine'
        }
    ]

# Note: @mcp.tool decorator will be injected by the MCP server when registered
# We cannot import mcp here due to circular imports, so functions are decorated at registration time
@mcp.tool
def get_hello_message_array() -> dict:
    """
    Retrieve a Hello message array from Unreal Engine.
    
    Returns:
        dict: The JSON-RPC 2.0 response object from Unreal Engine
    """
    try:        
        params = get_mcp_params() or {}
        ue_send_command("get_hello_message_array", params)
        return ue_receive_response()
    except Exception as e:
        raise Exception(f"get_hello_message_array failed: {str(e)}")