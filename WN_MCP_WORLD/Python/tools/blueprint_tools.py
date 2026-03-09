"""Blueprint CRUD tools.

Commands: get_blueprints, find_blueprints_by_name, create_blueprint,
          read_blueprint_content, compile_blueprint, delete_blueprint
"""

import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP
from . import ue_connection


def register_tools(mcp: FastMCP):
    """Register Blueprint CRUD tools with the MCP server."""

    @mcp.tool
    def get_blueprints(search_path: Optional[str] = None) -> str:
        """Get all Blueprint assets in the project.

        Args:
            search_path: Asset path to search in (default: "/Game/"). Use to narrow scope.

        Returns a list of all Blueprint assets with their name, path, and package path.
        """
        params: Dict[str, Any] = {}
        if search_path is not None:
            params["search_path"] = search_path

        result = ue_connection.execute("get_blueprints", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def find_blueprints_by_name(search_text: str) -> str:
        """Find Blueprint assets by partial name match.

        Args:
            search_text: Text to search for in Blueprint names (partial match, case-sensitive)

        Returns a list of matching Blueprints with their name, path, and package path.
        """
        result = ue_connection.execute("find_blueprints_by_name", {"search_text": search_text})
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def create_blueprint(name: str, parent_class: Optional[str] = None) -> str:
        """Create a new Blueprint asset in Unreal Engine.

        Args:
            name: Blueprint asset name (will be created at /Game/Blueprints/<name>)
            parent_class: Parent class name (e.g. "Actor", "Pawn"). Defaults to "Actor".

        Creates a new Blueprint asset and registers it in the asset registry.
        """
        params: Dict[str, Any] = {"name": name}
        if parent_class is not None:
            params["parent_class"] = parent_class

        result = ue_connection.execute("create_blueprint", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def read_blueprint_content(
        blueprint_path: str,
        include_event_graph: Optional[bool] = None,
        include_functions: Optional[bool] = None,
        include_variables: Optional[bool] = None,
        include_interfaces: Optional[bool] = None,
    ) -> str:
        """Read the content/structure of a Blueprint asset.

        Args:
            blueprint_path: Full asset path (e.g. "/Game/Blueprints/MyBP")
            include_event_graph: Include event graph info (default: true)
            include_functions: Include function list (default: true)
            include_variables: Include variable list (default: true)
            include_interfaces: Include implemented interfaces (default: true)

        Returns detailed information about the Blueprint's variables, functions,
        event graph, and interfaces.
        For component info, use read_components_from_blueprint() instead.
        """
        params: Dict[str, Any] = {"blueprint_path": blueprint_path}
        if include_event_graph is not None:
            params["include_event_graph"] = include_event_graph
        if include_functions is not None:
            params["include_functions"] = include_functions
        if include_variables is not None:
            params["include_variables"] = include_variables
        if include_interfaces is not None:
            params["include_interfaces"] = include_interfaces

        result = ue_connection.execute("read_blueprint_content", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def compile_blueprint(blueprint_name: str) -> str:
        """Compile a Blueprint asset.

        Args:
            blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")

        Compiles the Blueprint to update its generated class.
        """
        result = ue_connection.execute("compile_blueprint", {"blueprint_name": blueprint_name})
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def delete_blueprint(blueprint_path: str, force: Optional[bool] = None) -> str:
        """Delete a Blueprint asset from the project.

        Args:
            blueprint_path: Full asset path (e.g. "/Game/Blueprints/MyBP")
            force: If true, delete even if other assets reference this Blueprint.
                   If false (default), returns error with list of referencers.

        WARNING: Deleting a Blueprint that is referenced by other assets may break those assets.
        """
        params: Dict[str, Any] = {"blueprint_path": blueprint_path}
        if force is not None:
            params["force"] = force

        result = ue_connection.execute("delete_blueprint", params)
        return json.dumps(result, indent=2, ensure_ascii=False)
