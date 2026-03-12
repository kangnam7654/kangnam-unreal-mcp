"""Blueprint graph tools (nodes, connections).

Commands: read_blueprint_graph, add_event_node, add_function_call_node,
          add_variable_get_node, add_variable_set_node, connect_nodes, disconnect_nodes
"""

import json
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
import ue_connection

_APP = "WN_MCP_WORLD"


def register_tools(mcp: FastMCP):
    """Register BlueprintGraph tools with the MCP server."""

    @mcp.tool
    def read_blueprint_graph(blueprint_name: str) -> str:
        """Read the EventGraph of a Blueprint in detail.

        Args:
            blueprint_name: Blueprint name or full path

        Returns nodes with node_id (GUID), class, title, position, and pins
        (including connection info). Use node_id and pin_name for connect_nodes.
        """
        result = ue_connection.execute("read_blueprint_graph", {
            "blueprint_name": blueprint_name,
        }, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def add_event_node(
        blueprint_name: str,
        event_type: str,
        node_position: Optional[List[int]] = None,
    ) -> str:
        """Add an event node to the Blueprint's EventGraph.

        Args:
            blueprint_name: Blueprint name or full path
            event_type: Event type — BeginPlay, Tick, EndPlay, ActorBeginOverlap,
                        ActorEndOverlap, AnyDamage, Hit
            node_position: [X, Y] position in graph (default: [0, 0])

        Returns node_id (GUID) and pins for use with connect_nodes.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "event_type": event_type,
        }
        if node_position is not None:
            params["node_position"] = node_position

        result = ue_connection.execute("add_event_node", params, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def add_function_call_node(
        blueprint_name: str,
        function_name: str,
        target_class: Optional[str] = None,
        node_position: Optional[List[int]] = None,
    ) -> str:
        """Add a function call node to the Blueprint's EventGraph.

        Args:
            blueprint_name: Blueprint name or full path
            function_name: Function name (e.g. "PrintString", "SetActorLocation", "Delay")
            target_class: Class owning the function (e.g. "KismetSystemLibrary").
                          If omitted, searches parent class, then common UE libraries.
            node_position: [X, Y] position in graph (default: [0, 0])

        Returns node_id (GUID) and pins for use with connect_nodes.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "function_name": function_name,
        }
        if target_class is not None:
            params["target_class"] = target_class
        if node_position is not None:
            params["node_position"] = node_position

        result = ue_connection.execute("add_function_call_node", params, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def add_variable_get_node(
        blueprint_name: str,
        variable_name: str,
        node_position: Optional[List[int]] = None,
    ) -> str:
        """Add a variable Getter node to the Blueprint's EventGraph.

        Args:
            blueprint_name: Blueprint name or full path
            variable_name: Name of a variable that exists in the Blueprint
            node_position: [X, Y] position in graph (default: [0, 0])

        Returns node_id (GUID) and pins for use with connect_nodes.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
        }
        if node_position is not None:
            params["node_position"] = node_position

        result = ue_connection.execute("add_variable_get_node", params, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def add_variable_set_node(
        blueprint_name: str,
        variable_name: str,
        node_position: Optional[List[int]] = None,
    ) -> str:
        """Add a variable Setter node to the Blueprint's EventGraph.

        Args:
            blueprint_name: Blueprint name or full path
            variable_name: Name of a variable that exists in the Blueprint
            node_position: [X, Y] position in graph (default: [0, 0])

        Returns node_id (GUID) and pins for use with connect_nodes.
        """
        params: Dict[str, Any] = {
            "blueprint_name": blueprint_name,
            "variable_name": variable_name,
        }
        if node_position is not None:
            params["node_position"] = node_position

        result = ue_connection.execute("add_variable_set_node", params, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def connect_nodes(
        blueprint_name: str,
        source_node_id: str,
        source_pin_name: str,
        target_node_id: str,
        target_pin_name: str,
    ) -> str:
        """Connect two pins in the Blueprint's EventGraph.

        Args:
            blueprint_name: Blueprint name or full path
            source_node_id: GUID of the source node (from add_*_node response)
            source_pin_name: Name of the output pin (e.g. "then", "ReturnValue")
            target_node_id: GUID of the target node
            target_pin_name: Name of the input pin (e.g. "execute", "InString")

        Common pin names: "execute" (exec in), "then" (exec out), "ReturnValue".
        """
        result = ue_connection.execute("connect_nodes", {
            "blueprint_name": blueprint_name,
            "source_node_id": source_node_id,
            "source_pin_name": source_pin_name,
            "target_node_id": target_node_id,
            "target_pin_name": target_pin_name,
        }, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)

    @mcp.tool
    def disconnect_nodes(
        blueprint_name: str,
        node_id: str,
        pin_name: str,
    ) -> str:
        """Disconnect all links from a pin in the Blueprint's EventGraph.

        Args:
            blueprint_name: Blueprint name or full path
            node_id: GUID of the node
            pin_name: Name of the pin to disconnect

        Returns the number of connections that were removed.
        """
        result = ue_connection.execute("disconnect_nodes", {
            "blueprint_name": blueprint_name,
            "node_id": node_id,
            "pin_name": pin_name,
        }, app_name=_APP)
        return json.dumps(result, indent=2, ensure_ascii=False)
