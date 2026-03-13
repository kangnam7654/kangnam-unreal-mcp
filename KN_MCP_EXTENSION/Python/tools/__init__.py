"""KN_MCP_EXTENSION tools package.

Tool modules use @mcp.tool decorator which requires 'mcp' to be injected
into each module's namespace before execution. Use register_all_tools()
to load all tool modules with proper mcp injection.
"""

import importlib.util
import os
import sys


_TOOL_MODULES = [
    "actor_tools",
    "actor_component_tools",
    "blueprint_tools",
    "blueprint_component_tools",
    "property_tools",
    "material_tools",
    "static_mesh_tools",
    "blueprint_variable_tools",
    "blueprint_graph_tools",
]


def register_all_tools(mcp):
    """Load all WORLD tool modules with mcp injected, registering @mcp.tool functions."""
    tools_dir = os.path.dirname(__file__)

    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))

    for name in _TOOL_MODULES:
        path = os.path.join(tools_dir, f"{name}.py")
        module_name = f"tools.{name}"

        if module_name in sys.modules:
            continue

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            module.mcp = mcp
            sys.modules[module_name] = module
            sys.modules[name] = module
            spec.loader.exec_module(module)
