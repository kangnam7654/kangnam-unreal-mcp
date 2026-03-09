"""Material CRUD tools.

Commands: get_available_materials, apply_material_to_actor, apply_material_to_blueprint,
          get_actor_material_info, get_blueprint_material_info, set_mesh_material_color
"""

import json
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
from . import ue_connection


def register_tools(mcp: FastMCP):
    """Register Material tools with the MCP server."""

    @mcp.tool
    def get_available_materials(
        search_path: Optional[str] = None,
        include_engine_materials: Optional[bool] = None,
    ) -> str:
        """Get available material assets in the project.

        Args:
            search_path: Asset path to search in (default: "/Game/")
            include_engine_materials: Include built-in Engine materials (default: true)

        Returns a list of materials with name, path, package, and class.
        """
        params: Dict[str, Any] = {}
        if search_path is not None:
            params["search_path"] = search_path
        if include_engine_materials is not None:
            params["include_engine_materials"] = include_engine_materials

        result = ue_connection._ue_execute("get_available_materials", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def apply_material_to_actor(
        actor_name: str,
        material_path: str,
        material_slot: Optional[int] = None,
    ) -> str:
        """Apply a material to an actor's StaticMeshComponents in the level.

        Args:
            actor_name: Exact name of the actor
            material_path: Full asset path to the material (e.g. "/Engine/BasicShapes/BasicShapeMaterial")
            material_slot: Material slot index (default: 0)

        Applies the material to all StaticMeshComponents on the actor.
        """
        params: Dict[str, Any] = {
            "actor_name": actor_name,
            "material_path": material_path,
        }
        if material_slot is not None:
            params["material_slot"] = material_slot

        result = ue_connection._ue_execute("apply_material_to_actor", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def apply_material_to_blueprint(
        blueprint_name: str,
        component_name: str,
        material_path: str,
        material_slot: Optional[int] = None,
    ) -> str:
        """Apply a material to a Blueprint component.

        Args:
            blueprint_name: Blueprint name or full path
            component_name: Name of the PrimitiveComponent to modify
            material_path: Full asset path to the material
            material_slot: Material slot index (default: 0)

        The Blueprint is automatically marked as modified.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "material_path": material_path,
        }
        if material_slot is not None:
            params["material_slot"] = material_slot

        result = ue_connection._ue_execute("apply_material_to_blueprint", params)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def get_actor_material_info(actor_name: str) -> str:
        """Get material information for an actor's mesh components.

        Args:
            actor_name: Exact name of the actor

        Returns material slot info (name, path, class) for all StaticMeshComponents.
        """
        result = ue_connection._ue_execute("get_actor_material_info", {"actor_name": actor_name})
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def get_blueprint_material_info(
        blueprint_name: str,
        component_name: str,
    ) -> str:
        """Get material information for a Blueprint's StaticMeshComponent.

        Args:
            blueprint_name: Blueprint name or full path
            component_name: Name of the StaticMeshComponent to inspect

        Returns material slot info and whether a static mesh is assigned.
        """
        result = ue_connection._ue_execute("get_blueprint_material_info", {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
        })
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def set_mesh_material_color(
        blueprint_name: str,
        component_name: str,
        color: List[float],
        material_slot: Optional[int] = None,
        parameter_name: Optional[str] = None,
        material_path: Optional[str] = None,
    ) -> str:
        """Set a color parameter on a Blueprint component's material.

        Args:
            blueprint_name: Blueprint name or full path
            component_name: Name of the PrimitiveComponent
            color: [R, G, B] or [R, G, B, A] color values (0.0 to 1.0)
            material_slot: Material slot index (default: 0)
            parameter_name: Shader parameter name to set (default: "BaseColor")
            material_path: Optional base material path to use

        Creates a Dynamic Material Instance and sets the specified color parameter.
        The Blueprint is automatically marked as modified.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "component_name": component_name,
            "color": color,
        }
        if material_slot is not None:
            params["material_slot"] = material_slot
        if parameter_name is not None:
            params["parameter_name"] = parameter_name
        if material_path is not None:
            params["material_path"] = material_path

        result = ue_connection._ue_execute("set_mesh_material_color", params)
        return json.dumps(result, indent=2, ensure_ascii=False)
