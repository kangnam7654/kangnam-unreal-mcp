"""Shared fixtures for WN_MCP_WORLD tests."""

import json
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_ue_execute():
    """Mock _ue_execute to avoid real UE connection.

    Usage:
        def test_something(mock_ue_execute):
            mock_ue_execute.return_value = {"key": "value"}
            result = some_tool()
            mock_ue_execute.assert_called_once_with("command_name", {"param": "value"})
    """
    with patch("mcp_server._ue_execute") as mock:
        mock.return_value = {}
        yield mock


@pytest.fixture
def mock_ue_connection_error():
    """Mock _ue_execute to raise ConnectionError."""
    with patch("mcp_server._ue_execute") as mock:
        mock.side_effect = ConnectionError("Cannot connect to UE at 127.0.0.1:27777")
        yield mock


@pytest.fixture
def mock_ue_runtime_error():
    """Mock _ue_execute to raise RuntimeError (UE error response)."""
    with patch("mcp_server._ue_execute") as mock:
        mock.side_effect = RuntimeError("UE error [-32001]: Command execution failed")
        yield mock
