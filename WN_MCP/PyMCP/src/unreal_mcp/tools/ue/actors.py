"""Actor management tools: get_actors_in_level, find_actors_by_name, delete_actor, set_actor_transform."""
import logging
from typing import Any, Callable, Dict, List

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.actors")


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    @mcp.tool()
    def get_actors_in_level(random_string: str = "") -> Dict[str, Any]:
        """Get a list of all actors in the current level."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            response = unreal.send_command("get_actors_in_level", {})
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"get_actors_in_level error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def find_actors_by_name(pattern: str) -> Dict[str, Any]:
        """Find actors by name pattern."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            response = unreal.send_command("find_actors_by_name", {"pattern": pattern})
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"find_actors_by_name error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_actor(name: str) -> Dict[str, Any]:
        """Delete an actor by name."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            from helpers.actor_name_manager import safe_delete_actor
            response = safe_delete_actor(unreal, name)
            return response
        except Exception as e:
            logger.error(f"delete_actor error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_actor_transform(
        name: str,
        location: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None,
    ) -> Dict[str, Any]:
        """Set the transform of an actor."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {"name": name}
            if location is not None:
                params["location"] = location
            if rotation is not None:
                params["rotation"] = rotation
            if scale is not None:
                params["scale"] = scale
            response = unreal.send_command("set_actor_transform", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"set_actor_transform error: {e}")
            return {"success": False, "message": str(e)}
