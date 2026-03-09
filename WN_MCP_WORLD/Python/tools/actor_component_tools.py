"""Actor Component CRD tools.

Commands: add_component_to_actor, remove_component_from_actor, read_components_from_actor
"""

import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from . import ue_connection


def register_tools(mcp: FastMCP):
    """Register Actor Component CRD tools with the MCP server."""

    @mcp.tool
    def add_component_to_actor(
        name: str,
        component_class: str,
        component_name: Optional[str] = None,
    ) -> str:
        """Add a component to an existing actor in the level.

        Args:
            name: Exact name of the target actor
            component_class: Component class name (e.g. "StaticMeshComponent", "PointLightComponent")
            component_name: Optional name for the new component (auto-generated if omitted)

        SceneComponents are automatically attached to the actor's root component.
        """
        params: Dict[str, Any] = {"name": name, "component_class": component_class}
        if component_name is not None:
            params["component_name"] = component_name

        result = ue_connection._ue_execute("add_component_to_actor", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def remove_component_from_actor(name: str, component_name: str) -> str:
        """Remove a component from an actor in the level.

        Args:
            name: Exact name of the target actor
            component_name: Exact name of the component to remove

        The root component cannot be removed. Use delete_actor() to remove the entire actor.
        """
        result = ue_connection._ue_execute("remove_component_from_actor", {
            "name": name,
            "component_name": component_name,
        })
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def read_components_from_actor(name: str) -> str:
        """Read all components attached to an actor.

        Args:
            name: Exact name of the actor to inspect

        Returns a list of components with name, class, is_root flag,
        and transform info (relative_location/rotation/scale) for SceneComponents.
        """
        result = ue_connection._ue_execute("read_components_from_actor", {"name": name})
        return json.dumps(result, indent=2, ensure_ascii=False)
