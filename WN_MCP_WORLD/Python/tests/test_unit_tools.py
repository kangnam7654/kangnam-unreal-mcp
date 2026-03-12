"""Unit tests for MCP tools.

Tests tool parameter passing and response formatting.
UE connection is mocked — no running editor required.

Each tool module's register_tools() creates closures over ue_connection.execute().
We mock execute() at the source (tools.ue_connection) and call tool
functions via conftest.call_tool().
"""

import json
import asyncio
import inspect
import pytest
from conftest import call_tool, mcp


# =============================================================================
# Actor Tools
# =============================================================================


class TestGetActorsInLevel:
    def test_calls_correct_command(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "actors": []}
        call_tool("get_actors_in_level")
        mock_ue_execute.assert_called_once_with("get_actors_in_level", category_name="Actor")

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
            "find_actors_by_name", {"search_text": "Cube"}, category_name="Actor"
        )


class TestSpawnActor:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("spawn_actor", type="StaticMeshActor", name="MyCube")
        mock_ue_execute.assert_called_once_with(
            "spawn_actor", {"type": "StaticMeshActor", "name": "MyCube"}, category_name="Actor"
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
        mock_ue_execute.assert_called_once_with("delete_actor", {"name": "MyCube"}, category_name="Actor")


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

    def test_with_all_transform(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_actor_transform",
            name="MyCube",
            location=[1, 2, 3],
            rotation=[10, 20, 30],
            scale=[2, 2, 2],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["rotation"] == [10, 20, 30]
        assert params["scale"] == [2, 2, 2]


class TestReadActorContent:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "Cube", "class": "StaticMeshActor"}
        call_tool("read_actor_content", name="Cube")
        mock_ue_execute.assert_called_once_with("read_actor_content", {"name": "Cube"}, category_name="Actor")


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
            category_name="ActorComponent",
        )


class TestReadComponentsFromActor:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"actor_name": "Cube", "count": 0, "components": []}
        call_tool("read_components_from_actor", name="Cube")
        mock_ue_execute.assert_called_once_with(
            "read_components_from_actor", {"name": "Cube"}, category_name="ActorComponent"
        )


# =============================================================================
# Blueprint Tools
# =============================================================================


