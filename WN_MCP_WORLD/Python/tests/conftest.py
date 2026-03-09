"""Shared fixtures for WN_MCP_WORLD tests."""

import sys
import os
import pytest
from unittest.mock import patch

# Ensure parent dir is on path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture
def mock_ue_execute():
    """Mock _ue_execute to avoid real UE connection.

    Patches the single source in ue_connection module.
    All tool modules import from there, so this covers everything.
    """
    with patch("tools.ue_connection._ue_execute") as mock:
        mock.return_value = {}
        yield mock


@pytest.fixture
def mock_ue_connection_error():
    """Mock _ue_execute to raise ConnectionError."""
    with patch("tools.ue_connection._ue_execute") as mock:
        mock.side_effect = ConnectionError("Cannot connect to UE at 127.0.0.1:27777")
        yield mock


@pytest.fixture
def mock_ue_runtime_error():
    """Mock _ue_execute to raise RuntimeError (UE error response)."""
    with patch("tools.ue_connection._ue_execute") as mock:
        mock.side_effect = RuntimeError("UE error [-32001]: Command execution failed")
        yield mock
