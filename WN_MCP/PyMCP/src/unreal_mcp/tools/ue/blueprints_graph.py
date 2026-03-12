"""Blueprint graph tools: add_node, connect_nodes, create_variable, set_blueprint_variable_properties, events, delete_node, set_node_property, function CRUD."""
import logging
from typing import Any, Callable, Dict, Optional

from mcp.server.fastmcp import FastMCP

from unreal_mcp.helpers.blueprint_graph import (
    node_manager, 
    variable_manager, 
    connector_manager, 
    event_manager, 
    node_deleter, 
    node_properties, 
    function_manager, 
    function_io
)

logger = logging.getLogger("UnrealMCP.Tools.blueprints_graph")


def register_tools(mcp: FastMCP, get_connection: Callable) -> None:
    @mcp.tool()
    def add_node(
        blueprint_name: str,
        node_type: str,
        pos_x: float = 0,
        pos_y: float = 0,
        message: str = "",
        event_type: str = "BeginPlay",
        variable_name: str = "",
        target_function: str = "",
        target_blueprint: Optional[str] = None,
        function_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add a node to a Blueprint graph. Supports 23+ node types (Branch, VariableGet, Print, etc.)."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            node_params = {"pos_x": pos_x, "pos_y": pos_y}
            if message:
                node_params["message"] = message
            if event_type:
                node_params["event_type"] = event_type
            if variable_name:
                node_params["variable_name"] = variable_name
            if target_function:
                node_params["target_function"] = target_function
            if target_blueprint:
                node_params["target_blueprint"] = target_blueprint
            if function_name:
                node_params["function_name"] = function_name
            return node_manager.add_node(unreal, blueprint_name, node_type, node_params)
        except Exception as e:
            logger.error(f"add_node error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def connect_nodes(
        blueprint_name: str,
        source_node_id: str,
        source_pin_name: str,
        target_node_id: str,
        target_pin_name: str,
        function_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Connect two nodes in a Blueprint graph."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return connector_manager.connect_nodes(
                unreal, blueprint_name, source_node_id, source_pin_name, target_node_id, target_pin_name, function_name
            )
        except Exception as e:
            logger.error(f"connect_nodes error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_variable(
        blueprint_name: str,
        variable_name: str,
        variable_type: str,
        default_value: Any = None,
        is_public: bool = False,
        tooltip: str = "",
        category: str = "Default",
    ) -> Dict[str, Any]:
        """Create a variable in a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return variable_manager.create_variable(
                unreal, blueprint_name, variable_name, variable_type, default_value, is_public, tooltip, category
            )
        except Exception as e:
            logger.error(f"create_variable error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_blueprint_variable_properties(
        blueprint_name: str,
        variable_name: str,
        var_name: Optional[str] = None,
        var_type: Optional[str] = None,
        is_blueprint_readable: Optional[bool] = None,
        is_blueprint_writable: Optional[bool] = None,
        is_public: Optional[bool] = None,
        is_editable_in_instance: Optional[bool] = None,
        tooltip: Optional[str] = None,
        category: Optional[str] = None,
        default_value: Any = None,
        expose_on_spawn: Optional[bool] = None,
        expose_to_cinematics: Optional[bool] = None,
        slider_range_min: Optional[str] = None,
        slider_range_max: Optional[str] = None,
        value_range_min: Optional[str] = None,
        value_range_max: Optional[str] = None,
        units: Optional[str] = None,
        bitmask: Optional[bool] = None,
        bitmask_enum: Optional[str] = None,
        replication_enabled: Optional[bool] = None,
        replication_condition: Optional[int] = None,
        is_private: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Modify properties of an existing Blueprint variable."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return variable_manager.set_blueprint_variable_properties(
                unreal,
                blueprint_name,
                variable_name,
                var_name,
                var_type,
                is_blueprint_readable,
                is_blueprint_writable,
                is_public,
                is_editable_in_instance,
                tooltip,
                category,
                default_value,
                expose_on_spawn,
                expose_to_cinematics,
                slider_range_min,
                slider_range_max,
                value_range_min,
                value_range_max,
                units,
                bitmask,
                bitmask_enum,
                replication_enabled,
                replication_condition,
                is_private,
            )
        except Exception as e:
            logger.error(f"set_blueprint_variable_properties error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_event_node(
        blueprint_name: str,
        event_name: str,
        pos_x: float = 0,
        pos_y: float = 0,
    ) -> Dict[str, Any]:
        """Add an event node to a Blueprint graph (e.g. ReceiveBeginPlay, ReceiveTick)."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return event_manager.add_event_node(unreal, blueprint_name, event_name, pos_x, pos_y)
        except Exception as e:
            logger.error(f"add_event_node error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_node(
        blueprint_name: str,
        node_id: str,
        function_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Delete a node from a Blueprint graph."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return node_deleter.delete_node(unreal, blueprint_name, node_id, function_name)
        except Exception as e:
            logger.error(f"delete_node error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def set_node_property(
        blueprint_name: str,
        node_id: str,
        property_name: str = "",
        property_value: Any = None,
        function_name: Optional[str] = None,
        action: Optional[str] = None,
        pin_type: Optional[str] = None,
        pin_name: Optional[str] = None,
        enum_type: Optional[str] = None,
        new_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_function: Optional[str] = None,
        target_class: Optional[str] = None,
        event_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Set a property on a Blueprint node or perform semantic editing (add_pin, set_pin_type, etc.)."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            kwargs = {}
            if action is not None:
                if pin_type is not None:
                    kwargs["pin_type"] = pin_type
                if pin_name is not None:
                    kwargs["pin_name"] = pin_name
                if enum_type is not None:
                    kwargs["enum_type"] = enum_type
                if new_type is not None:
                    kwargs["new_type"] = new_type
                if target_type is not None:
                    kwargs["target_type"] = target_type
                if target_function is not None:
                    kwargs["target_function"] = target_function
                if target_class is not None:
                    kwargs["target_class"] = target_class
                if event_type is not None:
                    kwargs["event_type"] = event_type
            return node_properties.set_node_property(
                unreal, blueprint_name, node_id, property_name, property_value, function_name, action, **kwargs
            )
        except Exception as e:
            logger.error(f"set_node_property error: {e}", exc_info=True)
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def create_function(
        blueprint_name: str,
        function_name: str,
        return_type: str = "void",
    ) -> Dict[str, Any]:
        """Create a new function in a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return function_manager.create_function_handler(unreal, blueprint_name, function_name, return_type)
        except Exception as e:
            logger.error(f"create_function error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_function_input(
        blueprint_name: str,
        function_name: str,
        param_name: str,
        param_type: str,
        is_array: bool = False,
    ) -> Dict[str, Any]:
        """Add an input parameter to a Blueprint function."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return function_io.add_function_input_handler(
                unreal, blueprint_name, function_name, param_name, param_type, is_array
            )
        except Exception as e:
            logger.error(f"add_function_input error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def add_function_output(
        blueprint_name: str,
        function_name: str,
        param_name: str,
        param_type: str,
        is_array: bool = False,
    ) -> Dict[str, Any]:
        """Add an output parameter to a Blueprint function."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return function_io.add_function_output_handler(
                unreal, blueprint_name, function_name, param_name, param_type, is_array
            )
        except Exception as e:
            logger.error(f"add_function_output error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def delete_function(blueprint_name: str, function_name: str) -> Dict[str, Any]:
        """Delete a function from a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return function_manager.delete_function_handler(unreal, blueprint_name, function_name)
        except Exception as e:
            logger.error(f"delete_function error: {e}")
            return {"success": False, "message": str(e)}

    @mcp.tool()
    def rename_function(
        blueprint_name: str,
        old_function_name: str,
        new_function_name: str,
    ) -> Dict[str, Any]:
        """Rename a function in a Blueprint."""
        unreal = get_connection()
        if not unreal:
            return {"success": False, "message": "Failed to connect to Unreal Engine"}
        try:
            return function_manager.rename_function_handler(
                unreal, blueprint_name, old_function_name, new_function_name
            )
        except Exception as e:
            logger.error(f"rename_function error: {e}")
            return {"success": False, "message": str(e)}
