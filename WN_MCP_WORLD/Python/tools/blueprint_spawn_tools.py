"""Blueprint Spawn tools.

Commands: spawn_blueprint_actor
"""

import json
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
from . import ue_connection


def register_tools(mcp: FastMCP):
    """Register Blueprint Spawn tools with the MCP server."""

    @mcp.tool
    def spawn_blueprint_actor(
        blueprint_name: str,
        name: str,
        location: Optional[List[float]] = None,
        rotation: Optional[List[float]] = None,
        scale: Optional[List[float]] = None,
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
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "name": name,
        }
        if location is not None:
            params["location"] = location
        if rotation is not None:
            params["rotation"] = rotation
        if scale is not None:
            params["scale"] = scale

        result = ue_connection.execute("spawn_blueprint_actor", params)
        return json.dumps(result, indent=2, ensure_ascii=False)
