"""Blueprint CRUD tools.

Commands: get_blueprints, find_blueprints_by_name, create_blueprint,
          read_blueprint_content, compile_blueprint, delete_blueprint,
          spawn_blueprint_actor
"""

import json
from typing import Any
import ue_connection

_CATEGORY = "Blueprint"


@mcp.tool
def get_blueprints(search_path: str | None = None) -> str:
    """Get all Blueprint assets in the project.

    Args:
        search_path: Asset path to search in (default: "/Game/"). Use to narrow scope.

    Returns a list of all Blueprint assets with their name, path, and package path.
    """
    params: dict[str, Any] = {}
    if search_path is not None:
        params["search_path"] = search_path

    result = ue_connection.send_command("get_blueprints", params, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def find_blueprints_by_name(search_text: str) -> str:
    """Find Blueprint assets by partial name match.

    Args:
        search_text: Text to search for in Blueprint names (partial match, case-sensitive)

    Returns a list of matching Blueprints with their name, path, and package path.
    """
    result = ue_connection.send_command("find_blueprints_by_name", {"search_text": search_text}, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def create_blueprint(name: str, parent_class: str | None = None) -> str:
    """Create a new Blueprint asset in Unreal Engine.

    Args:
        name: Blueprint asset name (will be created at /Game/Blueprints/<name>)
        parent_class: Parent class name (e.g. "Actor", "Pawn"). Defaults to "Actor".

    Creates a new Blueprint asset and registers it in the asset registry.
    """
    params: dict[str, Any] = {"name": name}
    if parent_class is not None:
        params["parent_class"] = parent_class

    result = ue_connection.send_command("create_blueprint", params, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def read_blueprint_content(
    blueprint_name: str,
    include_event_graph: bool | None = None,
    include_functions: bool | None = None,
    include_variables: bool | None = None,
    include_interfaces: bool | None = None,
) -> str:
    """Read the content/structure of a Blueprint asset.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")
        include_event_graph: Include event graph info (default: true)
        include_functions: Include function list (default: true)
        include_variables: Include variable list (default: true)
        include_interfaces: Include implemented interfaces (default: true)

    Returns detailed information about the Blueprint's variables, functions,
    event graph, and interfaces.
    For component info, use read_components_from_blueprint() instead.
    """
    params: dict[str, Any] = {"blueprint_name": blueprint_name}
    if include_event_graph is not None:
        params["include_event_graph"] = include_event_graph
    if include_functions is not None:
        params["include_functions"] = include_functions
    if include_variables is not None:
        params["include_variables"] = include_variables
    if include_interfaces is not None:
        params["include_interfaces"] = include_interfaces

    result = ue_connection.send_command("read_blueprint_content", params, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def compile_blueprint(blueprint_name: str) -> str:
    """Compile a Blueprint asset.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")

    Compiles the Blueprint to update its generated class.
    """
    result = ue_connection.send_command("compile_blueprint", {"blueprint_name": blueprint_name}, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def delete_blueprint(blueprint_name: str, force: bool | None = None) -> str:
    """Delete a Blueprint asset from the project.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")
        force: If true, delete even if other assets reference this Blueprint.
               If false (default), returns error with list of referencers.

    WARNING: Deleting a Blueprint that is referenced by other assets may break those assets.
    """
    params: dict[str, Any] = {"blueprint_name": blueprint_name}
    if force is not None:
        params["force"] = force

    result = ue_connection.send_command("delete_blueprint", params, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def spawn_blueprint_actor(
    blueprint_name: str,
    name: str,
    location: list[float] | None = None,
    rotation: list[float] | None = None,
    scale: list[float] | None = None,
) -> str:
    """Spawn an instance of a Blueprint in the level.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")
        name: Unique name for the spawned actor
        location: [x, y, z] world position (default: [0, 0, 0])
        rotation: [pitch, yaw, roll] in degrees (default: [0, 0, 0])
        scale: [x, y, z] scale factors (default: [1, 1, 1])

    The Blueprint must be compiled before spawning.
    Name must be unique in the level.
    """
    params: dict[str, Any] = {
        "blueprint_name": blueprint_name,
        "name": name,
    }
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale

    result = ue_connection.send_command("spawn_blueprint_actor", params, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)
