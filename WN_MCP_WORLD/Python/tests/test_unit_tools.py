"""Unit tests for MCP tools.

Tests tool parameter passing and response formatting.
UE connection is mocked — no running editor required.

Each tool module's register_tools() creates closures over _ue_execute.
We mock _ue_execute at the source (tools.ue_connection) and call tool
functions via FastMCP's async get_tool() API.
"""

import json
import sys
import os
import asyncio
import inspect
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_server import mcp


# =============================================================================
# Helpers
# =============================================================================

_tool_fn_cache: dict = {}


def call_tool(tool_name: str, **kwargs) -> str:
    """Call a registered MCP tool synchronously and return raw result string."""
    if tool_name not in _tool_fn_cache:
        async def _resolve():
            tool = await mcp.get_tool(tool_name)
            return tool.fn
        _tool_fn_cache[tool_name] = asyncio.run(_resolve())
    return _tool_fn_cache[tool_name](**kwargs)


# =============================================================================
# Actor Tools
# =============================================================================


class TestGetActorsInLevel:
    def test_calls_correct_command(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "actors": []}
        call_tool("get_actors_in_level")
        mock_ue_execute.assert_called_once_with("get_actors_in_level")

    def test_returns_json_string(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 1, "actors": [{"name": "Cube"}]}
        result = call_tool("get_actors_in_level")
        parsed = json.loads(result)
        assert parsed["count"] == 1


class TestFindActorsByName:
    def test_passes_search_text(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "actors": []}
        call_tool("find_actors_by_name", search_text="Cube")
        mock_ue_execute.assert_called_once_with(
            "find_actors_by_name", {"search_text": "Cube"}
        )


class TestSpawnActor:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("spawn_actor", type="StaticMeshActor", name="MyCube")
        mock_ue_execute.assert_called_once_with(
            "spawn_actor", {"type": "StaticMeshActor", "name": "MyCube"}
        )

    def test_with_all_optional_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("spawn_actor",
            type="PointLight", name="MyLight",
            location=[1.0, 2.0, 3.0],
            rotation=[0.0, 90.0, 0.0],
            scale=[2.0, 2.0, 2.0],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["location"] == [1.0, 2.0, 3.0]
        assert params["rotation"] == [0.0, 90.0, 0.0]
        assert params["scale"] == [2.0, 2.0, 2.0]

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("spawn_actor", type="Actor", name="A", location=[0, 0, 0])
        params = mock_ue_execute.call_args[0][1]
        assert "location" in params
        assert "rotation" not in params
        assert "scale" not in params


class TestDeleteActor:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("delete_actor", name="MyCube")
        mock_ue_execute.assert_called_once_with("delete_actor", {"name": "MyCube"})


class TestSetActorTransform:
    def test_name_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_actor_transform", name="MyCube")
        params = mock_ue_execute.call_args[0][1]
        assert params == {"name": "MyCube"}

    def test_partial_transform(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_actor_transform", name="MyCube", location=[10, 20, 30])
        params = mock_ue_execute.call_args[0][1]
        assert params["location"] == [10, 20, 30]
        assert "rotation" not in params


class TestReadActorContent:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "Cube", "class": "StaticMeshActor"}
        call_tool("read_actor_content", name="Cube")
        mock_ue_execute.assert_called_once_with("read_actor_content", {"name": "Cube"})


# =============================================================================
# Actor Component Tools
# =============================================================================


class TestAddComponentToActor:
    def test_required_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_component_to_actor",
            name="MyCube", component_class="PointLightComponent",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["name"] == "MyCube"
        assert params["component_class"] == "PointLightComponent"
        assert "component_name" not in params

    def test_with_component_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_component_to_actor",
            name="MyCube", component_class="PointLightComponent",
            component_name="MyLight",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["component_name"] == "MyLight"


class TestRemoveComponentFromActor:
    def test_passes_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("remove_component_from_actor",
            name="MyCube", component_name="MyLight",
        )
        mock_ue_execute.assert_called_once_with(
            "remove_component_from_actor",
            {"name": "MyCube", "component_name": "MyLight"},
        )


class TestReadComponentsFromActor:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"actor_name": "Cube", "count": 0, "components": []}
        call_tool("read_components_from_actor", name="Cube")
        mock_ue_execute.assert_called_once_with(
            "read_components_from_actor", {"name": "Cube"}
        )


# =============================================================================
# Blueprint Tools
# =============================================================================


