"""
WN_MCP_WORLD - MCP Server

FastMCP server exposing Actor, Blueprint, and Component CRUD commands as MCP tools.
LLM (Claude Code, Cursor, etc.) connects to this server via stdio,
and this server forwards commands to UE C++ plugin via TCP JSON-RPC 2.0.

Usage:
    # Run as MCP server (stdio transport - for LLM integration)
    uv run python mcp_server.py

    # Add to Claude Code MCP config (~/.claude/settings.json):
    {
        "mcpServers": {
            "ue-world": {
                "command": "uv",
                "args": ["run", "python", "mcp_server.py"],
                "cwd": "<path-to>/WN_MCP_WORLD/Python"
            }
        }
    }
"""

from fastmcp import FastMCP
from tools import register_all_tools


# =============================================================================
# MCP Server
# =============================================================================

mcp = FastMCP("WN_MCP_WORLD")
register_all_tools(mcp)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio", log_level="WARNING", show_banner=False)
