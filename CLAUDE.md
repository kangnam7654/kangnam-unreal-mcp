# WN_MCP Plugin - Code Conventions & Architecture Guide

## Project Overview

Unreal Engine 5 MCP (Model Context Protocol) plugin. UE C++ TCP Server + Python FastMCP Server (stdio) 2-layer architecture.

- **WN_MCP**: Core plugin (TCP server, command group system, Python MCP server)
- **WN_MCPTest**: Example/test plugin (demonstrates how to extend WN_MCP)
- Protocol: **JSON-RPC 2.0** for all UE <-> Python communication

## Architecture

```
Agent (Claude/Cursor) <--stdio--> Python FastMCP Server <--TCP (127.0.0.1:27777~27787)--> UE C++ Plugin
```

### Two ways to add tools:

1. **C++ CommandGroup + Python `register_simple_commands()`**
   - C++ side: `FWN_MCP_CommandGroup` subclass handles the UE API call
   - Python side: `register_simple_commands()` returns command list, auto-wrapped with `ue_execute_simple_command()`
   - Use when: UE API access is needed (actors, assets, editor, etc.)

2. **Python `@mcp.tool` only**
   - Python function decorated with `@mcp.tool`, calls `ue_send_command()` + `ue_receive_response()` if UE interaction needed
   - Use when: Complex orchestration, multi-step logic, or pure Python tools

---

## C++ Code Conventions

### File Structure

```
WN_MCP/Source/WN_MCP/
  Public/
    WN_MCP_Module.h          # Module header (public API, WN_MCP_API exports)
    WN_MCP_CommandGroup.h     # Base class + macros + defines
  Private/
    WN_MCP_Module.cpp         # Module implementation
    WN_MCP_CommandGroup.cpp   # Base class implementation
    WN_MCP_ServerThread.h     # Private-only headers go here
    WN_MCP_ServerThread.cpp
    Commands/                 # Command group implementations
      WN_MCP_CommandGroup_XXX.h
      WN_MCP_CommandGroup_XXX.cpp
```

### Naming Rules

| Category | Convention | Example |
|----------|-----------|---------|
| File names | `WN_MCP_` prefix + PascalCase | `WN_MCP_CommandGroup_Editor.h` |
| Classes (non-UObject) | `F` prefix + `WN_MCP_` | `FWN_MCP_CommandGroup_Editor` |
| Classes (UObject) | `U` prefix + `WN_MCP_` | `UWN_MCP_Subsystem` |
| Input params | `In` prefix | `InCommandName`, `InParamsPtr` |
| Output params | `InOut` prefix | `InOutCommandNames` |
| Smart pointers | `Ptr` suffix | `ListenerSocketPtr`, `InClientSocketPtr` |
| Booleans | `b` prefix | `bIsRunning` |
| Methods | PascalCase | `OnExecute`, `GetName`, `OnRegisterCommands` |
| Macros | `WN_` prefix + ALL_CAPS | `WN_RETURN_COMMAND_RESPONSE` |
| Command names | snake_case string | `"get_actors_in_level"`, `"spawn_actor"` |

### Section Dividers (MUST follow exactly)

```cpp
// Top-level sections: 80 dashes
//-----------------------------------------------------------------------------
// Section Name
//-----------------------------------------------------------------------------

// Sub-sections inside class: 72 dashes
	//-------------------------------------------------------------------------
	// Sub-section Name
	//-------------------------------------------------------------------------
```

### Documentation Comments

```cpp
/// Single-line doc comment.
/// @param InName parameter description.
/// @return return value description.
```

Use `///` (triple-slash) for Doxygen. NOT `/** */` style.

### Header File Template

```cpp
#pragma once

#include "WN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_XXX
//-----------------------------------------------------------------------------

/// Command group for XXX operations.
class FWN_MCP_CommandGroup_XXX : public FWN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Overrides FWN_MCP_CommandGroup
	//-------------------------------------------------------------------------

public:

	/// Get command group name.
	FString GetName() const override;

	/// Register commands.
	void OnRegisterCommands(TArray<FString>& InOutCommandNames) const override;

	/// Execute command.
	TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	FWN_MCP_CommandGroup_XXX();

	/// destructor.
	~FWN_MCP_CommandGroup_XXX();
};
```

