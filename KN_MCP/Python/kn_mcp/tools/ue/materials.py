"""Materials: get_available_materials, apply_material_to_actor, apply_material_to_blueprint, get_actor_material_info, set_mesh_material_color."""
import logging
from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.materials")


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    @mcp.tool()
    def get_available_materials(
        search_path: str = "/Game/",
        include_engine_materials: bool = True,
    ) -> dict[str, Any]:
        """Get a list of available materials in the project."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {"search_path": search_path, "include_engine_materials": include_engine_materials}
            response = unreal.send_command("Material_get_available_materials", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"get_available_materials error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def apply_material_to_actor(
        actor_name: str,
        material_path: str,
        material_slot: int = 0,
    ) -> dict[str, Any]:
        """Apply a specific material to an actor in the level."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {"actor_name": actor_name, "material_path": material_path, "material_slot": material_slot}
            response = unreal.send_command("Material_apply_material_to_actor", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"apply_material_to_actor error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def apply_material_to_blueprint(
        blueprint_name: str,
        component_name: str,
        material_path: str,
        material_slot: int = 0,
    ) -> dict[str, Any]:
        """Apply a specific material to a component in a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "material_path": material_path,
                "material_slot": material_slot,
            }
            response = unreal.send_command("Material_apply_material_to_blueprint", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"apply_material_to_blueprint error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_actor_material_info(actor_name: str) -> dict[str, Any]:
        """Get information about the materials currently applied to an actor."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {"actor_name": actor_name}
            response = unreal.send_command("Material_get_actor_material_info", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"get_actor_material_info error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_mesh_material_color(
        blueprint_name: str,
        component_name: str,
        color: list[float],
        material_path: str = "/Engine/BasicShapes/BasicShapeMaterial",
        parameter_name: str = "BaseColor",
        material_slot: int = 0,
    ) -> dict[str, Any]:
        """Set material color on a mesh component (BaseColor and Color parameters)."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            if not isinstance(color, list) or len(color) != 4:
                return {"success": False, "message": "Invalid color format. Must be a list of 4 float values [R, G, B, A]."}
            color = [float(min(1.0, max(0.0, val))) for val in color]
            params_base = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "color": color,
                "material_path": material_path,
                "parameter_name": "BaseColor",
                "material_slot": material_slot,
            }
            response_base = unreal.send_command("Material_set_mesh_material_color", params_base)
            params_color = {**params_base, "parameter_name": "Color"}
            response_color = unreal.send_command("Material_set_mesh_material_color", params_color)
            if (response_base and response_base.get("status") == "success") or (response_color and response_color.get("status") == "success"):
                return {
                    "success": True,
                    "message": f"Color applied successfully to slot {material_slot}: {color}",
                    "base_color_result": response_base,
                    "color_result": response_color,
                    "material_slot": material_slot,
                }
            return {
                "success": False,
                "message": f"Failed to set color parameters on slot {material_slot}. BaseColor: {response_base}, Color: {response_color}",
            }
        except Exception as e:
            logger.error(f"set_mesh_material_color error: {e}")
            return {"success": False, "message": str(e)}
