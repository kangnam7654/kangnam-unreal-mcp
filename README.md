# KN_MCP — Unreal Engine MCP Plugin

Control Unreal Engine from AI agents (Claude Code, Cursor, etc.) via [Model Context Protocol](https://modelcontextprotocol.io/).

```
AI Agent (Claude/Cursor)
    | stdio
    v
Python MCP Server (FastMCP)        <-- KN_MCP/Python/
    | TCP JSON-RPC 2.0
    v
UE C++ TCP Server                  <-- KN_MCP/Source/
    | GameThread dispatch
    v
Unreal Engine API
```

## Features

- **38 commands** across 9 groups: Actor, Blueprint, Component, Material, Property, StaticMesh, BlueprintVariable, BlueprintGraph
- **Full CRUD** for Actors and Blueprints in the UE editor
- **Blueprint visual scripting** — add event/function/variable nodes and wire them up
- **SimpleCommand auto-registration** — C++ commands with `bIsSimple=true` auto-register as MCP tools
- **Extension plugin system** — add your own commands without modifying the core

## Requirements

- Unreal Engine 5.5+ (tested on 5.7)
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) (Python package manager)

## Quick Start

### 1. Add plugins to your UE project

Copy `KN_MCP/` and `KN_MCP_EXTENSION/` into your project's `Plugins/` directory.

### 2. Set up the Python MCP server

```bash
cd KN_MCP/Python
cp settings.ini.example settings.ini   # edit if needed
./setup_mcp.sh                         # or setup_mcp.bat on Windows
```

### 3. Configure your AI client

Add to your MCP client config (e.g., `~/.cursor/mcp.json` or Claude Code settings):

```json
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": [
        "--directory", "/path/to/KN_MCP/Python",
        "run", "python", "main.py"
      ]
    }
  }
}
```

### 4. Launch UE editor and start coding

Open your UE project. The plugin auto-starts a TCP server on port 27777-27787. Your AI agent can now control the editor.

## Supported Commands (38)

| Group | Count | Operations | Examples |
|-------|-------|------------|----------|
| Actor | 6 | CRUD | `spawn_actor`, `delete_actor`, `set_actor_transform` |
| ActorComponent | 3 | CRD | `add_component_to_actor`, `read_components_from_actor` |
| Blueprint | 7 | CRUD | `create_blueprint`, `compile_blueprint`, `spawn_blueprint_actor` |
| BlueprintComponent | 3 | CRD | `add_component_to_blueprint`, `remove_component_from_blueprint` |
| Property | 2 | U | `set_static_mesh_properties`, `set_physics_properties` |
| Material | 6 | RU | `apply_material_to_actor`, `set_mesh_material_color` |
| StaticMesh | 2 | R | `get_static_meshes`, `find_static_meshes_by_name` |
| BlueprintVariable | 2 | CD | `add_variable_to_blueprint`, `remove_variable_from_blueprint` |
| BlueprintGraph | 7 | CRUD | `add_event_node`, `add_function_call_node`, `connect_nodes` |

Full parameter/response reference: [KN_MCP_EXTENSION/docs/commands.md](KN_MCP_EXTENSION/docs/commands.md)

## Example: Create a Red Cube

An AI agent creating a red cube in UE:

```
1. create_blueprint(name="RedCube")
2. add_component_to_blueprint(blueprint_name="RedCube",
     component_class="StaticMeshComponent", component_name="Mesh")
3. set_static_mesh_properties(blueprint_name="RedCube",
     component_name="Mesh", static_mesh="/Engine/BasicShapes/Cube.Cube")
4. set_mesh_material_color(blueprint_name="RedCube",
     component_name="Mesh", color=[1.0, 0.0, 0.0])
5. compile_blueprint(blueprint_name="RedCube")
6. spawn_blueprint_actor(blueprint_name="RedCube",
     name="RedCube_1", location=[0, 0, 100])
```

## Plugin Structure

```
Plugins/
├── KN_MCP/                        # Core plugin (TCP server, command system, Python MCP server)
│   ├── Source/KN_MCP/             # C++ core
│   ├── Python/                    # Python MCP server (FastMCP)
│   └── docs/                      # Architecture docs
│
├── KN_MCP_EXTENSION/              # Extension plugin (38 commands for scene manipulation)
│   ├── Source/
│   │   ├── KN_MCP_EXTENSION/      # Runtime module (Actor, Component commands)
│   │   └── KN_MCP_EXTENSION_Editor/  # Editor module (Blueprint, Material commands)
│   ├── Python/tools/              # Python MCP tools
│   └── docs/                      # Command reference, design docs
│
└── KN_MCPTest/                    # Example/test extension plugin
```

## Creating Your Own Extension

1. Create a new UE plugin with `KN_MCP` dependency in `.build.cs`
2. In `StartupModule()`, call `FKN_MCP_Module::Get().AddUserToolDirectories()` to register your Python tools
3. Create C++ CommandGroups in `Private/Commands/` using `KN_MCP_REGISTER_COMMAND_GROUP` macro
4. Create Python tools in `Python/tools/` with `@mcp.tool()` decorators

See [KN_MCPTest/](KN_MCPTest/) for a minimal example.

Detailed architecture: [KN_MCP/docs/](KN_MCP/docs/)

## Tests

```bash
cd KN_MCP_EXTENSION/Python

# Unit tests (no UE required, mocked)
uv run python -m pytest tests/test_unit_tools.py -q

# Integration tests (UE editor must be running)
uv run python -m pytest tests/test_integration.py -q

# E2E tests (UE editor must be running)
uv run python -m pytest tests/test_e2e.py -q
```

| Type | Count | UE Required |
|------|-------|-------------|
| Unit | 85 | No |
| Integration | 111 | Yes |
| E2E | 10 | Yes |

## License

[MIT](LICENSE)
