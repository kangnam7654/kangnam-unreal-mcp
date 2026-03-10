"""Integration tests — requires running UE editor with WN_MCP plugin.

Run with: uv run python -m pytest tests/test_integration.py -v -m integration
Skip with: uv run python -m pytest -m "not integration"
"""

import json
import pytest

from conftest import call_tool

pytestmark = pytest.mark.integration


# =============================================================================
# Helpers
# =============================================================================


def call(tool_name: str, **kwargs) -> dict:
    """Call a registered tool by name and return parsed JSON result."""
    return json.loads(call_tool(tool_name, **kwargs))


# =============================================================================
# Actor CRUD
# =============================================================================


class TestActorCRUD:
    """Test actor create -> read -> update -> delete lifecycle."""

    ACTOR_NAME = "_IntTest_Actor"

    def test_01_spawn_actor(self):
        result = call("spawn_actor",
            type="StaticMeshActor", name=self.ACTOR_NAME,
            location=[100.0, 200.0, 300.0],
        )
        assert result["status"] == "success"

    def test_02_find_actor(self):
        result = call("find_actors_by_name", search_text=self.ACTOR_NAME)
        assert result["count"] >= 1
        names = [a["name"] for a in result["actors"]]
        assert self.ACTOR_NAME in names

    def test_03_read_actor(self):
        result = call("read_actor_content", name=self.ACTOR_NAME)
        assert result["status"] == "success"
        actor = result["actor"]
        assert actor["name"] == self.ACTOR_NAME
        assert "class" in actor
        assert "location" in actor

    def test_04_set_transform(self):
        result = call("set_actor_transform",
            name=self.ACTOR_NAME, location=[500.0, 600.0, 700.0],
        )
        assert result["status"] == "success"
        # Verify new location
        read = call("read_actor_content", name=self.ACTOR_NAME)
        assert abs(read["actor"]["location"][0] - 500.0) < 1.0

    def test_05_delete_actor(self):
        result = call("delete_actor", name=self.ACTOR_NAME)
        assert result["status"] == "success"
        # Verify gone
        search = call("find_actors_by_name", search_text=self.ACTOR_NAME)
        names = [a["name"] for a in search["actors"]]
        assert self.ACTOR_NAME not in names


# =============================================================================
# Actor Component CRD
# =============================================================================


class TestActorComponentCRD:
    """Test component add -> read -> remove on an actor."""

    ACTOR_NAME = "_IntTest_CompActor"
    COMP_NAME = "_IntTest_Light"

    def test_01_spawn_actor(self):
        result = call("spawn_actor",
            type="StaticMeshActor", name=self.ACTOR_NAME,
        )
        assert result["status"] == "success"

    def test_02_add_component(self):
        result = call("add_component_to_actor",
            name=self.ACTOR_NAME,
            component_class="PointLightComponent",
            component_name=self.COMP_NAME,
        )
        assert result["status"] == "success"
        assert result["component_class"] == "PointLightComponent"

    def test_03_read_components(self):
        result = call("read_components_from_actor", name=self.ACTOR_NAME)
        assert result["count"] >= 1
        names = [c["name"] for c in result["components"]]
        assert self.COMP_NAME in names

    def test_04_remove_component(self):
        result = call("remove_component_from_actor",
            name=self.ACTOR_NAME, component_name=self.COMP_NAME,
        )
        assert result["status"] == "success"
        # Verify removed
        read = call("read_components_from_actor", name=self.ACTOR_NAME)
        names = [c["name"] for c in read["components"]]
        assert self.COMP_NAME not in names

    def test_05_cleanup_actor(self):
        call("delete_actor", name=self.ACTOR_NAME)


# =============================================================================
# Blueprint CRUD
# =============================================================================


class TestBlueprintCRUD:
    """Test blueprint create -> read -> compile -> delete lifecycle."""

    BP_NAME = "_IntTest_Blueprint"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"

    def test_01_create_blueprint(self):
        result = call("create_blueprint", name=self.BP_NAME)
        assert result["name"] == self.BP_NAME

    def test_02_find_blueprint(self):
        result = call("find_blueprints_by_name", search_text=self.BP_NAME)
        assert result["count"] >= 1

    def test_03_read_blueprint(self):
        result = call("read_blueprint_content", blueprint_name=self.BP_NAME)
        assert result["blueprint_name"] == self.BP_NAME
        assert "parent_class" in result

    def test_04_compile_blueprint(self):
        result = call("compile_blueprint", blueprint_name=self.BP_NAME)
        assert result["compiled"] is True

    def test_05_delete_blueprint(self):
        result = call("delete_blueprint", blueprint_name=self.BP_NAME, force=True)
        assert result["status"] == "success"


# =============================================================================
# Blueprint Component CRD
# =============================================================================


class TestBlueprintComponentCRD:
    """Test blueprint component add -> read -> remove."""

    BP_NAME = "_IntTest_CompBP"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"
    COMP_NAME = "_IntTest_Mesh"

    def test_01_create_blueprint(self):
        result = call("create_blueprint", name=self.BP_NAME)
        assert result["name"] == self.BP_NAME

    def test_02_read_default_components(self):
        result = call("read_components_from_blueprint", blueprint_name=self.BP_NAME)
        # New Actor blueprint should have DefaultSceneRoot
        assert result["count"] >= 1

    def test_03_add_component(self):
        result = call("add_component_to_blueprint",
            blueprint_name=self.BP_NAME,
            component_class="StaticMeshComponent",
            component_name=self.COMP_NAME,
        )
        assert result["status"] == "success"

    def test_04_read_components(self):
        result = call("read_components_from_blueprint", blueprint_name=self.BP_NAME)
        names = [c["name"] for c in result["components"]]
        assert self.COMP_NAME in names

    def test_05_remove_component(self):
        result = call("remove_component_from_blueprint",
            blueprint_name=self.BP_NAME, component_name=self.COMP_NAME,
        )
        assert result["status"] == "success"

    def test_06_cleanup_blueprint(self):
        call("delete_blueprint", blueprint_name=self.BP_NAME, force=True)


