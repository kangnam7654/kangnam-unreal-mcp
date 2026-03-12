"""Component Property tools.

Commands: set_static_mesh_properties, set_physics_properties
"""

import json
from typing import Optional, Dict, Any
import ue_connection

_APP = "WN_MCP_WORLD"


@mcp.tool
def set_static_mesh_properties(
    blueprint_name: str,
    component_name: str,
    static_mesh: Optional[str] = None,
    material: Optional[str] = None,
) -> str:
    """Set static mesh and material on a Blueprint's StaticMeshComponent.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")
        component_name: Name of the StaticMeshComponent to modify
        static_mesh: Asset path to the static mesh (e.g. "/Engine/BasicShapes/Cube.Cube")
        material: Asset path to the material to apply

    At least one of static_mesh or material must be provided.
    The Blueprint is automatically marked as modified.
    """
    params: Dict[str, Any] = {
        "blueprint_name": blueprint_name,
        "component_name": component_name,
    }
    if static_mesh is not None:
        params["static_mesh"] = static_mesh
    if material is not None:
        params["material"] = material

    result = ue_connection.execute("set_static_mesh_properties", params, app_name=_APP)
    return json.dumps(result, indent=2, ensure_ascii=False)

@mcp.tool
def set_physics_properties(
    blueprint_name: str,
    component_name: str,
    simulate_physics: Optional[bool] = None,
    mass: Optional[float] = None,
    linear_damping: Optional[float] = None,
    angular_damping: Optional[float] = None,
) -> str:
    """Set physics properties on a Blueprint's PrimitiveComponent.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")
        component_name: Name of the PrimitiveComponent to modify
        simulate_physics: Enable/disable physics simulation
        mass: Mass override in kilograms
        linear_damping: Linear damping value (resistance to linear movement)
        angular_damping: Angular damping value (resistance to rotation)

    Only provided properties are updated; others remain unchanged.
    The Blueprint is automatically marked as modified.
    """
    params: Dict[str, Any] = {
        "blueprint_name": blueprint_name,
        "component_name": component_name,
    }
    if simulate_physics is not None:
        params["simulate_physics"] = simulate_physics
    if mass is not None:
        params["mass"] = mass
    if linear_damping is not None:
        params["linear_damping"] = linear_damping
    if angular_damping is not None:
        params["angular_damping"] = angular_damping

    result = ue_connection.execute("set_physics_properties", params, app_name=_APP)
    return json.dumps(result, indent=2, ensure_ascii=False)
