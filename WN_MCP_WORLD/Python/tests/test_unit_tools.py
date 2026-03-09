"""Unit tests for MCP tools.

Tests tool parameter passing and response formatting.
UE connection is mocked — no running editor required.
"""

import json
import sys
import os
import pytest

# Add parent directory to path so we can import mcp_server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mcp_server


# =============================================================================
# Actor Tools
# =============================================================================


class TestGetActorsInLevel:
    def test_calls_correct_command(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "actors": []}
        result = mcp_server.get_actors_in_level()
        mock_ue_execute.assert_called_once_with("get_actors_in_level")

    def test_returns_json_string(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 1, "actors": [{"name": "Cube"}]}
        result = mcp_server.get_actors_in_level()
        parsed = json.loads(result)
        assert parsed["count"] == 1


class TestFindActorsByName:
    def test_passes_search_text(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "actors": []}
        mcp_server.find_actors_by_name("Cube")
        mock_ue_execute.assert_called_once_with(
            "find_actors_by_name", {"search_text": "Cube"}
        )


class TestSpawnActor:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.spawn_actor(type="StaticMeshActor", name="MyCube")
        mock_ue_execute.assert_called_once_with(
            "spawn_actor", {"type": "StaticMeshActor", "name": "MyCube"}
        )

    def test_with_all_optional_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.spawn_actor(
            type="PointLight",
            name="MyLight",
            location=[1.0, 2.0, 3.0],
            rotation=[0.0, 90.0, 0.0],
            scale=[2.0, 2.0, 2.0],
        )
        args = mock_ue_execute.call_args
        params = args[0][1]
        assert params["location"] == [1.0, 2.0, 3.0]
        assert params["rotation"] == [0.0, 90.0, 0.0]
        assert params["scale"] == [2.0, 2.0, 2.0]

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.spawn_actor(type="Actor", name="A", location=[0, 0, 0])
        params = mock_ue_execute.call_args[0][1]
        assert "location" in params
        assert "rotation" not in params
        assert "scale" not in params


class TestDeleteActor:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.delete_actor("MyCube")
        mock_ue_execute.assert_called_once_with("delete_actor", {"name": "MyCube"})


class TestSetActorTransform:
    def test_name_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.set_actor_transform(name="MyCube")
        params = mock_ue_execute.call_args[0][1]
        assert params == {"name": "MyCube"}

    def test_partial_transform(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.set_actor_transform(name="MyCube", location=[10, 20, 30])
        params = mock_ue_execute.call_args[0][1]
        assert params["location"] == [10, 20, 30]
        assert "rotation" not in params


class TestReadActorContent:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "Cube", "class": "StaticMeshActor"}
        mcp_server.read_actor_content("Cube")
        mock_ue_execute.assert_called_once_with("read_actor_content", {"name": "Cube"})


# =============================================================================
# Actor Component Tools
# =============================================================================


