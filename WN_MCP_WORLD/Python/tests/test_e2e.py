"""End-to-end tests — MCP client through stdio transport.

Requires running UE editor with WN_MCP plugin.

Run with: uv run python -m pytest tests/test_e2e.py -v -m e2e
Skip with: uv run python -m pytest -m "not e2e"
"""

import json
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

pytestmark = pytest.mark.e2e


# =============================================================================
# Helpers
# =============================================================================

@pytest.fixture(scope="module")
def mcp_client():
    """Create an in-process MCP client using FastMCP's test utilities."""
    from mcp_server import mcp
    from fastmcp import Client

    client = Client(mcp)
    return client


async def call_tool(client, tool_name: str, args: dict = None) -> dict:
    """Call a tool and parse the JSON result."""
    result = await client.call_tool(tool_name, args or {})
    # FastMCP returns list of TextContent
    text = result[0].text if result else "{}"
    return json.loads(text)


# =============================================================================
# Tool Discovery
# =============================================================================


@pytest.mark.asyncio
async def test_all_18_tools_registered(mcp_client):
    """Verify all 18 tools are registered in the MCP server."""
    async with mcp_client:
        tools = await mcp_client.list_tools()
        tool_names = {t.name for t in tools}

        expected = {
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

        missing = expected - tool_names
        assert not missing, f"Missing tools: {missing}"


# =============================================================================
# Actor CRUD E2E
# =============================================================================


@pytest.mark.asyncio
async def test_actor_crud_e2e(mcp_client):
    """Full actor lifecycle: spawn → read → transform → delete."""
    name = "_E2E_Actor"

    async with mcp_client:
        # Create
        result = await call_tool(mcp_client, "spawn_actor", {
            "type": "StaticMeshActor", "name": name,
            "location": [100, 200, 300],
        })
        assert result["status"] == "success"

        # Read
        result = await call_tool(mcp_client, "read_actor_content", {"name": name})
        assert result["name"] == name

        # Update transform
        result = await call_tool(mcp_client, "set_actor_transform", {
            "name": name, "location": [999, 999, 999],
        })
        assert result["status"] == "success"

        # Delete
        result = await call_tool(mcp_client, "delete_actor", {"name": name})
        assert result["status"] == "success"

        # Verify gone
        result = await call_tool(mcp_client, "find_actors_by_name", {
            "search_text": name,
        })
        assert result["count"] == 0


# =============================================================================
# Component CRUD E2E
# =============================================================================


@pytest.mark.asyncio
async def test_actor_component_crud_e2e(mcp_client):
    """Component lifecycle on actor: spawn actor → add comp → read → remove → delete actor."""
    actor_name = "_E2E_CompActor"
    comp_name = "_E2E_Light"

    async with mcp_client:
        # Setup: create actor
        await call_tool(mcp_client, "spawn_actor", {
            "type": "StaticMeshActor", "name": actor_name,
        })

        # Add component
        result = await call_tool(mcp_client, "add_component_to_actor", {
            "name": actor_name,
            "component_class": "PointLightComponent",
            "component_name": comp_name,
        })
        assert result["status"] == "success"

        # Read components
        result = await call_tool(mcp_client, "read_components_from_actor", {
            "name": actor_name,
        })
        names = [c["name"] for c in result["components"]]
        assert comp_name in names

        # Remove component
        result = await call_tool(mcp_client, "remove_component_from_actor", {
            "name": actor_name, "component_name": comp_name,
        })
        assert result["status"] == "success"

        # Cleanup
        await call_tool(mcp_client, "delete_actor", {"name": actor_name})


# =============================================================================
# Blueprint CRUD E2E
# =============================================================================


@pytest.mark.asyncio
async def test_blueprint_crud_e2e(mcp_client):
    """Blueprint lifecycle: create → read → compile → add component → remove → delete."""
    bp_name = "_E2E_Blueprint"
    bp_path = f"/Game/Blueprints/{bp_name}"
    comp_name = "_E2E_Mesh"

    async with mcp_client:
        # Create blueprint
        result = await call_tool(mcp_client, "create_blueprint", {"name": bp_name})
        assert result["name"] == bp_name

        # Read content
        result = await call_tool(mcp_client, "read_blueprint_content", {
            "blueprint_path": bp_path,
        })
        assert result["blueprint_name"] == bp_name

        # Compile
        result = await call_tool(mcp_client, "compile_blueprint", {
            "blueprint_name": bp_name,
        })
        assert result["compiled"] is True

        # Add component
        result = await call_tool(mcp_client, "add_component_to_blueprint", {
            "blueprint_name": bp_name,
            "component_class": "StaticMeshComponent",
            "component_name": comp_name,
        })
        assert result["status"] == "success"

        # Read components
        result = await call_tool(mcp_client, "read_components_from_blueprint", {
            "blueprint_name": bp_name,
        })
        names = [c["name"] for c in result["components"]]
        assert comp_name in names

        # Remove component
        result = await call_tool(mcp_client, "remove_component_from_blueprint", {
            "blueprint_name": bp_name, "component_name": comp_name,
        })
        assert result["status"] == "success"

        # Delete blueprint
        result = await call_tool(mcp_client, "delete_blueprint", {
            "blueprint_path": bp_path, "force": True,
        })
        assert result["status"] == "success"
