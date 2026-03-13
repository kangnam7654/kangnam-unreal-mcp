"""Blueprint Component CRD tools.

Commands: add_component_to_blueprint, remove_component_from_blueprint,
          read_components_from_blueprint
"""

import json
from typing import Any
import ue_connection

_CATEGORY = "BlueprintComponent"


@mcp.tool
def add_component_to_blueprint(
    blueprint_name: str,
    component_class: str,
    component_name: str | None = None,
    parent_component: str | None = None,
) -> str:
    """Add a component to a Blueprint's component hierarchy (SCS).

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")
        component_class: Component class name (e.g. "StaticMeshComponent", "BoxCollisionComponent")
        component_name: Optional name for the component (auto-generated if omitted)
        parent_component: Optional parent component name to attach under (added as root if omitted)

    The Blueprint is automatically recompiled after adding the component.
    """
    params: dict[str, Any] = {
        "blueprint_name": blueprint_name,
        "component_class": component_class,
    }
    if component_name is not None:
        params["component_name"] = component_name
    if parent_component is not None:
        params["parent_component"] = parent_component

    result = ue_connection.send_command("add_component_to_blueprint", params, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def remove_component_from_blueprint(blueprint_name: str, component_name: str) -> str:
    """Remove a component from a Blueprint's component hierarchy (SCS).

    Args:
        blueprint_name: Blueprint name or full path
        component_name: Exact name of the component to remove

    Children of the removed component are re-parented to its parent (or promoted to root).
    The default scene root cannot be removed. The Blueprint is automatically recompiled.
    """
    result = ue_connection.send_command("remove_component_from_blueprint", {
        "blueprint_name": blueprint_name,
        "component_name": component_name,
    }, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def read_components_from_blueprint(blueprint_name: str) -> str:
    """Read all components in a Blueprint's component hierarchy (SCS).

    Args:
        blueprint_name: Blueprint name or full path

    Returns a list of components with name, class, is_root flag, and parent info.
    """
    result = ue_connection.send_command("read_components_from_blueprint", {"blueprint_name": blueprint_name}, category_name=_CATEGORY)
    return json.dumps(result, indent=2, ensure_ascii=False)
