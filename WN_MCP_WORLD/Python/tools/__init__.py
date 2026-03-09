"""WN_MCP_WORLD tools package.

Each module registers its tools via register_tools(mcp).
"""

from fastmcp import FastMCP

from . import actor_tools
from . import actor_component_tools
from . import blueprint_tools
from . import blueprint_component_tools
from . import property_tools


def register_all_tools(mcp: FastMCP):
    """Register all WORLD tools with the MCP server."""
    actor_tools.register_tools(mcp)
    actor_component_tools.register_tools(mcp)
    blueprint_tools.register_tools(mcp)
    blueprint_component_tools.register_tools(mcp)
    property_tools.register_tools(mcp)
