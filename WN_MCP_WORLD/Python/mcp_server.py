"""
WN_MCP_WORLD - MCP Server

FastMCP server exposing Actor & Blueprint CRUD commands as MCP tools.
LLM (Claude Code, Cursor, etc.) connects to this server via stdio,
and this server forwards commands to UE C++ plugin via TCP JSON-RPC 2.0.

Usage:
    # Run as MCP server (stdio transport - for LLM integration)
    uv run python mcp_server.py

    # Add to Claude Code MCP config (~/.claude/settings.json):
    {
        "mcpServers": {
            "ue-world": {
                "command": "uv",
                "args": ["run", "python", "mcp_server.py"],
                "cwd": "<path-to>/WN_MCP_WORLD/Python"
            }
        }
    }
"""

import json
import socket
from typing import Optional, Dict, Any, List
from fastmcp import FastMCP


# =============================================================================
# UE TCP Connection
# =============================================================================

UE_HOST = "127.0.0.1"
UE_PORT = 27777
UE_TIMEOUT = 30.0
_ue_socket: Optional[socket.socket] = None


def _ue_connect() -> bool:
    global _ue_socket
    if _ue_socket is not None:
        return True
    try:
        _ue_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _ue_socket.settimeout(UE_TIMEOUT)
        _ue_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        _ue_socket.connect((UE_HOST, UE_PORT))
        return True
    except Exception as e:
        _ue_socket = None
        raise ConnectionError(f"Cannot connect to UE at {UE_HOST}:{UE_PORT} - {e}")


def _ue_disconnect():
    global _ue_socket
    if _ue_socket:
        try:
            _ue_socket.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        _ue_socket.close()
        _ue_socket = None


