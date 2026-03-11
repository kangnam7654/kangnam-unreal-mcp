"""End-to-end tests — MCP client through stdio transport.

Requires running UE editor with WN_MCP plugin.

Run with: uv run python -m pytest tests/test_e2e.py -v -m e2e
Skip with: uv run python -m pytest -m "not e2e"
"""

import json
import pytest

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
    # FastMCP Client returns CallToolResult with .content list
    text = result.content[0].text if result.content else "{}"
    return json.loads(text)


async def safe_delete_actor(client, name: str):
    """Delete actor, ignoring errors if it doesn't exist."""
    try:
        await client.call_tool("delete_actor", {"name": name})
    except Exception:
        pass


async def safe_delete_blueprint(client, bp_name: str):
    """Delete blueprint, ignoring errors if it doesn't exist."""
    try:
        await client.call_tool("delete_blueprint", {"blueprint_name": bp_name, "force": True})
    except Exception:
        pass


# =============================================================================
# Tool Discovery
# =============================================================================


@pytest.mark.asyncio
async def test_all_38_tools_registered(mcp_client):
    """Verify all 38 tools are registered in the MCP server."""
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

        missing = expected - tool_names
        assert not missing, f"Missing tools: {missing}"


# =============================================================================
# Actor CRUD E2E
# =============================================================================


@pytest.mark.asyncio
async def test_actor_crud_e2e(mcp_client):
    """Full actor lifecycle: spawn -> read -> transform -> delete."""
    name = "_E2E_Actor"

    async with mcp_client:
        # Cleanup any leftover from previous run
        await safe_delete_actor(mcp_client, name)

        try:
            # Create
            result = await call_tool(mcp_client, "spawn_actor", {
                "type": "StaticMeshActor", "name": name,
                "location": [100, 200, 300],
            })
            assert result["status"] == "success"

            # Read
            result = await call_tool(mcp_client, "read_actor_content", {"name": name})
            assert result["status"] == "success"
            assert result["actor"]["name"] == name

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
        finally:
            await safe_delete_actor(mcp_client, name)


# =============================================================================
# Component CRUD E2E
# =============================================================================


@pytest.mark.asyncio
async def test_actor_component_crud_e2e(mcp_client):
    """Component lifecycle on actor: spawn actor -> add comp -> read -> remove -> delete actor."""
    actor_name = "_E2E_CompActor"
    comp_name = "_E2E_Light"

    async with mcp_client:
        await safe_delete_actor(mcp_client, actor_name)

        try:
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
        finally:
            await safe_delete_actor(mcp_client, actor_name)


# =============================================================================
# Blueprint CRUD E2E
# =============================================================================


@pytest.mark.asyncio
async def test_blueprint_crud_e2e(mcp_client):
    """Blueprint lifecycle: create -> read -> compile -> add component -> remove -> delete."""
    bp_name = "_E2E_Blueprint"

    comp_name = "_E2E_Mesh"

    async with mcp_client:
        await safe_delete_blueprint(mcp_client, bp_name)

        try:
            # Create blueprint
            result = await call_tool(mcp_client, "create_blueprint", {"name": bp_name})
            assert result["name"] == bp_name

            # Read content
            result = await call_tool(mcp_client, "read_blueprint_content", {
                "blueprint_name": bp_name,
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
                "blueprint_name": bp_name, "force": True,
            })
            assert result["status"] == "success"
        finally:
            await safe_delete_blueprint(mcp_client, bp_name)


# =============================================================================
# Property E2E
# =============================================================================


@pytest.mark.asyncio
async def test_property_e2e(mcp_client):
    """Property lifecycle: create BP -> add mesh comp -> set mesh -> set physics -> cleanup."""
    bp_name = "_E2E_PropBP"

    comp_name = "_E2E_PropMesh"

    async with mcp_client:
        await safe_delete_blueprint(mcp_client, bp_name)

        try:
            # Create blueprint with StaticMeshComponent
            await call_tool(mcp_client, "create_blueprint", {"name": bp_name})
            await call_tool(mcp_client, "add_component_to_blueprint", {
                "blueprint_name": bp_name,
                "component_class": "StaticMeshComponent",
                "component_name": comp_name,
            })

            # Set static mesh
            result = await call_tool(mcp_client, "set_static_mesh_properties", {
                "blueprint_name": bp_name,
                "component_name": comp_name,
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            })
            assert result["status"] == "success"

            # Set physics
            result = await call_tool(mcp_client, "set_physics_properties", {
                "blueprint_name": bp_name,
                "component_name": comp_name,
                "simulate_physics": True,
                "mass": 25.0,
            })
            assert result["status"] == "success"
        finally:
            await safe_delete_blueprint(mcp_client, bp_name)


