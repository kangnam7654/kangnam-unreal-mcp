"""Blueprint variable tools.

Commands: add_variable_to_blueprint, remove_variable_from_blueprint
"""

import json
from typing import Optional, Dict, Any
from fastmcp import FastMCP
import ue_connection

_APP = "WN_MCP_WORLD"


def register_tools(mcp: FastMCP):
    """Register BlueprintVariable tools with the MCP server."""

    @mcp.tool
    def add_variable_to_blueprint(
        blueprint_name: str,
        variable_name: str,
        variable_type: str,
        default_value: Optional[str] = None,
        is_instance_editable: Optional[bool] = None,
    ) -> str:
        """Add a member variable to a Blueprint.

        Args:
            blueprint_name: Blueprint name or full path
            variable_name: Name for the new variable
            variable_type: Type — Bool, Int, Float, String, Name, Text, Vector, Rotator, Transform
            default_value: Default value as string (e.g. "100.0", "true", "1.0,2.0,3.0")
            is_instance_editable: Expose in Details panel (default: false)

        The Blueprint is automatically marked as structurally modified.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
            "variable_type": variable_type,
        }
        if default_value is not None:
            params["default_value"] = default_value
        if is_instance_editable is not None:
            params["is_instance_editable"] = is_instance_editable

        result = ue_connection.execute("add_variable_to_blueprint", params, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def remove_variable_from_blueprint(
        blueprint_name: str,
        variable_name: str,
    ) -> str:
        """Remove a member variable from a Blueprint.

        Args:
            blueprint_name: Blueprint name or full path
            variable_name: Name of the variable to remove

        The Blueprint is automatically marked as structurally modified.
        """
        result = ue_connection.execute("remove_variable_from_blueprint", {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
        }, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)