class TestGetBlueprints:
    def test_default_no_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        call_tool("get_blueprints")
        mock_ue_execute.assert_called_once_with("get_blueprints", {})

    def test_with_search_path(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        call_tool("get_blueprints", search_path="/Game/Maps/")
        mock_ue_execute.assert_called_once_with(
            "get_blueprints", {"search_path": "/Game/Maps/"}
        )


class TestFindBlueprintsByName:
    def test_passes_search_text(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        call_tool("find_blueprints_by_name", search_text="Player")
        mock_ue_execute.assert_called_once_with(
            "find_blueprints_by_name", {"search_text": "Player"}
        )


class TestCreateBlueprint:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP", "path": "/Game/Blueprints/MyBP"}
        call_tool("create_blueprint", name="MyBP")
        mock_ue_execute.assert_called_once_with("create_blueprint", {"name": "MyBP"})

    def test_with_parent_class(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP"}
        call_tool("create_blueprint", name="MyBP", parent_class="Pawn")
        params = mock_ue_execute.call_args[0][1]
        assert params["parent_class"] == "Pawn"


class TestReadBlueprintContent:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        call_tool("read_blueprint_content", blueprint_path="/Game/Blueprints/MyBP")
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_path"] == "/Game/Blueprints/MyBP"

    def test_no_include_components_param(self):
        """Verify include_components parameter was removed."""
        fn = _tool_fn_cache.get("read_blueprint_content")
        if fn is None:
            fn = asyncio.run(mcp.get_tool("read_blueprint_content")).fn
        sig = inspect.signature(fn)
        assert "include_components" not in sig.parameters

    def test_with_filter_flags(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        call_tool("read_blueprint_content",
            blueprint_path="/Game/Blueprints/MyBP",
            include_event_graph=False,
            include_variables=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["include_event_graph"] is False
        assert params["include_variables"] is True


class TestCompileBlueprint:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP", "compiled": True}
        call_tool("compile_blueprint", blueprint_name="MyBP")
        mock_ue_execute.assert_called_once_with(
            "compile_blueprint", {"blueprint_name": "MyBP"}
        )


class TestDeleteBlueprint:
    def test_default_no_force(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("delete_blueprint", blueprint_path="/Game/Blueprints/MyBP")
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_path"] == "/Game/Blueprints/MyBP"
        assert "force" not in params

    def test_with_force(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("delete_blueprint",
            blueprint_path="/Game/Blueprints/MyBP", force=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["force"] is True


# =============================================================================
# Blueprint Component Tools
# =============================================================================


class TestAddComponentToBlueprint:
    def test_required_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_component_to_blueprint",
            blueprint_name="MyBP", component_class="StaticMeshComponent",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["component_class"] == "StaticMeshComponent"
        assert "component_name" not in params
        assert "parent_component" not in params

    def test_with_all_optional(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_component_to_blueprint",
            blueprint_name="MyBP", component_class="StaticMeshComponent",
            component_name="Mesh1", parent_component="DefaultSceneRoot",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["component_name"] == "Mesh1"
        assert params["parent_component"] == "DefaultSceneRoot"


class TestRemoveComponentFromBlueprint:
    def test_passes_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("remove_component_from_blueprint",
            blueprint_name="MyBP", component_name="Mesh1",
        )
        mock_ue_execute.assert_called_once_with(
            "remove_component_from_blueprint",
            {"blueprint_name": "MyBP", "component_name": "Mesh1"},
        )


class TestReadComponentsFromBlueprint:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP", "count": 0, "components": []}
        call_tool("read_components_from_blueprint", blueprint_name="MyBP")
        mock_ue_execute.assert_called_once_with(
            "read_components_from_blueprint", {"blueprint_name": "MyBP"}
        )


# =============================================================================
# Error Handling
# =============================================================================


class TestErrorHandling:
    def test_connection_error_propagates(self, mock_ue_connection_error):
        with pytest.raises(ConnectionError, match="Cannot connect to UE"):
            call_tool("get_actors_in_level")

    def test_runtime_error_propagates(self, mock_ue_runtime_error):
        with pytest.raises(RuntimeError, match="UE error"):
            call_tool("spawn_actor", type="Actor", name="Test")


# =============================================================================
# Tool Registration
# =============================================================================


class TestToolRegistration:
    def test_all_18_tools_registered(self):
        """Verify all 18 tools are registered in the MCP server."""
        expected_tools = {
            # Actor (6)
            "get_actors_in_level", "find_actors_by_name", "spawn_actor",
            "delete_actor", "set_actor_transform", "read_actor_content",
            # ActorComponent (3)
            "add_component_to_actor", "remove_component_from_actor",
            "read_components_from_actor",
            # Blueprint (6)
            "get_blueprints", "find_blueprints_by_name", "create_blueprint",
            "read_blueprint_content", "compile_blueprint", "delete_blueprint",
            # BlueprintComponent (3)
            "add_component_to_blueprint", "remove_component_from_blueprint",
            "read_components_from_blueprint",
        }

        tools = asyncio.run(mcp.list_tools())
        registered = {t.name for t in tools}
        missing = expected_tools - registered
        assert not missing, f"Missing tools: {missing}"
