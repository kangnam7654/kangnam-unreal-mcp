"""Unit tests for simple_commands module.

Tests SimpleCommand discovery and dynamic MCP tool registration.
UE connection is mocked — no running editor required.
"""
import json
import pytest
from unittest.mock import MagicMock, patch

from kn_mcp.tools.simple_commands import (
    get_simple_commands,
    register_simple_commands,
    _make_simple_tool,
)


# =============================================================================
# get_simple_commands
# =============================================================================


class TestGetSimpleCommands:
    def test_returns_commands_on_success(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {
            "commands": [
                {"name": "Test_get_hello_message", "description": "Get hello message from UE"},
            ]
        }
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = get_simple_commands()
        assert len(result) == 1
        assert result[0]["name"] == "Test_get_hello_message"
        mock_conn.send_command.assert_called_once_with("Application_get_simple_commands", {})

    def test_returns_empty_on_no_connection(self):
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=None):
            result = get_simple_commands()
        assert result == []

    def test_returns_empty_on_error_response(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {"status": "error", "error": "not found"}
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = get_simple_commands()
        assert result == []

    def test_returns_empty_on_none_response(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = None
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = get_simple_commands()
        assert result == []

    def test_returns_empty_on_unexpected_format(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {"commands": "not_a_list"}
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = get_simple_commands()
        assert result == []

    def test_returns_multiple_commands(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {
            "commands": [
                {"name": "Test_cmd1", "description": "Desc 1"},
                {"name": "Test_cmd2", "description": "Desc 2"},
                {"name": "Other_cmd3", "description": "Desc 3"},
            ]
        }
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = get_simple_commands()
        assert len(result) == 3


# =============================================================================
# _make_simple_tool
# =============================================================================


class TestMakeSimpleTool:
    def test_tool_fn_has_correct_name_and_doc(self):
        fn = _make_simple_tool("Test_hello", "Say hello")
        assert fn.__name__ == "Test_hello"
        assert fn.__doc__ == "Say hello"

    def test_tool_fn_returns_json_on_success(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {"message": "Hello from UE"}
        fn = _make_simple_tool("Test_hello", "Say hello")
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = fn()
        parsed = json.loads(result)
        assert parsed["message"] == "Hello from UE"
        mock_conn.send_command.assert_called_once_with("Test_hello", {})

    def test_tool_fn_returns_error_when_no_connection(self):
        fn = _make_simple_tool("Test_hello", "Say hello")
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=None):
            result = fn()
        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "Not connected" in parsed["error"]

    def test_tool_fn_returns_error_when_no_response(self):
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = None
        fn = _make_simple_tool("Test_hello", "Say hello")
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            result = fn()
        parsed = json.loads(result)
        assert parsed["status"] == "error"
        assert "No response" in parsed["error"]


# =============================================================================
# register_simple_commands
# =============================================================================


class TestRegisterSimpleCommands:
    def test_registers_tools_on_server(self):
        mock_server = MagicMock()
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {
            "commands": [
                {"name": "Test_get_hello", "description": "Get hello"},
                {"name": "Test_get_world", "description": "Get world"},
            ]
        }
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            register_simple_commands(mock_server)
        assert mock_server.tool.call_count == 2
        # Verify tool function names
        registered_names = [call.args[0].__name__ for call in mock_server.tool.call_args_list]
        assert "Test_get_hello" in registered_names
        assert "Test_get_world" in registered_names

    def test_skips_when_no_commands(self):
        mock_server = MagicMock()
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=None):
            register_simple_commands(mock_server)
        mock_server.tool.assert_not_called()

    def test_skips_commands_with_empty_name(self):
        mock_server = MagicMock()
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {
            "commands": [
                {"name": "", "description": "Empty name"},
                {"name": "Test_valid", "description": "Valid"},
            ]
        }
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            register_simple_commands(mock_server)
        assert mock_server.tool.call_count == 1

    def test_handles_registration_error_gracefully(self):
        mock_server = MagicMock()
        mock_server.tool.side_effect = [Exception("registration failed"), None]
        mock_conn = MagicMock()
        mock_conn.send_command.return_value = {
            "commands": [
                {"name": "Test_bad", "description": "Will fail"},
                {"name": "Test_good", "description": "Will succeed"},
            ]
        }
        with patch("kn_mcp.tools.simple_commands.get_unreal_connection", return_value=mock_conn):
            register_simple_commands(mock_server)
        assert mock_server.tool.call_count == 2