class TestAddComponentToActor:
    def test_required_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.add_component_to_actor(
            name="MyCube", component_class="PointLightComponent"
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["name"] == "MyCube"
        assert params["component_class"] == "PointLightComponent"
        assert "component_name" not in params

    def test_with_component_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.add_component_to_actor(
            name="MyCube",
            component_class="PointLightComponent",
            component_name="MyLight",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["component_name"] == "MyLight"


class TestRemoveComponentFromActor:
    def test_passes_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.remove_component_from_actor(
            name="MyCube", component_name="MyLight"
        )
        mock_ue_execute.assert_called_once_with(
            "remove_component_from_actor",
            {"name": "MyCube", "component_name": "MyLight"},
        )


class TestReadComponentsFromActor:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"actor_name": "Cube", "count": 0, "components": []}
        mcp_server.read_components_from_actor("Cube")
        mock_ue_execute.assert_called_once_with(
            "read_components_from_actor", {"name": "Cube"}
        )


# =============================================================================
# Blueprint Tools
# =============================================================================


class TestGetBlueprints:
    def test_default_no_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        mcp_server.get_blueprints()
        mock_ue_execute.assert_called_once_with("get_blueprints", {})

    def test_with_search_path(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        mcp_server.get_blueprints(search_path="/Game/Maps/")
        mock_ue_execute.assert_called_once_with(
            "get_blueprints", {"search_path": "/Game/Maps/"}
        )


class TestFindBlueprintsByName:
    def test_passes_search_text(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        mcp_server.find_blueprints_by_name("Player")
        mock_ue_execute.assert_called_once_with(
            "find_blueprints_by_name", {"search_text": "Player"}
        )


class TestCreateBlueprint:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP", "path": "/Game/Blueprints/MyBP"}
        mcp_server.create_blueprint("MyBP")
        mock_ue_execute.assert_called_once_with(
            "create_blueprint", {"name": "MyBP"}
        )

    def test_with_parent_class(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP"}
        mcp_server.create_blueprint("MyBP", parent_class="Pawn")
        params = mock_ue_execute.call_args[0][1]
        assert params["parent_class"] == "Pawn"


class TestReadBlueprintContent:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        mcp_server.read_blueprint_content("/Game/Blueprints/MyBP")
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_path"] == "/Game/Blueprints/MyBP"

    def test_no_include_components_param(self, mock_ue_execute):
        """Verify include_components parameter was removed."""
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        import inspect
        sig = inspect.signature(mcp_server.read_blueprint_content)
        assert "include_components" not in sig.parameters

    def test_with_filter_flags(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        mcp_server.read_blueprint_content(
            "/Game/Blueprints/MyBP",
            include_event_graph=False,
            include_variables=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["include_event_graph"] is False
        assert params["include_variables"] is True


class TestCompileBlueprint:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP", "compiled": True}
        mcp_server.compile_blueprint("MyBP")
        mock_ue_execute.assert_called_once_with(
            "compile_blueprint", {"blueprint_name": "MyBP"}
        )


class TestDeleteBlueprint:
    def test_default_no_force(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.delete_blueprint("/Game/Blueprints/MyBP")
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_path"] == "/Game/Blueprints/MyBP"
        assert "force" not in params

    def test_with_force(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.delete_blueprint("/Game/Blueprints/MyBP", force=True)
        params = mock_ue_execute.call_args[0][1]
        assert params["force"] is True


# =============================================================================
# Blueprint Component Tools
# =============================================================================


class TestAddComponentToBlueprint:
    def test_required_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.add_component_to_blueprint(
            blueprint_name="MyBP",
            component_class="StaticMeshComponent",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["component_class"] == "StaticMeshComponent"
        assert "component_name" not in params
        assert "parent_component" not in params

    def test_with_all_optional(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.add_component_to_blueprint(
            blueprint_name="MyBP",
            component_class="StaticMeshComponent",
            component_name="Mesh1",
            parent_component="DefaultSceneRoot",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["component_name"] == "Mesh1"
        assert params["parent_component"] == "DefaultSceneRoot"


class TestRemoveComponentFromBlueprint:
    def test_passes_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        mcp_server.remove_component_from_blueprint(
            blueprint_name="MyBP", component_name="Mesh1"
        )
        mock_ue_execute.assert_called_once_with(
            "remove_component_from_blueprint",
            {"blueprint_name": "MyBP", "component_name": "Mesh1"},
        )


class TestReadComponentsFromBlueprint:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP", "count": 0, "components": []}
        mcp_server.read_components_from_blueprint("MyBP")
        mock_ue_execute.assert_called_once_with(
            "read_components_from_blueprint", {"blueprint_name": "MyBP"}
        )


# =============================================================================
# Error Handling
# =============================================================================


class TestErrorHandling:
    def test_connection_error_propagates(self, mock_ue_connection_error):
        with pytest.raises(ConnectionError, match="Cannot connect to UE"):
            mcp_server.get_actors_in_level()

    def test_runtime_error_propagates(self, mock_ue_runtime_error):
        with pytest.raises(RuntimeError, match="UE error"):
            mcp_server.spawn_actor(type="Actor", name="Test")


# =============================================================================
# Tool Registration
# =============================================================================


class TestToolRegistration:
    def test_all_18_tools_exist(self):
        """Verify all 18 tool functions are defined in mcp_server."""
        expected_tools = [
            # Actor (6)
            "get_actors_in_level",
            "find_actors_by_name",
            "spawn_actor",
            "delete_actor",
            "set_actor_transform",
            "read_actor_content",
            # ActorComponent (3)
            "add_component_to_actor",
            "remove_component_from_actor",
            "read_components_from_actor",
            # Blueprint (6)
            "get_blueprints",
            "find_blueprints_by_name",
            "create_blueprint",
            "read_blueprint_content",
            "compile_blueprint",
            "delete_blueprint",
            # BlueprintComponent (3)
            "add_component_to_blueprint",
            "remove_component_from_blueprint",
            "read_components_from_blueprint",
        ]
        for tool_name in expected_tools:
            assert hasattr(mcp_server, tool_name), f"Missing tool: {tool_name}"
            assert callable(getattr(mcp_server, tool_name)), f"Not callable: {tool_name}"
