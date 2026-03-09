"""StaticMesh query tools.

Commands: get_static_meshes, find_static_meshes_by_name
"""

import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from . import ue_connection


def register_tools(mcp: FastMCP):
    """Register StaticMesh tools with the MCP server."""

    @mcp.tool
    def get_static_meshes(
        search_path: Optional[str] = None,
        include_engine_meshes: Optional[bool] = None,
    ) -> str:
        """Get available static mesh assets in the project.

        Args:
            search_path: Asset path to search in (default: "/Game/")
            include_engine_meshes: Include built-in Engine meshes like Cube, Sphere (default: true)

        Returns a list of static meshes with name, path, and package.
        """
        params: Dict[str, Any] = {}
        if search_path is not None:
            params["search_path"] = search_path
        if include_engine_meshes is not None:
            params["include_engine_meshes"] = include_engine_meshes

        result = ue_connection.execute("get_static_meshes", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def find_static_meshes_by_name(
        search_text: str,
        include_engine_meshes: Optional[bool] = None,
    ) -> str:
        """Find static mesh assets by name.

        Args:
            search_text: Text to search for in mesh names (case-sensitive, partial match)
            include_engine_meshes: Include built-in Engine meshes (default: true)

        Returns matching static meshes with name, path, and package.
        """
        params: Dict[str, Any] = {"search_text": search_text}
        if include_engine_meshes is not None:
            params["include_engine_meshes"] = include_engine_meshes

        result = ue_connection.execute("find_static_meshes_by_name", params)
        return json.dumps(result, indent=2, ensure_ascii=False)