def _ue_execute(command_name: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Send JSON-RPC 2.0 command to UE and return result."""
    _ue_connect()

    request = {
        "jsonrpc": "2.0",
        "method": "command",
        "id": command_name,
        "params": params if params is not None else {}
    }

    try:
        _ue_socket.send(json.dumps(request).encode("utf-8"))

        # Read until we have a complete JSON response
        chunks = []
        while True:
            chunk = _ue_socket.recv(65536)
            if not chunk:
                _ue_disconnect()
                raise ConnectionError("UE closed connection")
            chunks.append(chunk)
            try:
                response = json.loads(b"".join(chunks).decode("utf-8"))
                break
            except json.JSONDecodeError:
                continue

        if "error" in response:
            error = response["error"]
            raise RuntimeError(f"UE error [{error.get('code', '?')}]: {error.get('message', 'Unknown')}")

        return response.get("result", {})

    except (socket.timeout, ConnectionError, BrokenPipeError, OSError) as e:
        _ue_disconnect()
        raise ConnectionError(f"UE communication failed: {e}")


# =============================================================================
# MCP Server
# =============================================================================

mcp = FastMCP("WN_MCP_WORLD")


# =============================================================================
# Actor CRUD Tools
# =============================================================================


@mcp.tool
def get_actors_in_level() -> str:
    """Get all actors currently in the Unreal Engine level.

    Returns a list of all actors with their name, class, location, rotation, and scale.
    Use this to inspect the current state of the level.
    """
    result = _ue_execute("get_actors_in_level")
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def find_actors_by_name(search_text: str) -> str:
    """Find actors in the level by partial name match.

    Args:
        search_text: Text to search for in actor names (partial match, case-sensitive)

    Returns a list of matching actors with their name, class, location, rotation, and scale.
    """
    result = _ue_execute("find_actors_by_name", {"search_text": search_text})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def spawn_actor(
    type: str,
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> str:
    """Spawn a new actor in the Unreal Engine level.

    Args:
        type: Actor class name (e.g. "StaticMeshActor", "PointLight", "CameraActor")
        name: Unique name for the new actor
        location: [x, y, z] world position (default: [0, 0, 0])
        rotation: [pitch, yaw, roll] in degrees (default: [0, 0, 0])
        scale: [x, y, z] scale factors (default: [1, 1, 1])

    Creates the actor at the specified transform. Name must be unique in the level.
    """
    params: Dict[str, Any] = {"type": type, "name": name}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale

    result = _ue_execute("spawn_actor", params)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def delete_actor(name: str) -> str:
    """Delete an actor from the Unreal Engine level.

    Args:
        name: Exact name of the actor to delete

    Permanently removes the actor from the level.
    """
    result = _ue_execute("delete_actor", {"name": name})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def set_actor_transform(
    name: str,
    location: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> str:
    """Set the transform (position/rotation/scale) of an existing actor.

    Args:
        name: Exact name of the actor to modify
        location: [x, y, z] new world position (omit to keep current)
        rotation: [pitch, yaw, roll] new rotation in degrees (omit to keep current)
        scale: [x, y, z] new scale factors (omit to keep current)

    Only provided transform components are updated; others remain unchanged.
    """
    params: Dict[str, Any] = {"name": name}
    if location is not None:
        params["location"] = location
    if rotation is not None:
        params["rotation"] = rotation
    if scale is not None:
        params["scale"] = scale

    result = _ue_execute("set_actor_transform", params)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def read_actor_content(name: str) -> str:
    """Read detailed content of a single actor, including its components.

    Args:
        name: Exact name of the actor to inspect

    Returns name, class, transform (location/rotation/scale), and a list of
    all components attached to the actor with their name and class.
    """
    result = _ue_execute("read_actor_content", {"name": name})
    return json.dumps(result, indent=2, ensure_ascii=False)


# =============================================================================
# Blueprint CRUD Tools
# =============================================================================


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

    result = _ue_execute("create_blueprint", params)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def read_blueprint_content(
    blueprint_path: str,
    include_event_graph: Optional[bool] = None,
    include_functions: Optional[bool] = None,
    include_variables: Optional[bool] = None,
    include_components: Optional[bool] = None,
    include_interfaces: Optional[bool] = None,
) -> str:
    """Read the content/structure of a Blueprint asset.

    Args:
        blueprint_path: Full asset path (e.g. "/Game/Blueprints/MyBP")
        include_event_graph: Include event graph info (default: true)
        include_functions: Include function list (default: true)
        include_variables: Include variable list (default: true)
        include_components: Include component list (default: true)
        include_interfaces: Include implemented interfaces (default: true)

    Returns detailed information about the Blueprint's variables, functions,
    event graph, components, and interfaces.
    """
    params: Dict[str, Any] = {"blueprint_path": blueprint_path}
    if include_event_graph is not None:
        params["include_event_graph"] = include_event_graph
    if include_functions is not None:
        params["include_functions"] = include_functions
    if include_variables is not None:
        params["include_variables"] = include_variables
    if include_components is not None:
        params["include_components"] = include_components
    if include_interfaces is not None:
        params["include_interfaces"] = include_interfaces

    result = _ue_execute("read_blueprint_content", params)
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def compile_blueprint(blueprint_name: str) -> str:
    """Compile a Blueprint asset.

    Args:
        blueprint_name: Blueprint name or full path (e.g. "MyBP" or "/Game/Blueprints/MyBP")

    Compiles the Blueprint to update its generated class.
    """
    result = _ue_execute("compile_blueprint", {"blueprint_name": blueprint_name})
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool
def delete_blueprint(blueprint_path: str, force: bool = False) -> str:
    """Delete a Blueprint asset from the project.

    Args:
        blueprint_path: Full asset path (e.g. "/Game/Blueprints/MyBP")
        force: If true, delete even if other assets reference this Blueprint.
               If false (default), returns error with list of referencers.

    WARNING: Deleting a Blueprint that is referenced by other assets may break those assets.
    """
    params: Dict[str, Any] = {"blueprint_path": blueprint_path}
    if force:
        params["force"] = True

    result = _ue_execute("delete_blueprint", params)
    return json.dumps(result, indent=2, ensure_ascii=False)


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run(transport="stdio", log_level="WARNING", show_banner=False)
