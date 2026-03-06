# WN_MCP Plugin - Code Conventions & Architecture Guide

## Project Overview

Unreal Engine 5 MCP (Model Context Protocol) plugin. UE C++ TCP Server + Python FastMCP Server (stdio) 2-layer architecture.

- **WN_MCP**: Core plugin (TCP server, command group system, Python MCP server)
- **WN_MCPTest**: Example/test plugin (demonstrates how to extend WN_MCP)
- Protocol: **JSON-RPC 2.0** for all UE <-> Python communication

## Terminology

| Term | Meaning |
|------|---------|
| **Command (커맨드)** | C++ side function. `FWN_MCP_CommandGroup` subclass에서 UE API를 호출하는 함수. |
| **Tool (툴)** | Python side function. `@mcp.tool` 데코레이터로 등록되어 Agent가 호출하는 함수. |

- Command는 UE 엔진 내부에서 실행되며, TCP 소켓을 통해 JSON-RPC 2.0으로 응답한다.
- Tool은 Python MCP Server에서 실행되며, 필요 시 Command를 호출하여 UE와 통신한다.

## Architecture

```
Agent (Claude/Cursor) <--stdio--> Python MCP Server (Tool) <--TCP JSON-RPC 2.0--> UE C++ Plugin (Command)
```

### How to add functionality:

1. **C++ Command** - UE API 접근이 필요한 기능
   - `FWN_MCP_CommandGroup` 서브클래스에 커맨드 구현
   - `WN_MCP_REGISTER_COMMAND_GROUP` 매크로로 자동 등록
   - Python Tool에서 `ue_execute_simple_command()` 또는 `ue_send_command()` + `ue_receive_response()`로 호출

2. **Python Tool only** - UE 접근 불필요하거나 복잡한 오케스트레이션
   - `@mcp.tool` 데코레이터로 등록

## Work Rules

1. **기존 코드 수정 금지**: 이미 구현된 파일은 절대 수정하지 않는다.
2. **C++ 커맨드만 이식**: Python Tool은 별도 담당자가 작업 중이므로 건드리지 않는다.
3. **커맨드 단위 작업**: 커맨드 하나를 이식할 때마다 사용자에게 설명하고 허락을 받는다.
4. **커맨드 단위 커밋**: 커맨드 하나를 이식할 때마다 git commit한다.
5. **새 파일만 추가**: 새 CommandGroup은 `Private/Commands/`에 새 .h/.cpp 파일로 추가한다.

---

## C++ Command Conventions

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

New command plugins MUST follow this pattern:
1. Depend on `WN_MCP` module in `.build.cs`
2. In `StartupModule()`: get `FWN_MCP_Module::Get()`, call `AddUserToolDirectories()`
3. Create `Python/` directory with tool `.py` files
4. C++ CommandGroups auto-register via `WN_MCP_REGISTER_COMMAND_GROUP` macro

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

1. **NEVER** modify existing files - only add new files
2. New command groups go in `Private/Commands/` directory as new .h/.cpp pairs
3. Every `OnExecute` MUST end with `WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(WN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));`
4. All UE API calls in `OnExecute` run on GameThread (already dispatched by ServerThread)
5. Command names are globally unique across all plugins - check for conflicts
6. Python Tool 작업은 하지 않는다 (별도 담당자 영역)
7. 커맨드 이식 전 반드시 사용자에게 설명 및 승인을 받는다
8. 커맨드 이식 후 반드시 git commit한다
9. Copyright header: `// Copyright WemadeNext, Inc. All Rights Reserved.` (only in .build.cs files)

---

## Porting Status

Source: `FlopperamUnrealMCP` (`C:\projects\mir-unreal-mcp\mcp-plugin`)

### Editor Commands (FWN_MCP_CommandGroup_Editor)

| # | Command | Source Function | CommandGroup File | Status |
|---|---------|----------------|-------------------|--------|
| 1 | `get_actors_in_level` | `HandleGetActorsInLevel` | `WN_MCP_CommandGroup_Editor` | Done |
| 2 | `find_actors_by_name` | `HandleFindActorsByName` | `WN_MCP_CommandGroup_Editor` | Done |
| 3 | `spawn_actor` | `HandleSpawnActor` | `WN_MCP_CommandGroup_Editor` | Done |
| 4 | `delete_actor` | `HandleDeleteActor` | `WN_MCP_CommandGroup_Editor` | Done |
| 5 | `set_actor_transform` | `HandleSetActorTransform` | `WN_MCP_CommandGroup_Editor` | Done |
| 6 | `focus_viewport` | `HandleFocusViewport` | `WN_MCP_CommandGroup_Editor` | - |
| 7 | `take_screenshot` | `HandleTakeScreenshot` | `WN_MCP_CommandGroup_Editor` | - |

### Blueprint Commands (FWN_MCP_CommandGroup_Blueprint - TBD)

| # | Command | Source Function | Status |
|---|---------|----------------|--------|
| 8 | `create_blueprint` | `HandleCreateBlueprint` | - |
| 9 | `add_component_to_blueprint` | `HandleAddComponentToBlueprint` | - |
| 10 | `compile_blueprint` | `HandleCompileBlueprint` | - |
| 11 | `spawn_blueprint_actor` | `HandleSpawnBlueprintActor` | - |
| 12 | `set_static_mesh_properties` | `HandleSetStaticMeshProperties` | - |
| 13 | `set_physics_properties` | `HandleSetPhysicsProperties` | - |
| 14 | `set_mesh_material_color` | `HandleSetMeshMaterialColor` | - |

### Blueprint Graph Commands (FWN_MCP_CommandGroup_BlueprintGraph - TBD)

| # | Command | Source Function | Status |
|---|---------|----------------|--------|
| 15 | `add_blueprint_node` | `HandleAddBlueprintNode` | - |
| 16 | `connect_nodes` | `HandleConnectNodes` | - |
| 17 | `create_variable` | `HandleCreateVariable` | - |
| 18 | `add_event_node` | `HandleAddEventNode` | - |
| 19 | `delete_node` | `HandleDeleteNode` | - |
| 20 | `set_node_property` | `HandleSetNodeProperty` | - |
| 21 | `create_function` | `HandleCreateFunction` | - |
