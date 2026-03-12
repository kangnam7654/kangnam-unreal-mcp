"""Blueprint system tools: create_blueprint, compile, read_blueprint_content, add_component, set_static_mesh, set_physics."""
import logging
from typing import Any, Callable, Dict, List

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("UnrealMCP.Tools.blueprints")


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    @mcp.tool()
    def create_blueprint(name: str, parent_class: str) -> Dict[str, Any]:
        """Create a new Blueprint class."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            response = unreal.send_command("create_blueprint", {"name": name, "parent_class": parent_class})
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"create_blueprint error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_component_to_blueprint(
        blueprint_name: str,
        component_type: str,
        component_name: str,
        location: List[float] = None,
        rotation: List[float] = None,
        scale: List[float] = None,
        component_properties: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """Add a component to a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {
                "blueprint_name": blueprint_name,
                "component_type": component_type,
                "component_name": component_name,
                "location": location or [],
                "rotation": rotation or [],
                "scale": scale or [],
                "component_properties": component_properties or {},
            }
            response = unreal.send_command("add_component_to_blueprint", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"add_component_to_blueprint error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_static_mesh_properties(
        blueprint_name: str,
        component_name: str,
        static_mesh: str = "/Engine/BasicShapes/Cube.Cube",
    ) -> Dict[str, Any]:
        """Set static mesh properties on a StaticMeshComponent."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {"blueprint_name": blueprint_name, "component_name": component_name, "static_mesh": static_mesh}
            response = unreal.send_command("set_static_mesh_properties", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"set_static_mesh_properties error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_physics_properties(
        blueprint_name: str,
        component_name: str,
        simulate_physics: bool = True,
        gravity_enabled: bool = True,
        mass: float = 1,
        linear_damping: float = 0.01,
        angular_damping: float = 0,
    ) -> Dict[str, Any]:
        """Set physics properties on a component."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {
                "blueprint_name": blueprint_name,
                "component_name": component_name,
                "simulate_physics": simulate_physics,
                "gravity_enabled": gravity_enabled,
                "mass": mass,
                "linear_damping": linear_damping,
                "angular_damping": angular_damping,
            }
            response = unreal.send_command("set_physics_properties", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"set_physics_properties error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def compile_blueprint(blueprint_name: str) -> Dict[str, Any]:
        """Compile a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            response = unreal.send_command("compile_blueprint", {"blueprint_name": blueprint_name})
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"compile_blueprint error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def read_blueprint_content(
        blueprint_path: str,
        include_event_graph: bool = True,
        include_functions: bool = True,
        include_variables: bool = True,
        include_components: bool = True,
        include_interfaces: bool = True,
    ) -> Dict[str, Any]:
        """Read and analyze the complete content of a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {
                "blueprint_path": blueprint_path,
                "include_event_graph": include_event_graph,
                "include_functions": include_functions,
                "include_variables": include_variables,
                "include_components": include_components,
                "include_interfaces": include_interfaces,
            }
            response = unreal.send_command("read_blueprint_content", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"read_blueprint_content error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def analyze_blueprint_graph(
        blueprint_path: str,
        graph_name: str = "EventGraph",
        include_node_details: bool = True,
        include_pin_connections: bool = True,
        trace_execution_flow: bool = True,
    ) -> Dict[str, Any]:
        """Analyze a specific graph within a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {
                "blueprint_path": blueprint_path,
                "graph_name": graph_name,
                "include_node_details": include_node_details,
                "include_pin_connections": include_pin_connections,
                "trace_execution_flow": trace_execution_flow,
            }
            response = unreal.send_command("analyze_blueprint_graph", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"analyze_blueprint_graph error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_blueprint_variable_details(
        blueprint_path: str,
        variable_name: str = None,
    ) -> Dict[str, Any]:
        """Get detailed information about Blueprint variables."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {"blueprint_path": blueprint_path, "variable_name": variable_name}
            response = unreal.send_command("get_blueprint_variable_details", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"get_blueprint_variable_details error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def get_blueprint_function_details(
        blueprint_path: str,
        function_name: str = None,
        include_graph: bool = True,
    ) -> Dict[str, Any]:
        """Get detailed information about Blueprint functions."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            params = {
                "blueprint_path": blueprint_path,
                "function_name": function_name,
                "include_graph": include_graph,
            }
            response = unreal.send_command("get_blueprint_function_details", params)
            return response or {"success": False, "message": "No response from Unreal"}
        except Exception as e:
            logger.error(f"get_blueprint_function_details error: {e}")
            return {"success": False, "message": str(e)}