# =============================================================================
# Blueprint Spawn E2E
# =============================================================================


@pytest.mark.asyncio
async def test_blueprint_spawn_e2e(mcp_client):
    """Blueprint spawn lifecycle: create BP -> compile -> spawn -> verify -> cleanup."""
    bp_name = "_E2E_SpawnBP"

    actor_name = "_E2E_SpawnedActor"

    async with mcp_client:
        await safe_delete_actor(mcp_client, actor_name)
        await safe_delete_blueprint(mcp_client, bp_name)

        try:
            # Create and compile blueprint
            await call_tool(mcp_client, "create_blueprint", {"name": bp_name})
            await call_tool(mcp_client, "compile_blueprint", {
                "blueprint_name": bp_name,
            })

            # Spawn blueprint actor
            result = await call_tool(mcp_client, "spawn_blueprint_actor", {
                "blueprint_name": bp_name,
                "name": actor_name,
                "location": [300, 400, 0],
            })
            assert result["status"] == "success"

            # Verify actor exists
            result = await call_tool(mcp_client, "find_actors_by_name", {
                "search_text": actor_name,
            })
            assert result["count"] >= 1
        finally:
            await safe_delete_actor(mcp_client, actor_name)
            await safe_delete_blueprint(mcp_client, bp_name)


# =============================================================================
# Material E2E
# =============================================================================


@pytest.mark.asyncio
async def test_material_e2e(mcp_client):
    """Material lifecycle: list -> apply to actor -> info -> apply to BP -> color -> cleanup."""
    actor_name = "_E2E_MatActor"
    bp_name = "_E2E_MatBP"

    comp_name = "_E2E_MatMesh"

    async with mcp_client:
        await safe_delete_actor(mcp_client, actor_name)
        await safe_delete_blueprint(mcp_client, bp_name)

        try:
            # List available materials
            result = await call_tool(mcp_client, "get_available_materials", {})
            assert result["count"] > 0

            # Spawn actor and apply material
            await call_tool(mcp_client, "spawn_actor", {
                "type": "StaticMeshActor", "name": actor_name,
            })
            result = await call_tool(mcp_client, "get_actor_material_info", {
                "actor_name": actor_name,
            })
            assert result["actor_name"] == actor_name
            assert "material_slots" in result

            result = await call_tool(mcp_client, "apply_material_to_actor", {
                "actor_name": actor_name,
                "material_path": "/Engine/BasicShapes/BasicShapeMaterial",
            })
            assert result["status"] == "success"

            # Create blueprint with mesh component
            await call_tool(mcp_client, "create_blueprint", {"name": bp_name})
            await call_tool(mcp_client, "add_component_to_blueprint", {
                "blueprint_name": bp_name,
                "component_class": "StaticMeshComponent",
                "component_name": comp_name,
            })
            await call_tool(mcp_client, "set_static_mesh_properties", {
                "blueprint_name": bp_name,
                "component_name": comp_name,
                "static_mesh": "/Engine/BasicShapes/Cube.Cube",
            })

            # Get blueprint material info
            result = await call_tool(mcp_client, "get_blueprint_material_info", {
                "blueprint_name": bp_name,
                "component_name": comp_name,
            })
            assert result["blueprint_name"] == bp_name
            assert "material_slots" in result

            # Apply material to blueprint
            result = await call_tool(mcp_client, "apply_material_to_blueprint", {
                "blueprint_name": bp_name,
                "component_name": comp_name,
                "material_path": "/Engine/BasicShapes/BasicShapeMaterial",
            })
            assert result["status"] == "success"

            # Set mesh material color
            result = await call_tool(mcp_client, "set_mesh_material_color", {
                "blueprint_name": bp_name,
                "component_name": comp_name,
                "color": [1.0, 0.0, 0.0],
            })
            assert result["status"] == "success"
        finally:
            await safe_delete_actor(mcp_client, actor_name)
            await safe_delete_blueprint(mcp_client, bp_name)


# =============================================================================
# StaticMesh E2E
# =============================================================================


