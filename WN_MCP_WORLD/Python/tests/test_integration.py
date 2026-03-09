"""Integration tests — requires running UE editor with WN_MCP plugin.

Run with: uv run python -m pytest tests/test_integration.py -v -m integration
Skip with: uv run python -m pytest -m "not integration"
"""

import json
import sys
import os
import asyncio
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mcp_server import mcp

pytestmark = pytest.mark.integration


# =============================================================================
# Helpers
# =============================================================================

_tool_cache: dict = {}


def call(tool_name: str, **kwargs) -> dict:
    """Call a registered tool by name and return parsed result."""
    if tool_name not in _tool_cache:
        async def _resolve():
            tool = await mcp.get_tool(tool_name)
            return tool.fn
        _tool_cache[tool_name] = asyncio.run(_resolve())

    result_str = _tool_cache[tool_name](**kwargs)
    return json.loads(result_str)


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
        assert result["name"] == self.ACTOR_NAME
        assert "class" in result
        assert "location" in result

    def test_04_set_transform(self):
        result = call("set_actor_transform",
            name=self.ACTOR_NAME, location=[500.0, 600.0, 700.0],
        )
        assert result["status"] == "success"
        # Verify new location
        read = call("read_actor_content", name=self.ACTOR_NAME)
        assert abs(read["location"][0] - 500.0) < 1.0

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
        result = call("read_blueprint_content", blueprint_path=self.BP_PATH)
        assert result["blueprint_name"] == self.BP_NAME
        assert "parent_class" in result

    def test_04_compile_blueprint(self):
        result = call("compile_blueprint", blueprint_name=self.BP_NAME)
        assert result["compiled"] is True

    def test_05_delete_blueprint(self):
        result = call("delete_blueprint", blueprint_path=self.BP_PATH, force=True)
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
        call("delete_blueprint", blueprint_path=self.BP_PATH, force=True)
