"""Actor CRUD tools.

Commands: get_actors_in_level, find_actors_by_name, spawn_actor,
          delete_actor, set_actor_transform, read_actor_content
"""

import json
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
from . import ue_connection


def register_tools(mcp: FastMCP):
    """Register Actor CRUD tools with the MCP server."""

    @mcp.tool
    def get_actors_in_level() -> str:
        """Get all actors currently in the Unreal Engine level.

        Returns a list of all actors with their name, class, location, rotation, and scale.
        Use this to inspect the current state of the level.
        """
        result = ue_connection._ue_execute("get_actors_in_level")
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def find_actors_by_name(search_text: str) -> str:
        """Find actors in the level by partial name match.

        Args:
            search_text: Text to search for in actor names (partial match, case-sensitive)

        Returns a list of matching actors with their name, class, location, rotation, and scale.
        """
        result = ue_connection._ue_execute("find_actors_by_name", {"search_text": search_text})
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def spawn_actor(
        type: str,
        name: str,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
    ) -> str:
        """Spawn a new actor in the Unreal Engine level.

        Args:
            type: Actor class name (e.g. "StaticMeshActor", "PointLight", "CameraActor")
            name: Unique name for the new actor
            location: [x, y, z] world position (default: [0, 0, 0])
            rotation: [pitch, yaw, roll] in degrees (default: [0, 0, 0])
            scale: [x, y, z] scale factors (default: [1, 1, 1])

        Creates the actor at the specified transform. Name must be unique in the level.
        """
        params: Dict[str, Any] = {"type": type, "name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale

        result = ue_connection._ue_execute("spawn_actor", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def delete_actor(name: str) -> str:
        """Delete an actor from the Unreal Engine level.

        Args:
            name: Exact name of the actor to delete

        Permanently removes the actor from the level.
        """
        result = ue_connection._ue_execute("delete_actor", {"name": name})
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def set_actor_transform(
        name: str,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
    ) -> str:
        """Set the transform (position/rotation/scale) of an existing actor.

        Args:
            name: Exact name of the actor to modify
            location: [x, y, z] new world position (omit to keep current)
            rotation: [pitch, yaw, roll] new rotation in degrees (omit to keep current)
            scale: [x, y, z] new scale factors (omit to keep current)

        Only provided transform components are updated; others remain unchanged.
        """
        params: Dict[str, Any] = {"name": name}
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale

        result = ue_connection._ue_execute("set_actor_transform", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def read_actor_content(name: str) -> str:
        """Read detailed content of a single actor.

        Args:
            name: Exact name of the actor to inspect

        Returns name, class, and transform (location/rotation/scale).
        For component info, use read_components_from_actor() instead.
        """
        result = ue_connection._ue_execute("read_actor_content", {"name": name})
        return json.dumps(result, indent=2, ensure_ascii=False)
