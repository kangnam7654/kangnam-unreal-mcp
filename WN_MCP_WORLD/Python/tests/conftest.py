"""Shared fixtures and helpers for WN_MCP_WORLD tests."""

import sys
import os
import asyncio
import pytest
from unittest.mock import patch

# Add parent dir to path so test files can import tools package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Add PyMCP dir to path so tool modules can import Tools package
_pymcp_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "WN_MCP", "PyMCP"))
if _pymcp_dir not in sys.path:
    sys.path.insert(0, _pymcp_dir)

from fastmcp import FastMCP
from tools import register_all_tools

mcp = FastMCP("WN_MCP_WORLD_Test")
register_all_tools(mcp)

# Resolve the actual ue_interaction_tool module used by tool modules
from Tools import ue_interaction_tool


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
def mock_ue_execute():
    """Mock ue_send_command + ue_receive_response to avoid real UE connection.

    Patches ue_interaction_tool module attributes so all tool modules see the mock.
    Yields mock_send for call assertion compatibility.
    """
    with patch.object(ue_interaction_tool, "ue_send_command") as mock_send, \
         patch.object(ue_interaction_tool, "ue_receive_response") as mock_recv:
        mock_send.return_value = True
        mock_recv.return_value = {"jsonrpc": "2.0", "result": {}}

        def set_return_value(val):
            mock_recv.return_value = {"jsonrpc": "2.0", "result": val}

        mock_send.set_result = set_return_value
        mock_send._mock_recv = mock_recv
        yield mock_send, mock_recv


@pytest.fixture
def mock_ue_connection_error():
    """Mock ue_send_command to return False (not connected)."""
    with patch.object(ue_interaction_tool, "ue_send_command") as mock_send, \
         patch.object(ue_interaction_tool, "ue_receive_response") as mock_recv:
        mock_send.return_value = False
        mock_recv.return_value = None
        yield mock_send


@pytest.fixture
def mock_ue_runtime_error():
    """Mock ue_receive_response to return an error response."""
    with patch.object(ue_interaction_tool, "ue_send_command") as mock_send, \
         patch.object(ue_interaction_tool, "ue_receive_response") as mock_recv:
        mock_send.return_value = True
        mock_recv.return_value = {
            "jsonrpc": "2.0",
            "error": {"code": -32001, "message": "Command execution failed"},
        }
        yield mock_send, mock_recv