# =============================================================================
# Property Commands
# =============================================================================


class TestPropertyCommands:
    """Test set_static_mesh_properties and set_physics_properties on a Blueprint."""

    BP_NAME = "_IntTest_PropBP"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"
    COMP_NAME = "_IntTest_PropMesh"

    def test_01_create_blueprint(self):
        result = call("create_blueprint", name=self.BP_NAME)
        assert result["name"] == self.BP_NAME

    def test_02_add_static_mesh_component(self):
        result = call("add_component_to_blueprint",
            blueprint_name=self.BP_NAME,
            component_class="StaticMeshComponent",
            component_name=self.COMP_NAME,
        )
        assert result["status"] == "success"

    def test_03_set_static_mesh(self):
        result = call("set_static_mesh_properties",
            blueprint_name=self.BP_NAME,
            component_name=self.COMP_NAME,
            static_mesh="/Engine/BasicShapes/Cube.Cube",
        )
        assert result["status"] == "success"

    def test_04_set_physics(self):
        result = call("set_physics_properties",
            blueprint_name=self.BP_NAME,
            component_name=self.COMP_NAME,
            simulate_physics=True,
            mass=50.0,
            linear_damping=0.5,
        )
        assert result["status"] == "success"

    def test_05_cleanup_blueprint(self):
        call("delete_blueprint", blueprint_name=self.BP_NAME, force=True)


# =============================================================================
# Blueprint Spawn
# =============================================================================


class TestBlueprintSpawn:
    """Test spawn_blueprint_actor: create BP -> compile -> spawn -> verify -> cleanup."""

    BP_NAME = "_IntTest_SpawnBP"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"
    ACTOR_NAME = "_IntTest_SpawnedActor"

    def test_01_create_blueprint(self):
        result = call("create_blueprint", name=self.BP_NAME)
        assert result["name"] == self.BP_NAME

    def test_02_compile_blueprint(self):
        result = call("compile_blueprint", blueprint_name=self.BP_NAME)
        assert result["compiled"] is True

    def test_03_spawn_blueprint_actor(self):
        result = call("spawn_blueprint_actor",
            blueprint_name=self.BP_NAME, name=self.ACTOR_NAME,
            location=[100.0, 200.0, 0.0],
        )
        assert result["status"] == "success"

    def test_04_verify_actor_exists(self):
        result = call("find_actors_by_name", search_text=self.ACTOR_NAME)
        assert result["count"] >= 1
        names = [a["name"] for a in result["actors"]]
        assert self.ACTOR_NAME in names

    def test_05_cleanup_actor(self):
        call("delete_actor", name=self.ACTOR_NAME)

    def test_06_cleanup_blueprint(self):
        call("delete_blueprint", blueprint_name=self.BP_NAME, force=True)


# =============================================================================
# Material Commands
# =============================================================================


class TestMaterialCommands:
    """Test material query, apply, info, and color commands."""

    ACTOR_NAME = "_IntTest_MatActor"
    BP_NAME = "_IntTest_MatBP"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"
    COMP_NAME = "_IntTest_MatMesh"

    def test_01_get_available_materials(self):
        result = call("get_available_materials")
        assert result["count"] > 0
        assert len(result["materials"]) > 0

    def test_02_spawn_actor(self):
        result = call("spawn_actor",
            type="StaticMeshActor", name=self.ACTOR_NAME,
        )
        assert result["status"] == "success"

    def test_03_get_actor_material_info(self):
        result = call("get_actor_material_info", actor_name=self.ACTOR_NAME)
        assert result["actor_name"] == self.ACTOR_NAME
        assert "material_slots" in result

    def test_04_apply_material_to_actor(self):
        result = call("apply_material_to_actor",
            actor_name=self.ACTOR_NAME,
            material_path="/Engine/BasicShapes/BasicShapeMaterial",
        )
        assert result["status"] == "success"

    def test_05_create_blueprint_with_mesh(self):
        call("create_blueprint", name=self.BP_NAME)
        call("add_component_to_blueprint",
            blueprint_name=self.BP_NAME,
            component_class="StaticMeshComponent",
            component_name=self.COMP_NAME,
        )
        result = call("set_static_mesh_properties",
            blueprint_name=self.BP_NAME,
            component_name=self.COMP_NAME,
            static_mesh="/Engine/BasicShapes/Cube.Cube",
        )
        assert result["status"] == "success"

    def test_06_get_blueprint_material_info(self):
        result = call("get_blueprint_material_info",
            blueprint_name=self.BP_NAME, component_name=self.COMP_NAME,
        )
        assert result["blueprint_name"] == self.BP_NAME
        assert "material_slots" in result

    def test_07_apply_material_to_blueprint(self):
        result = call("apply_material_to_blueprint",
            blueprint_name=self.BP_NAME,
            component_name=self.COMP_NAME,
            material_path="/Engine/BasicShapes/BasicShapeMaterial",
        )
        assert result["status"] == "success"

    def test_08_set_mesh_material_color(self):
        result = call("set_mesh_material_color",
            blueprint_name=self.BP_NAME,
            component_name=self.COMP_NAME,
            color=[1.0, 0.0, 0.0],
        )
        assert result["status"] == "success"

    def test_09_cleanup_actor(self):
        call("delete_actor", name=self.ACTOR_NAME)

    def test_10_cleanup_blueprint(self):
        call("delete_blueprint", blueprint_name=self.BP_NAME, force=True)
