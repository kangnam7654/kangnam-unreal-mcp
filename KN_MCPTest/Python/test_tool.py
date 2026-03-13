"""
KN_MCPTest test tool module.

Demonstrates extension plugin pattern:
- get_hello_message: Simple command (auto-registered by C++ KN_MCP_REGISTER_SIMPLE_COMMAND)
- get_hello_message_array: Regular command (Python tool calls C++ via connection)
"""
import json

from kn_mcp.connection import get_unreal_connection

_CATEGORY = "Test"


# @mcp.tool decorator is injected by PyMCP when this module is dynamically loaded
@mcp.tool()
def get_hello_message_array() -> str:
    """Retrieve a Hello message array from Unreal Engine.

    Returns:
        JSON string with array of hello messages from UE.
    """
    conn = get_unreal_connection()
    if conn is None:
        return json.dumps({"status": "error", "error": "Not connected to UE"})

    full_name = f"{_CATEGORY}_get_hello_message_array"
    result = conn.send_command(full_name, {})
    if result is None:
        return json.dumps({"status": "error", "error": "No response from UE"})

    return json.dumps(result, indent=2, ensure_ascii=False)