### Source File Template

```cpp
#include "WN_MCP_CommandGroup_XXX.h"
#include "WN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FWN_MCP_CommandGroup_XXX
//-----------------------------------------------------------------------------

WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_XXX);

FWN_MCP_CommandGroup_XXX::FWN_MCP_CommandGroup_XXX()
{

}

FWN_MCP_CommandGroup_XXX::~FWN_MCP_CommandGroup_XXX()
{
}

FString FWN_MCP_CommandGroup_XXX::GetName() const
{
	return FString("XXX");
}

void FWN_MCP_CommandGroup_XXX::OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
	InOutCommandNames.Add(FString(TEXT("command_name_here")));
}

TSharedPtr<FJsonObject> FWN_MCP_CommandGroup_XXX::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	if (InCommandName == FString(TEXT("command_name_here")))
	{
		// Implementation here
		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("key"), TEXT("value"));
		WN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
```

### Response Macros (MUST use these, never hand-build response JSON)

| Macro | Usage |
|-------|-------|
| `WN_RETURN_COMMAND_RESPONSE(InResultPtr)` | Object result |
| `WN_RETURN_COMMAND_TEXT_RESPONSE(TEXT("msg"))` | Text result |
| `WN_RETURN_COMMAND_ARRAY_RESPONSE(jsonArray)` | Array result |
| `WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(code, TEXT("msg"))` | Error with text |
| `WN_RETURN_COMMAND_ERROR_RESPONSE(code, errorObj)` | Error with object |

### Code Style Details

- Tabs for indentation (UE standard), NOT spaces
- Opening brace on next line for functions/classes
- Opening brace on same line for `if/else/for/while`
- Access specifiers (`public:`, `private:`) with blank line after
- Empty constructor/destructor bodies: opening brace on next line, empty line, closing brace
- `FString(TEXT("..."))` for command name comparisons
- `MakeShareable(new FJsonObject())` for creating JSON objects
- Always end `OnExecute` with `WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));`

### Extension Plugin Pattern (like WN_MCPTest)

New tool plugins MUST follow this pattern:
1. Depend on `WN_MCP` module in `.build.cs`
2. In `StartupModule()`: get `FWN_MCP_Module::Get()`, call `AddUserToolDirectories()`
3. Create `Python/` directory with tool `.py` files
4. C++ CommandGroups auto-register via `WN_MCP_REGISTER_COMMAND_GROUP` macro

---

## Python Code Conventions

### File Structure

```
PyMCP/
  wn_mcp_server.py            # MCP server entry point
  settings.ini                 # Configuration
  pyproject.toml
  Tools/
    __init__.py                # Package init
    params.py                  # get_mcp_params() / _set_mcp_params()
    log_tool.py                # Logging utilities
    ue_interaction_tool.py     # UE connection + built-in MCP tools
    agent_interaction_tool.py  # Agent/chat interaction tools
```

### Naming Rules

| Category | Convention | Example |
|----------|-----------|---------|
| Files | snake_case | `ue_interaction_tool.py` |
| Functions | snake_case | `register_tools`, `ue_send_command` |
| Classes | PascalCase | `ChatInteractionManager`, `DialogueState` |
| Constants | UPPER_SNAKE | `UE_HOST`, `AUTO_RECONNECT_ENABLED` |
| Private vars | `_` prefix | `_manager`, `_agent_tools_registered` |
| MCP tool names | snake_case | `check_ue_connection`, `show_notification` |

### Tool Registration Pattern