class TestGetBlueprints:
    def test_default_no_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        call_tool("get_blueprints")
        mock_ue_execute.assert_called_once_with("get_blueprints", {}, category_name="Blueprint")

    def test_with_search_path(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        call_tool("get_blueprints", search_path="/Game/Maps/")
        mock_ue_execute.assert_called_once_with(
            "get_blueprints", {"search_path": "/Game/Maps/"}, category_name="Blueprint"
        )


class TestFindBlueprintsByName:
    def test_passes_search_text(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "blueprints": []}
        call_tool("find_blueprints_by_name", search_text="Player")
        mock_ue_execute.assert_called_once_with(
            "find_blueprints_by_name", {"search_text": "Player"}, category_name="Blueprint"
        )


class TestCreateBlueprint:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP", "path": "/Game/Blueprints/MyBP"}
        call_tool("create_blueprint", name="MyBP")
        mock_ue_execute.assert_called_once_with("create_blueprint", {"name": "MyBP"}, category_name="Blueprint")

    def test_with_parent_class(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP"}
        call_tool("create_blueprint", name="MyBP", parent_class="Pawn")
        params = mock_ue_execute.call_args[0][1]
        assert params["parent_class"] == "Pawn"


class TestReadBlueprintContent:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        call_tool("read_blueprint_content", blueprint_name="MyBP")
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"

    def test_no_include_components_param(self):
        """Verify include_components parameter was removed."""
        tool = asyncio.run(mcp.get_tool("read_blueprint_content"))
        sig = inspect.signature(tool.fn)
        assert "include_components" not in sig.parameters

    def test_with_filter_flags(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP"}
        call_tool("read_blueprint_content",
            blueprint_name="MyBP",
            include_event_graph=False,
            include_functions=True,
            include_variables=True,
            include_interfaces=False,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["include_event_graph"] is False
        assert params["include_functions"] is True
        assert params["include_variables"] is True
        assert params["include_interfaces"] is False


class TestCompileBlueprint:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"name": "MyBP", "compiled": True}
        call_tool("compile_blueprint", blueprint_name="MyBP")
        mock_ue_execute.assert_called_once_with(
            "compile_blueprint", {"blueprint_name": "MyBP"}, category_name="Blueprint"
        )


class TestDeleteBlueprint:
    def test_default_no_force(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("delete_blueprint", blueprint_name="MyBP")
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert "force" not in params

    def test_with_force(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("delete_blueprint",
            blueprint_name="MyBP", force=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["force"] is True


class TestSpawnBlueprintActor:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("spawn_blueprint_actor",
            blueprint_name="MyBP", name="MyInstance",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["name"] == "MyInstance"
        assert "location" not in params
        assert "rotation" not in params
        assert "scale" not in params

    def test_with_all_optional_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("spawn_blueprint_actor",
            blueprint_name="MyBP", name="MyInstance",
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
        call_tool("spawn_blueprint_actor",
            blueprint_name="MyBP", name="MyInstance",
            location=[0, 0, 0],
        )
        params = mock_ue_execute.call_args[0][1]
        assert "location" in params
        assert "rotation" not in params
        assert "scale" not in params


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
            category_name="BlueprintComponent",
        )


class TestReadComponentsFromBlueprint:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP", "count": 0, "components": []}
        call_tool("read_components_from_blueprint", blueprint_name="MyBP")
        mock_ue_execute.assert_called_once_with(
            "read_components_from_blueprint", {"blueprint_name": "MyBP"}, category_name="BlueprintComponent"
        )


# =============================================================================
# Property Tools
# =============================================================================


class TestSetStaticMeshProperties:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_static_mesh_properties",
            blueprint_name="MyBP", component_name="Mesh1",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["component_name"] == "Mesh1"
        assert "static_mesh" not in params
        assert "material" not in params

    def test_with_static_mesh(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_static_mesh_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            static_mesh="/Engine/BasicShapes/Cube.Cube",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["static_mesh"] == "/Engine/BasicShapes/Cube.Cube"

    def test_with_material(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_static_mesh_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            material="/Game/Materials/M_Red",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["material"] == "/Game/Materials/M_Red"

    def test_with_all_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_static_mesh_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            static_mesh="/Engine/BasicShapes/Sphere.Sphere",
            material="/Game/Materials/M_Blue",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["static_mesh"] == "/Engine/BasicShapes/Sphere.Sphere"
        assert params["material"] == "/Game/Materials/M_Blue"


class TestSetPhysicsProperties:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_physics_properties",
            blueprint_name="MyBP", component_name="Mesh1",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["component_name"] == "Mesh1"
        assert "simulate_physics" not in params
        assert "mass" not in params

    def test_with_simulate_physics(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_physics_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            simulate_physics=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["simulate_physics"] is True

    def test_with_mass(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_physics_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            mass=50.0,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["mass"] == 50.0

    def test_with_all_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_physics_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            simulate_physics=True, mass=10.0,
            linear_damping=0.5, angular_damping=1.0,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["simulate_physics"] is True
        assert params["mass"] == 10.0
        assert params["linear_damping"] == 0.5
        assert params["angular_damping"] == 1.0

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_physics_properties",
            blueprint_name="MyBP", component_name="Mesh1",
            simulate_physics=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert "simulate_physics" in params
        assert "mass" not in params
        assert "linear_damping" not in params
        assert "angular_damping" not in params


# =============================================================================
# Material Tools
# =============================================================================


class TestGetAvailableMaterials:
    def test_default_no_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "materials": []}
        call_tool("get_available_materials")
        mock_ue_execute.assert_called_once_with("get_available_materials", {}, category_name="Material")

    def test_with_search_path(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "materials": []}
        call_tool("get_available_materials", search_path="/Game/Materials/")
        params = mock_ue_execute.call_args[0][1]
        assert params["search_path"] == "/Game/Materials/"

    def test_with_include_engine(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "materials": []}
        call_tool("get_available_materials", include_engine_materials=False)
        params = mock_ue_execute.call_args[0][1]
        assert params["include_engine_materials"] is False


class TestApplyMaterialToActor:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("apply_material_to_actor",
            actor_name="MyCube", material_path="/Game/Materials/M_Red",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["actor_name"] == "MyCube"
        assert params["material_path"] == "/Game/Materials/M_Red"
        assert "material_slot" not in params

    def test_with_material_slot(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("apply_material_to_actor",
            actor_name="MyCube", material_path="/Game/Materials/M_Red",
            material_slot=1,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["material_slot"] == 1


class TestApplyMaterialToBlueprint:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("apply_material_to_blueprint",
            blueprint_name="MyBP", component_name="Mesh1",
            material_path="/Game/Materials/M_Red",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["component_name"] == "Mesh1"
        assert params["material_path"] == "/Game/Materials/M_Red"
        assert "material_slot" not in params

    def test_with_material_slot(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("apply_material_to_blueprint",
            blueprint_name="MyBP", component_name="Mesh1",
            material_path="/Game/Materials/M_Red", material_slot=2,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["material_slot"] == 2


class TestGetActorMaterialInfo:
    def test_passes_actor_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"actor_name": "MyCube", "total_slots": 0, "material_slots": []}
        call_tool("get_actor_material_info", actor_name="MyCube")
        mock_ue_execute.assert_called_once_with(
            "get_actor_material_info", {"actor_name": "MyCube"}, category_name="Material"
        )

    def test_returns_json_string(self, mock_ue_execute):
        mock_ue_execute.return_value = {
            "actor_name": "MyCube",
            "total_slots": 1,
            "material_slots": [{"slot": 0, "component": "StaticMeshComponent0", "material_name": "M_Default"}],
        }
        result = call_tool("get_actor_material_info", actor_name="MyCube")
        parsed = json.loads(result)
        assert parsed["actor_name"] == "MyCube"
        assert len(parsed["material_slots"]) == 1


class TestGetBlueprintMaterialInfo:
    def test_passes_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP", "total_slots": 0, "material_slots": []}
        call_tool("get_blueprint_material_info",
            blueprint_name="MyBP", component_name="Mesh1",
        )
        mock_ue_execute.assert_called_once_with(
            "get_blueprint_material_info",
            {"blueprint_name": "MyBP", "component_name": "Mesh1"},
            category_name="Material",
        )


class TestSetMeshMaterialColor:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_mesh_material_color",
            blueprint_name="MyBP", component_name="Mesh1",
            color=[1.0, 0.0, 0.0],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["component_name"] == "Mesh1"
        assert params["color"] == [1.0, 0.0, 0.0]
        assert "material_slot" not in params
        assert "parameter_name" not in params
        assert "material_path" not in params
        assert "metallic" not in params
        assert "roughness" not in params

    def test_with_all_optional_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_mesh_material_color",
            blueprint_name="MyBP", component_name="Mesh1",
            color=[0.0, 1.0, 0.0, 1.0], material_slot=1,
            parameter_name="Emissive", material_path="/Game/Materials/M_Base",
            metallic=1.0, roughness=0.2,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["color"] == [0.0, 1.0, 0.0, 1.0]
        assert params["material_slot"] == 1
        assert params["parameter_name"] == "Emissive"
        assert params["material_path"] == "/Game/Materials/M_Base"
        assert params["metallic"] == 1.0
        assert params["roughness"] == 0.2

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_mesh_material_color",
            blueprint_name="MyBP", component_name="Mesh1",
            color=[1.0, 0.0, 0.0], material_slot=0,
        )
        params = mock_ue_execute.call_args[0][1]
        assert "material_slot" in params
        assert "parameter_name" not in params
        assert "material_path" not in params
        assert "metallic" not in params
        assert "roughness" not in params

    def test_metallic_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_mesh_material_color",
            blueprint_name="MyBP", component_name="Mesh1",
            color=[0.7, 0.7, 0.7], metallic=1.0,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["metallic"] == 1.0
        assert "roughness" not in params

    def test_roughness_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("set_mesh_material_color",
            blueprint_name="MyBP", component_name="Mesh1",
            color=[0.5, 0.5, 0.5], roughness=0.1,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["roughness"] == 0.1
        assert "metallic" not in params


# =============================================================================
# StaticMesh Tools
# =============================================================================


class TestGetStaticMeshes:
    def test_default_no_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "static_meshes": []}
        call_tool("get_static_meshes")
        mock_ue_execute.assert_called_once_with("get_static_meshes", {}, category_name="StaticMesh")

    def test_with_search_path(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "static_meshes": []}
        call_tool("get_static_meshes", search_path="/Game/Meshes/")
        params = mock_ue_execute.call_args[0][1]
        assert params["search_path"] == "/Game/Meshes/"

    def test_with_include_engine(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "static_meshes": []}
        call_tool("get_static_meshes", include_engine_meshes=False)
        params = mock_ue_execute.call_args[0][1]
        assert params["include_engine_meshes"] is False


class TestFindStaticMeshesByName:
    def test_passes_search_text(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "static_meshes": []}
        call_tool("find_static_meshes_by_name", search_text="Cube")
        mock_ue_execute.assert_called_once_with(
            "find_static_meshes_by_name", {"search_text": "Cube"}, category_name="StaticMesh"
        )

    def test_with_include_engine(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "static_meshes": []}
        call_tool("find_static_meshes_by_name",
            search_text="Sphere", include_engine_meshes=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["search_text"] == "Sphere"
        assert params["include_engine_meshes"] is True

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"count": 0, "static_meshes": []}
        call_tool("find_static_meshes_by_name", search_text="Cube")
        params = mock_ue_execute.call_args[0][1]
        assert "search_text" in params
        assert "include_engine_meshes" not in params


# =============================================================================
# Blueprint Variable Tools
# =============================================================================


class TestAddVariableToBlueprint:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_variable_to_blueprint",
            blueprint_name="MyBP", variable_name="HP", variable_type="Float",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["variable_name"] == "HP"
        assert params["variable_type"] == "Float"
        assert "default_value" not in params
        assert "is_instance_editable" not in params

    def test_with_default_value(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_variable_to_blueprint",
            blueprint_name="MyBP", variable_name="HP", variable_type="Float",
            default_value="100.0",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["default_value"] == "100.0"

    def test_with_instance_editable(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_variable_to_blueprint",
            blueprint_name="MyBP", variable_name="IsAlive", variable_type="Bool",
            is_instance_editable=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["is_instance_editable"] is True

    def test_with_all_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_variable_to_blueprint",
            blueprint_name="MyBP", variable_name="Speed", variable_type="Float",
            default_value="300.0", is_instance_editable=True,
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["default_value"] == "300.0"
        assert params["is_instance_editable"] is True

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("add_variable_to_blueprint",
            blueprint_name="MyBP", variable_name="HP", variable_type="Float",
        )
        params = mock_ue_execute.call_args[0][1]
        assert "default_value" not in params
        assert "is_instance_editable" not in params


class TestRemoveVariableFromBlueprint:
    def test_passes_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("remove_variable_from_blueprint",
            blueprint_name="MyBP", variable_name="HP",
        )
        mock_ue_execute.assert_called_once_with(
            "remove_variable_from_blueprint",
            {"blueprint_name": "MyBP", "variable_name": "HP"},
            category_name="BlueprintVariable",
        )


# =============================================================================
# Blueprint Graph Tools
# =============================================================================


class TestReadBlueprintGraph:
    def test_passes_name(self, mock_ue_execute):
        mock_ue_execute.return_value = {"blueprint_name": "MyBP", "nodes": []}
        call_tool("read_blueprint_graph", blueprint_name="MyBP")
        mock_ue_execute.assert_called_once_with(
            "read_blueprint_graph", {"blueprint_name": "MyBP"}, category_name="BlueprintGraph"
        )


class TestAddEventNode:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "AAA"}
        call_tool("add_event_node",
            blueprint_name="MyBP", event_type="BeginPlay",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["event_type"] == "BeginPlay"
        assert "node_position" not in params

    def test_with_position(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "AAA"}
        call_tool("add_event_node",
            blueprint_name="MyBP", event_type="Tick",
            node_position=[100, 200],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["node_position"] == [100, 200]


class TestAddFunctionCallNode:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "BBB"}
        call_tool("add_function_call_node",
            blueprint_name="MyBP", function_name="PrintString",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["function_name"] == "PrintString"
        assert "target_class" not in params
        assert "node_position" not in params

    def test_with_target_class(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "BBB"}
        call_tool("add_function_call_node",
            blueprint_name="MyBP", function_name="PrintString",
            target_class="KismetSystemLibrary",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["target_class"] == "KismetSystemLibrary"

    def test_with_all_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "BBB"}
        call_tool("add_function_call_node",
            blueprint_name="MyBP", function_name="Delay",
            target_class="KismetSystemLibrary", node_position=[300, 100],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["target_class"] == "KismetSystemLibrary"
        assert params["node_position"] == [300, 100]

    def test_omitted_optionals_not_sent(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "BBB"}
        call_tool("add_function_call_node",
            blueprint_name="MyBP", function_name="PrintString",
        )
        params = mock_ue_execute.call_args[0][1]
        assert "target_class" not in params
        assert "node_position" not in params


class TestAddVariableGetNode:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "CCC"}
        call_tool("add_variable_get_node",
            blueprint_name="MyBP", variable_name="HP",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["variable_name"] == "HP"
        assert "node_position" not in params

    def test_with_position(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "CCC"}
        call_tool("add_variable_get_node",
            blueprint_name="MyBP", variable_name="HP",
            node_position=[200, 300],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["node_position"] == [200, 300]


class TestAddVariableSetNode:
    def test_required_params_only(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "DDD"}
        call_tool("add_variable_set_node",
            blueprint_name="MyBP", variable_name="HP",
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["blueprint_name"] == "MyBP"
        assert params["variable_name"] == "HP"
        assert "node_position" not in params

    def test_with_position(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "node_id": "DDD"}
        call_tool("add_variable_set_node",
            blueprint_name="MyBP", variable_name="HP",
            node_position=[400, 100],
        )
        params = mock_ue_execute.call_args[0][1]
        assert params["node_position"] == [400, 100]


class TestConnectNodes:
    def test_passes_all_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success"}
        call_tool("connect_nodes",
            blueprint_name="MyBP",
            source_node_id="AAA", source_pin_name="then",
            target_node_id="BBB", target_pin_name="execute",
        )
        mock_ue_execute.assert_called_once_with(
            "connect_nodes",
            {
                "blueprint_name": "MyBP",
                "source_node_id": "AAA",
                "source_pin_name": "then",
                "target_node_id": "BBB",
                "target_pin_name": "execute",
            },
            category_name="BlueprintGraph",
        )


class TestDisconnectNodes:
    def test_passes_all_params(self, mock_ue_execute):
        mock_ue_execute.return_value = {"status": "success", "disconnected_count": 1}
        call_tool("disconnect_nodes",
            blueprint_name="MyBP", node_id="AAA", pin_name="then",
        )
        mock_ue_execute.assert_called_once_with(
            "disconnect_nodes",
            {"blueprint_name": "MyBP", "node_id": "AAA", "pin_name": "then"},
            category_name="BlueprintGraph",
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
    def test_all_38_tools_registered(self):
        """Verify all 38 tools are registered in the MCP server."""
        expected_tools = {
            # Actor (6)
            "get_actors_in_level", "find_actors_by_name", "spawn_actor",
            "delete_actor", "set_actor_transform", "read_actor_content",
            # ActorComponent (3)
            "add_component_to_actor", "remove_component_from_actor",
            "read_components_from_actor",
            # Blueprint (7)
            "get_blueprints", "find_blueprints_by_name", "create_blueprint",
            "read_blueprint_content", "compile_blueprint", "delete_blueprint",
            "spawn_blueprint_actor",
            # BlueprintComponent (3)
            "add_component_to_blueprint", "remove_component_from_blueprint",
            "read_components_from_blueprint",
            # Property (2)
            "set_static_mesh_properties", "set_physics_properties",
            # Material (6)
            "get_available_materials", "apply_material_to_actor",
            "apply_material_to_blueprint", "get_actor_material_info",
            "get_blueprint_material_info", "set_mesh_material_color",
            # StaticMesh (2)
            "get_static_meshes", "find_static_meshes_by_name",
            # BlueprintVariable (2)
            "add_variable_to_blueprint", "remove_variable_from_blueprint",
            # BlueprintGraph (7)
            "read_blueprint_graph", "add_event_node", "add_function_call_node",
            "add_variable_get_node", "add_variable_set_node",
            "connect_nodes", "disconnect_nodes",
        }

        tools = asyncio.run(mcp.list_tools())
        registered = {t.name for t in tools}
        missing = expected_tools - registered
        assert not missing, f"Missing tools: {missing}"
