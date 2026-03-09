"""Integration tests — requires running UE editor with WN_MCP plugin.

Run with: uv run python -m pytest tests/test_integration.py -v -m integration
Skip with: uv run python -m pytest -m "not integration"
"""

import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import mcp_server

pytestmark = pytest.mark.integration


# =============================================================================
# Helpers
# =============================================================================

def parse(result: str) -> dict:
    """Parse JSON string result from a tool."""
    return json.loads(result)


# =============================================================================
# Actor CRUD
# =============================================================================


class TestActorCRUD:
    """Test actor create → read → update → delete lifecycle."""

    ACTOR_NAME = "_IntTest_Actor"

    def test_01_spawn_actor(self):
        result = parse(mcp_server.spawn_actor(
            type="StaticMeshActor",
            name=self.ACTOR_NAME,
            location=[100.0, 200.0, 300.0],
        ))
        assert result["status"] == "success"

    def test_02_find_actor(self):
        result = parse(mcp_server.find_actors_by_name(self.ACTOR_NAME))
        assert result["count"] >= 1
        names = [a["name"] for a in result["actors"]]
        assert self.ACTOR_NAME in names

    def test_03_read_actor(self):
        result = parse(mcp_server.read_actor_content(self.ACTOR_NAME))
        assert result["name"] == self.ACTOR_NAME
        assert "class" in result
        assert "location" in result

    def test_04_set_transform(self):
        result = parse(mcp_server.set_actor_transform(
            name=self.ACTOR_NAME,
            location=[500.0, 600.0, 700.0],
        ))
        assert result["status"] == "success"
        # Verify new location
        read = parse(mcp_server.read_actor_content(self.ACTOR_NAME))
        loc = read["location"]
        assert abs(loc[0] - 500.0) < 1.0

    def test_05_delete_actor(self):
        result = parse(mcp_server.delete_actor(self.ACTOR_NAME))
        assert result["status"] == "success"
        # Verify gone
        search = parse(mcp_server.find_actors_by_name(self.ACTOR_NAME))
        names = [a["name"] for a in search["actors"]]
        assert self.ACTOR_NAME not in names


# =============================================================================
# Actor Component CRD
# =============================================================================


class TestActorComponentCRD:
    """Test component add → read → remove on an actor."""

    ACTOR_NAME = "_IntTest_CompActor"
    COMP_NAME = "_IntTest_Light"

    def test_01_spawn_actor(self):
        result = parse(mcp_server.spawn_actor(
            type="StaticMeshActor", name=self.ACTOR_NAME
        ))
        assert result["status"] == "success"

    def test_02_add_component(self):
        result = parse(mcp_server.add_component_to_actor(
            name=self.ACTOR_NAME,
            component_class="PointLightComponent",
            component_name=self.COMP_NAME,
        ))
        assert result["status"] == "success"
        assert result["component_class"] == "PointLightComponent"

    def test_03_read_components(self):
        result = parse(mcp_server.read_components_from_actor(self.ACTOR_NAME))
        assert result["count"] >= 1
        names = [c["name"] for c in result["components"]]
        assert self.COMP_NAME in names

    def test_04_remove_component(self):
        result = parse(mcp_server.remove_component_from_actor(
            name=self.ACTOR_NAME, component_name=self.COMP_NAME
        ))
        assert result["status"] == "success"
        # Verify removed
        read = parse(mcp_server.read_components_from_actor(self.ACTOR_NAME))
        names = [c["name"] for c in read["components"]]
        assert self.COMP_NAME not in names

    def test_05_cleanup_actor(self):
        mcp_server.delete_actor(self.ACTOR_NAME)


# =============================================================================
# Blueprint CRUD
# =============================================================================


class TestBlueprintCRUD:
    """Test blueprint create → read → compile → delete lifecycle."""

    BP_NAME = "_IntTest_Blueprint"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"

    def test_01_create_blueprint(self):
        result = parse(mcp_server.create_blueprint(self.BP_NAME))
        assert result["name"] == self.BP_NAME

    def test_02_find_blueprint(self):
        result = parse(mcp_server.find_blueprints_by_name(self.BP_NAME))
        assert result["count"] >= 1

    def test_03_read_blueprint(self):
        result = parse(mcp_server.read_blueprint_content(self.BP_PATH))
        assert result["blueprint_name"] == self.BP_NAME
        assert "parent_class" in result

    def test_04_compile_blueprint(self):
        result = parse(mcp_server.compile_blueprint(self.BP_NAME))
        assert result["compiled"] is True

    def test_05_delete_blueprint(self):
        result = parse(mcp_server.delete_blueprint(self.BP_PATH, force=True))
        assert result["status"] == "success"


# =============================================================================
# Blueprint Component CRD
# =============================================================================


class TestBlueprintComponentCRD:
    """Test blueprint component add → read → remove."""

    BP_NAME = "_IntTest_CompBP"
    BP_PATH = f"/Game/Blueprints/{BP_NAME}"
    COMP_NAME = "_IntTest_Mesh"

    def test_01_create_blueprint(self):
        result = parse(mcp_server.create_blueprint(self.BP_NAME))
        assert result["name"] == self.BP_NAME

    def test_02_read_default_components(self):
        result = parse(mcp_server.read_components_from_blueprint(self.BP_NAME))
        # New Actor blueprint should have DefaultSceneRoot
        assert result["count"] >= 1

    def test_03_add_component(self):
        result = parse(mcp_server.add_component_to_blueprint(
            blueprint_name=self.BP_NAME,
            component_class="StaticMeshComponent",
            component_name=self.COMP_NAME,
        ))
        assert result["status"] == "success"

    def test_04_read_components(self):
        result = parse(mcp_server.read_components_from_blueprint(self.BP_NAME))
        names = [c["name"] for c in result["components"]]
        assert self.COMP_NAME in names

    def test_05_remove_component(self):
        result = parse(mcp_server.remove_component_from_blueprint(
            blueprint_name=self.BP_NAME, component_name=self.COMP_NAME
        ))
        assert result["status"] == "success"

    def test_06_cleanup_blueprint(self):
        mcp_server.delete_blueprint(self.BP_PATH, force=True)