```python
# Track registration to prevent duplicates
_tools_registered = False

def register_tools(mcp) -> None:
    """Register tools with MCP server."""
    global _tools_registered
    if _tools_registered:
        log_debug('Tools already registered, skipping')
        return

    @mcp.tool
    def my_tool_name() -> Dict[str, Any]:
        """Tool description for LLM context.

        Expects params (via get_mcp_params()):
            param_name: Description
        """
        try:
            params = get_mcp_params()
            # ... implementation
            return {
                "jsonrpc": "2.0",
                "result": { ... }
            }
        except Exception as e:
            mcp_log(f'Tool: Error in my_tool_name: {e}')
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }

    _tools_registered = True
    mcp_log('Tools registered')
```

### User Tool File Pattern (for `register_simple_commands`)

```python
"""
Module description.
"""

from Tools import get_mcp_params
from Tools.ue_interaction_tool import ue_send_command, ue_receive_response

def register_simple_commands() -> list[dict]:
    """Register simple commands that execute on UE."""
    return [
        {
            'name': 'command_name',
            'description': 'Description for LLM context'
        }
    ]

# For complex tools that need custom Python logic:
@mcp.tool
def complex_tool() -> dict:
    """Tool description."""
    try:
        params = get_mcp_params() or {}
        ue_send_command("ue_command_name", params)
        return ue_receive_response()
    except Exception as e:
        raise Exception(f"complex_tool failed: {str(e)}")
```

### Return Format (ALWAYS JSON-RPC 2.0)

```python
# Success
{"jsonrpc": "2.0", "result": {"key": "value", "message": "..."}}

# Error
{"jsonrpc": "2.0", "error": {"code": -32603, "message": "Error description"}}
```

### Logging

```python
from Tools.log_tool import log_info as mcp_log, log_debug, log_misc

mcp_log('Important info')                    # INFO level, file + stderr
log_debug('Debug detail')                    # DEBUG level, stderr only by default
log_misc(f'JSON dump: {json.dumps(data)}')   # MISC level (5), for verbose data

# In tool functions, prefix with 'Tool: '
mcp_log(f'Tool: my_tool() called')
mcp_log(f'Tool: Error in my_tool: {e}')
```

### Imports

```python
# Standard library first
import json
import time
from typing import Dict, Any, Optional

# Then project imports
from Tools.log_tool import log_info as mcp_log, log_debug
from Tools.params import get_mcp_params
from Tools.ue_interaction_tool import ue_send_command, ue_receive_response, ue_execute_simple_command
```

---

## JSON-RPC 2.0 Protocol

### Python -> UE (Request)
```json
{
    "jsonrpc": "2.0",
    "method": "command",
    "id": "command_name",
    "params": { ... }
}
```

### UE -> Python (Success Response)
```json
{
    "jsonrpc": "2.0",
    "result": { ... },
    "id": "command_name"
}
```

### UE -> Python (Error Response)
```json
{
    "jsonrpc": "2.0",
    "error": {
        "code": -32601,
        "message": "Method not found",
        "data": "additional info"
    },
    "id": "command_name"
}
```

### Standard Error Codes

| Code | Name | Usage |
|------|------|-------|
| -32700 | Parse error | Invalid JSON |
| -32600 | Invalid Request | Not a valid request |
| -32601 | Method not found | Command not registered |
| -32602 | Invalid params | Wrong parameters |
| -32603 | Internal error | Server-side error |
| -32001 | Command failed | Command execution failed |
| -32002 | Invalid arguments | Invalid command arguments |

---

## CRITICAL RULES

1. **NEVER** modify files in `WN_MCP/` core plugin without explicit approval
2. New command groups go in `Private/Commands/` directory
3. Every `OnExecute` MUST end with `WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));`
4. All UE API calls in `OnExecute` run on GameThread (already dispatched by ServerThread)
5. Command names are globally unique across all plugins - check for conflicts
6. Python tool return values MUST be JSON-RPC 2.0 format
7. Use `get_mcp_params()` for parameterless `@mcp.tool` functions
8. Use `ue_execute_simple_command()` for simple send+receive patterns
9. Log with `mcp_log()` at appropriate levels, prefix tool logs with `'Tool: '`
10. Copyright header: `// Copyright WemadeNext, Inc. All Rights Reserved.` (only in .build.cs files)
