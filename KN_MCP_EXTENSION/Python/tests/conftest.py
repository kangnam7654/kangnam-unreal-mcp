"""Shared fixtures and helpers for KN_MCP_EXTENSION tests."""

import sys
import os
import asyncio
import pytest
from unittest.mock import patch

# Add parent dir to path so test files can import tools package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Add KN_MCP Python to path (ue_connection imports from kn_mcp.connection)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "KN_MCP", "Python"))

from fastmcp import FastMCP
from tools import register_all_tools

mcp = FastMCP("KN_MCP_EXTENSION_Test")
register_all_tools(mcp)


# =============================================================================
# Tool Invocation Helper
# =============================================================================

_tool_fn_cache: dict = {}


def call_tool(tool_name: str, **kwargs) -> str:
    """Call a registered MCP tool synchronously and return raw result string.

    Resolves the tool function on first call, then caches it.
    Used by unit tests (directly) and integration tests (via json.loads wrapper).
    """
    if tool_name not in _tool_fn_cache:
        async def _resolve():
            tool = await mcp.get_tool(tool_name)
            return tool.fn
        _tool_fn_cache[tool_name] = asyncio.run(_resolve())
    return _tool_fn_cache[tool_name](**kwargs)


# =============================================================================
# UE Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_ue_send_command():
    """Mock send_command() to avoid real UE connection.

    Patches the single source in ue_connection module.
    All tool modules import from there, so this covers everything.
    """
    with patch("ue_connection.send_command") as mock:
        mock.return_value = {}
        yield mock


@pytest.fixture
def mock_ue_connection_error():
    """Mock send_command() to return connection error dict."""
    with patch("ue_connection.send_command") as mock:
        mock.return_value = {"status": "error", "error": "Cannot connect to UE at 127.0.0.1:27777"}
        yield mock


@pytest.fixture
def mock_ue_runtime_error():
    """Mock send_command() to return UE error response dict."""
    with patch("ue_connection.send_command") as mock:
        mock.return_value = {"status": "error", "error": "Command execution failed", "code": -32001}
        yield mock