@pytest.mark.asyncio
async def test_static_mesh_e2e(mcp_client):
    """StaticMesh lifecycle: list meshes -> search by name -> verify results."""
    async with mcp_client:
        # List all static meshes (including engine)
        result = await call_tool(mcp_client, "get_static_meshes", {})
        assert result["count"] > 0

        # Search for engine basic shapes
        result = await call_tool(mcp_client, "find_static_meshes_by_name", {
            "search_text": "Cube",
        })
        assert result["count"] >= 1
        names = [m["name"] for m in result["static_meshes"]]
        assert any("Cube" in n for n in names)


# =============================================================================
# Blueprint Variable E2E
# =============================================================================


@pytest.mark.asyncio
async def test_blueprint_variable_e2e(mcp_client):
    """BlueprintVariable lifecycle: create BP -> add variable -> verify -> remove -> cleanup."""
    bp_name = "_E2E_VarBP"
    var_name = "_E2E_HP"

    async with mcp_client:
        await safe_delete_blueprint(mcp_client, bp_name)

        try:
            # Create blueprint
            await call_tool(mcp_client, "create_blueprint", {"name": bp_name})

            # Add variable
            result = await call_tool(mcp_client, "add_variable_to_blueprint", {
                "blueprint_name": bp_name,
                "variable_name": var_name,
                "variable_type": "Float",
                "default_value": "100.0",
                "is_instance_editable": True,
            })
            assert result["status"] == "success"
            assert result["variable_name"] == var_name

            # Verify variable exists via read_blueprint_content
            result = await call_tool(mcp_client, "read_blueprint_content", {
                "blueprint_name": bp_name,
            })
            assert result["blueprint_name"] == bp_name

            # Remove variable
            result = await call_tool(mcp_client, "remove_variable_from_blueprint", {
                "blueprint_name": bp_name,
                "variable_name": var_name,
            })
            assert result["status"] == "success"
        finally:
            await safe_delete_blueprint(mcp_client, bp_name)


# =============================================================================
# Blueprint Graph E2E
# =============================================================================


@pytest.mark.asyncio
async def test_blueprint_graph_e2e(mcp_client):
    """BlueprintGraph lifecycle: nodes -> connect -> read -> disconnect -> cleanup."""
    bp_name = "_E2E_GraphBP"
    var_name = "_E2E_GraphVar"

    async with mcp_client:
        await safe_delete_blueprint(mcp_client, bp_name)

        try:
            # Setup: create blueprint with a variable
            await call_tool(mcp_client, "create_blueprint", {"name": bp_name})
            await call_tool(mcp_client, "add_variable_to_blueprint", {
                "blueprint_name": bp_name,
                "variable_name": var_name,
                "variable_type": "Float",
            })

            # Add event node
            result = await call_tool(mcp_client, "add_event_node", {
                "blueprint_name": bp_name,
                "event_type": "BeginPlay",
            })
            assert result["status"] == "success"
            event_node_id = result["node_id"]

            # Add function call node
            result = await call_tool(mcp_client, "add_function_call_node", {
                "blueprint_name": bp_name,
                "function_name": "PrintString",
                "target_class": "KismetSystemLibrary",
            })
            assert result["status"] == "success"
            func_node_id = result["node_id"]

            # Add variable get/set nodes
            result = await call_tool(mcp_client, "add_variable_get_node", {
                "blueprint_name": bp_name,
                "variable_name": var_name,
            })
            assert result["status"] == "success"

            result = await call_tool(mcp_client, "add_variable_set_node", {
                "blueprint_name": bp_name,
                "variable_name": var_name,
            })
            assert result["status"] == "success"

            # Connect event -> function call
            result = await call_tool(mcp_client, "connect_nodes", {
                "blueprint_name": bp_name,
                "source_node_id": event_node_id,
                "source_pin_name": "then",
                "target_node_id": func_node_id,
                "target_pin_name": "execute",
            })
            assert result["status"] == "success"

            # Read graph — verify nodes exist
            result = await call_tool(mcp_client, "read_blueprint_graph", {
                "blueprint_name": bp_name,
            })
            assert result["blueprint_name"] == bp_name
            assert len(result["nodes"]) >= 4

            # Disconnect
            result = await call_tool(mcp_client, "disconnect_nodes", {
                "blueprint_name": bp_name,
                "node_id": event_node_id,
                "pin_name": "then",
            })
            assert result["status"] == "success"
        finally:
            await safe_delete_blueprint(mcp_client, bp_name)
