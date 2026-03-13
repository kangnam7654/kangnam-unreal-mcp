# KN_MCP Plugin - Code Conventions & Architecture Guide

## Project Overview

Unreal Engine 5 MCP (Model Context Protocol) plugin. UE C++ TCP Server + Python FastMCP Server (stdio) 2-layer architecture.

- **KN_MCP**: Core plugin (TCP server, command group system, Python MCP server) — **보수적 수정 허용** (아래 Work Rules 참조)
- **KN_MCP_EXTENSION**: 실제 커맨드 구현 플러그인 (Actor, Blueprint, Component CRUD)
- Protocol: **JSON-RPC 2.0** for all UE <-> Python communication

## Terminology

| Term | Meaning |
|------|---------|
| **Command (커맨드)** | C++ side function. `FKN_MCP_CommandGroup` subclass에서 UE API를 호출하는 함수. |
| **Tool (툴)** | Python side function. `@mcp.tool` 데코레이터로 등록되어 Agent가 호출하는 함수. |

- Command는 UE 엔진 내부에서 실행되며, TCP 소켓을 통해 JSON-RPC 2.0으로 응답한다.
- Tool은 Python MCP Server에서 실행되며, 필요 시 Command를 호출하여 UE와 통신한다.

## Architecture

```
Agent (Claude/Cursor) <--stdio--> Python MCP Server (Tool) <--TCP JSON-RPC 2.0--> UE C++ Plugin (Command)
```

### How to add functionality:

1. **C++ Command** - UE API 접근이 필요한 기능
   - `FKN_MCP_CommandGroup` 서브클래스에 커맨드 구현
   - `KN_MCP_REGISTER_COMMAND_GROUP` 매크로로 자동 등록
   - Python Tool에서 `ue_connection.send_command(command_name, params, category_name=_CATEGORY)`로 호출

2. **Python Tool only** - UE 접근 불필요하거나 복잡한 오케스트레이션
   - `@mcp.tool` 데코레이터로 등록

## Work Rules

1. **KN_MCP 보수적 수정**: `KN_MCP/` 코드를 수정할 때 아래 원칙을 위반하면 안 된다:
   - 목적과 무관한 코드를 변경하면 안 된다. 리팩터링/스타일 변경 금지.
   - 기존 동작을 깨뜨리면 안 된다. KN_MCP_EXTENSION 등 기존 확장 플러그인이 수정 없이 동작해야 한다.
   - KN_MCP 변경을 다른 변경과 같은 커밋에 섞으면 안 된다. 언제든 `git revert`로 원복 가능해야 한다.
   - 사용자 승인 없이 KN_MCP를 수정하면 안 된다.
2. **KN_MCP Python 보수적 수정**: `KN_MCP/Python/`도 위와 동일한 원칙을 위반하면 안 된다.
3. 커맨드 이식 전 사용자에게 설명 없이 바로 구현하면 안 된다.
4. 커맨드 이식 후 커밋하지 않고 다음 커맨드로 넘어가면 안 된다.
5. 기존 CommandGroup 파일을 수정하면 안 된다. 새 CommandGroup은 `Private/Commands/`에 새 .h/.cpp 파일로 추가한다.

---

## C++ Command Conventions

### File Structure

```
KN_MCP/Source/KN_MCP/                          # Core plugin (보수적 수정 허용)
  Public/
    KN_MCP_Module.h                            # Module header (public API, KN_MCP_API exports)
    KN_MCP_CommandGroup.h                      # Base class + macros + defines
  Private/
    KN_MCP_Module.cpp                          # Module implementation
    KN_MCP_CommandGroup.cpp                    # Base class implementation
    KN_MCP_ServerThread.h/.cpp                 # TCP server thread

KN_MCP_EXTENSION/Source/
  KN_MCP_EXTENSION/                                # Runtime module (Engine API만 사용)
    Public/
      KN_MCP_ActorUtils.h                      # 공유 유틸리티 (FindActorByName, KN_MCP_EXTENSION_API export)
    Private/
      KN_MCP_ActorUtils.cpp                    # FindActorByName 구현
      Commands/
        KN_MCP_CommandGroup_Actor.h/.cpp         # Actor CRUD
        KN_MCP_CommandGroup_ActorComponent.h/.cpp # Actor component CRD
  KN_MCP_EXTENSION_Editor/                         # Editor module (UnrealEd 의존)
    Private/
      KN_MCP_BlueprintUtils.h/.cpp             # 공유 유틸리티 (FindBlueprintByName, FindSCSNodeByName)
      Commands/
        KN_MCP_CommandGroup_Blueprint.h/.cpp    # Blueprint CRUD + Spawn
        KN_MCP_CommandGroup_BlueprintComponent.h/.cpp # Blueprint component CRD
        KN_MCP_CommandGroup_Property.h/.cpp    # Property 설정
        KN_MCP_CommandGroup_Material.h/.cpp    # Material 조회/적용
        KN_MCP_CommandGroup_StaticMesh.h/.cpp  # StaticMesh 조회
        KN_MCP_CommandGroup_BlueprintVariable.h/.cpp # Blueprint 변수 추가/제거
        KN_MCP_CommandGroup_BlueprintGraph.h/.cpp    # Blueprint 그래프 노드/연결
KN_MCP_EXTENSION/Python/                           # Python Tool 패키지 (자체 MCP Server 없음, Python MCP Server가 동적 Import)
    pyproject.toml
    tools/                                     # Tool 모듈 (용도별 분리)
      __init__.py                              # register_all_tools()
      ue_connection.py                         # UE TCP 연결 유틸리티
      actor_tools.py                           # Actor CRUD 6개
      actor_component_tools.py                 # ActorComponent CRD 3개
      blueprint_tools.py                       # Blueprint CRUD 7개 (스폰 포함)
      blueprint_component_tools.py             # BlueprintComponent CRD 3개
      property_tools.py                        # Property 설정 2개
      material_tools.py                        # Material 조회/적용 6개
      static_mesh_tools.py                     # StaticMesh 조회 2개
      blueprint_variable_tools.py              # BlueprintVariable 추가/제거 2개
      blueprint_graph_tools.py                 # BlueprintGraph 노드/연결 7개
    tests/                                     # 테스트 (unit/integration/e2e)
      conftest.py                              # 공통 fixture
      test_unit_tools.py                       # Unit 테스트 (UE Mock)
      test_integration.py                      # 통합 테스트 (UE 필요)
      test_e2e.py                              # E2E 테스트 (UE 필요)
```

### Naming Rules

| Category | Convention | Example |
|----------|-----------|---------|
| File names | `KN_MCP_` prefix + PascalCase | `KN_MCP_CommandGroup_Actor.h` |
| Classes (non-UObject) | `F` prefix + `KN_MCP_` | `FKN_MCP_CommandGroup_Actor` |
| Classes (UObject) | `U` prefix + `KN_MCP_` | `UKN_MCP_Subsystem` |
| Input params | `In` prefix | `InCommandName`, `InParamsPtr` |
| Output params | `InOut` prefix | `InOutCommandInfos` |
| Local result objects | `InResultPtr` | KN_MCP 매크로가 이 변수명에 의존 |
| Smart pointers | `Ptr` suffix | `ListenerSocketPtr`, `InClientSocketPtr` |
| Booleans | `b` prefix | `bIsRunning` |
| Methods | PascalCase | `OnExecute`, `GetName`, `OnRegisterCommands` |
| Macros | `KN_` prefix + ALL_CAPS | `KN_RETURN_COMMAND_RESPONSE` |
| Command names | snake_case string | `"get_actors_in_level"`, `"spawn_actor"` |

### Section Dividers (아래 형식 외 다른 구분선 형식을 사용하면 안 된다)

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

### Documentation Comments (Doxygen에 `/** */` 스타일을 사용하면 안 된다 — `///` triple-slash만 사용)

```cpp
/// Single-line doc comment.
/// @param InName parameter description.
/// @return return value description.
```

### Header File Template

```cpp
#pragma once

#include "KN_MCP_CommandGroup.h"

//-----------------------------------------------------------------------------
// Forward Declarations
//-----------------------------------------------------------------------------

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_XXX
//-----------------------------------------------------------------------------

/// Command group for XXX operations.
class FKN_MCP_CommandGroup_XXX : public FKN_MCP_CommandGroup
{
	//-------------------------------------------------------------------------
	// Overrides FKN_MCP_CommandGroup
	//-------------------------------------------------------------------------

public:

	/// Get command group name.
	FString GetName() const override;

	/// Get application name prefix for command registration.
	FString GetApplicationName() const override;

	/// Register commands.
	void OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const override;

	/// Execute command.
	TSharedPtr<FJsonObject> OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const override;

	//-------------------------------------------------------------------------
	// Methods
	//-------------------------------------------------------------------------

public:

	/// constructor.
	FKN_MCP_CommandGroup_XXX();

	/// destructor.
	~FKN_MCP_CommandGroup_XXX();
};
```

### Source File Template

```cpp
#include "KN_MCP_CommandGroup_XXX.h"
#include "KN_MCP_Module.h"

#include "Dom/JsonObject.h"

//-----------------------------------------------------------------------------
// FKN_MCP_CommandGroup_XXX
//-----------------------------------------------------------------------------

KN_MCP_REGISTER_COMMAND_GROUP(FKN_MCP_CommandGroup_XXX);

FKN_MCP_CommandGroup_XXX::FKN_MCP_CommandGroup_XXX()
{

}

FKN_MCP_CommandGroup_XXX::~FKN_MCP_CommandGroup_XXX()
{
}

FString FKN_MCP_CommandGroup_XXX::GetName() const
{
	return FString("XXX");
}

FString FKN_MCP_CommandGroup_XXX::GetApplicationName() const
{
	return FString("KN_MCP_EXTENSION");
}

void FKN_MCP_CommandGroup_XXX::OnRegisterCommands(TArray<FKN_MCP_CommandInfo>& InOutCommandInfos) const
{
	KN_MCP_REGISTER_COMMAND(InOutCommandInfos, "command_name_here");
}

TSharedPtr<FJsonObject> FKN_MCP_CommandGroup_XXX::OnExecute(const FString& InCommandName, const TSharedPtr<FJsonObject>& InParamsPtr, TSharedPtr<FSocket> InClientSocketPtr) const
{
	//-------------------------------------------------------------------------
	// command_name_here
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("command_name_here")))
	{
		// Implementation here

		TSharedPtr<FJsonObject> InResultPtr = MakeShareable(new FJsonObject());
		InResultPtr->SetStringField(TEXT("key"), TEXT("value"));
		KN_RETURN_COMMAND_RESPONSE(InResultPtr);
	}

	KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));
}
```

### Command Registration

Commands are registered via `FKN_MCP_CommandInfo` struct and helper macros:

```cpp
/// Struct holding command metadata for registration.
struct FKN_MCP_CommandInfo
{
    FString Name;
    FString Description;
    bool bIsSimple;
};

/// Register a standard command (Python Tool docstring serves as description).
KN_MCP_REGISTER_COMMAND(InOutList, "command_name")

/// Register a simple command (auto-wrapped by the framework).
KN_MCP_REGISTER_SIMPLE_COMMAND(InOutList, "command_name", "Description")
```

Each CommandGroup MUST override `GetApplicationName()` to return its plugin name (e.g. `"KN_MCP_EXTENSION"`). This prefix is prepended to command names during registration to prevent cross-plugin collisions. `Execute()` automatically strips the prefix before calling `OnExecute()`, so if-statements inside `OnExecute` use raw names (e.g. `"spawn_actor"`, not `"KN_MCP_EXTENSION_spawn_actor"`).

### Response Macros (응답 JSON을 매크로 없이 직접 구성하면 안 된다)

| Macro | Usage |
|-------|-------|
| `KN_RETURN_COMMAND_RESPONSE(InResultPtr)` | Object result |
| `KN_RETURN_COMMAND_TEXT_RESPONSE(TEXT("msg"))` | Text result |
| `KN_RETURN_COMMAND_ARRAY_RESPONSE(jsonArray)` | Array result |
| `KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(code, TEXT("msg"))` | Error with text |
| `KN_RETURN_COMMAND_ERROR_RESPONSE(code, errorObj)` | Error with object |

### Code Style Details

- 들여쓰기에 spaces를 사용하면 안 된다 — tabs만 사용 (UE standard)
- 함수/클래스의 여는 중괄호를 같은 줄에 두면 안 된다 (다음 줄로)
- `if/else/for/while`의 여는 중괄호를 다음 줄로 내리면 안 된다 (같은 줄에)
- 접근 지정자(`public:`, `private:`) 뒤에 빈 줄 없이 코드를 쓰면 안 된다
- 빈 생성자 본문에서 여는/닫는 중괄호 사이 빈 줄을 빠뜨리면 안 된다
- 빈 소멸자 본문에 빈 줄을 넣으면 안 된다
- 커맨드 이름 비교에 `FString(TEXT("..."))` 외 형식을 사용하면 안 된다
- JSON 오브젝트 생성에 `MakeShareable(new FJsonObject())` 외 방법을 사용하면 안 된다
- `OnExecute`를 `KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));` 없이 끝내면 안 된다
- `OnExecute` 내 커맨드 블록 앞에 72-dash 구분선(커맨드 이름 포함) 없이 코드를 쓰면 안 된다
- 코드가 이미 설명하는 내용을 주석으로 반복하면 안 된다: `// Get required parameters`, `// Return result` 등 금지
- `InResultPtr` 생성 앞에 빈 줄 없이 바로 쓰면 안 된다 (결과 생성부와 로직 분리)
- 인라인 주석을 소문자로 시작하면 안 된다: `// Find actor by name` (NOT `// find actor by name`)
- CommandGroup 내부 헬퍼를 클래스 멤버로 선언하면 안 된다 — 파일 스코프 `static` 함수로 선언
- 여러 CommandGroup에서 공유하는 유틸리티를 개별 CommandGroup 안에 두면 안 된다 — 전용 유틸리티 클래스(`FKN_MCP_BlueprintUtils` 등)에 `static` 멤버로 선언
- 헤더 파일이 사용하는 타입의 include를 빠뜨리면 안 된다 (IWYU). `FString`, `KN_MCP_EXTENSION_API` → `CoreMinimal.h` 필수. `FModuleManager` → `Modules/ModuleManager.h` 필수

### Extension Plugin Pattern

새 커맨드 플러그인 작성 시:
- `.build.cs`에 `KN_MCP` 모듈 의존성 없이 만들면 안 된다
- `StartupModule()`에서 `FKN_MCP_Module::Get()` → `AddUserToolDirectories()` 호출을 빠뜨리면 안 된다
- Python Tool 파일을 `Python/` 디렉터리 밖에 두면 안 된다
- `KN_MCP_REGISTER_COMMAND_GROUP` 매크로 없이 CommandGroup을 수동 등록하면 안 된다

---

## JSON-RPC 2.0 Protocol

### Python -> UE (Request)
```json
{
    "jsonrpc": "2.0",
    "method": "Actor_command_name",
    "id": "<uuid>",
    "params": { ... }
}
```

- `method`: 커맨드 라우팅에 사용 (e.g. `"Actor_get_actors_in_level"`)
- `id`: 유니크 요청 식별자 (UUID), 응답에서 echo back

### UE -> Python (Success Response)
```json
{
    "jsonrpc": "2.0",
    "result": { ... },
    "id": "<uuid>"
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
    "id": "<uuid>"
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

## Python Tool Conventions

### UE Connection

Python Tool에서 C++ Command를 `ue_connection.send_command()` 외 방법으로 호출하면 안 된다:

```python
from tools import ue_connection

_CATEGORY = "Actor"  # C++ GetName() 반환값과 일치해야 함

result = ue_connection.send_command("command_name", params, category_name=_CATEGORY)
```

- `category_name` 파라미터가 C++ `GetName()` 반환값과 불일치하면 안 된다
- `send_command()`가 내부적으로 `"{category_name}_{command_name}"` 형태로 full command name을 구성한다
- 에러 시 예외를 발생시키지 않고 `{"status": "error", "error": "..."}` 형태의 dict를 반환한다

---

## Testing

- 테스트 커버리지가 80% 미만이면 안 된다
- 새 Tool/Command 추가 시 Unit 테스트 없이 코드만 추가하면 안 된다
- Unit 테스트에서 외부 의존성(UE 연결 등)을 Mock 없이 직접 호출하면 안 된다
- 코드 변경 후 `uv run python -m pytest tests/ -q` 실행 없이 작업을 완료하면 안 된다

## CRITICAL RULES

1. `KN_MCP/` 수정 시 Work Rules 1번의 4가지 원칙(최소 변경, 하위 호환, 변경 단위 커밋, 사전 승인)을 위반하면 안 된다
2. 기존 CommandGroup .h/.cpp 파일에 새 커맨드를 끼워 넣으면 안 된다. 새 .h/.cpp 파일로 추가해야 한다
3. `OnExecute`를 `KN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(KN_JSON_RPC_ERROR_METHOD_NOT_FOUND, TEXT(""));` 없이 끝내면 안 된다
4. `OnExecute` 내에서 GameThread 외 스레드에서 UE API를 호출하면 안 된다 (ServerThread가 이미 GameThread로 디스패치)
5. 커맨드 이름이 다른 플러그인과 충돌하면 안 된다 — 등록 전 반드시 확인
6. `KN_MCP/Python/` 수정 시 Work Rules 2번의 원칙(최소 변경, 하위 호환, 변경 단위 커밋, 사전 승인)을 위반하면 안 된다
7. 사용자 승인 없이 커맨드를 이식하면 안 된다
8. 커맨드 이식 후 커밋하지 않고 다음 작업으로 넘어가면 안 된다
9. `.build.cs` 외 파일에 Copyright header를 추가하면 안 된다: `// Copyright Kangnam Kim. All Rights Reserved.`
10. git commit 메시지에 `Co-Authored-By` 라인을 추가하면 안 된다

---

## Command Status

### Actor Commands — `KN_MCP_EXTENSION` (Runtime)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `get_actors_in_level` | Actor | Done |
| `find_actors_by_name` | Actor | Done |
| `spawn_actor` | Actor | Done |
| `delete_actor` | Actor | Done |
| `set_actor_transform` | Actor | Done |
| `read_actor_content` | Actor | Done |

### Actor Component Commands — `KN_MCP_EXTENSION` (Runtime)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `add_component_to_actor` | ActorComponent | Done |
| `remove_component_from_actor` | ActorComponent | Done |
| `read_components_from_actor` | ActorComponent | Done |

### Blueprint Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `create_blueprint` | Blueprint | Done |
| `read_blueprint_content` | Blueprint | Done |
| `compile_blueprint` | Blueprint | Done |
| `delete_blueprint` | Blueprint | Done |
| `get_blueprints` | Blueprint | Done |
| `find_blueprints_by_name` | Blueprint | Done |
| `spawn_blueprint_actor` | Blueprint | Done |

### Blueprint Component Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `add_component_to_blueprint` | BlueprintComponent | Done |
| `remove_component_from_blueprint` | BlueprintComponent | Done |
| `read_components_from_blueprint` | BlueprintComponent | Done |

### Property Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `set_static_mesh_properties` | Property | Done |
| `set_physics_properties` | Property | Done |

### StaticMesh Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `get_static_meshes` | StaticMesh | Done |
| `find_static_meshes_by_name` | StaticMesh | Done |

### Material Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `get_available_materials` | Material | Done |
| `apply_material_to_actor` | Material | Done |
| `apply_material_to_blueprint` | Material | Done |
| `get_actor_material_info` | Material | Done |
| `get_blueprint_material_info` | Material | Done |
| `set_mesh_material_color` | Material | Done |

### Shared Utilities — `KN_MCP_EXTENSION` (Runtime)

| Utility | File | Used By |
|---------|------|---------|
| `FKN_MCP_ActorUtils::FindActorByName` | `Public/KN_MCP_ActorUtils.h` | Actor, ActorComponent, Material |

### Shared Utilities — `KN_MCP_EXTENSION_Editor`

| Utility | File | Used By |
|---------|------|---------|
| `FKN_MCP_BlueprintUtils::FindBlueprintByName` | `KN_MCP_BlueprintUtils.h/.cpp` | Blueprint, BlueprintComponent, Property, Material, BlueprintVariable, BlueprintGraph |
| `FKN_MCP_BlueprintUtils::FindSCSNodeByName` | `KN_MCP_BlueprintUtils.h/.cpp` | BlueprintComponent, Property, Material |

### Blueprint Variable Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `add_variable_to_blueprint` | BlueprintVariable | Done |
| `remove_variable_from_blueprint` | BlueprintVariable | Done |

### Blueprint Graph Commands — `KN_MCP_EXTENSION_Editor` (Editor)

| Command | CommandGroup | Status |
|---------|-------------|--------|
| `read_blueprint_graph` | BlueprintGraph | Done |
| `add_event_node` | BlueprintGraph | Done |
| `add_function_call_node` | BlueprintGraph | Done |
| `add_variable_get_node` | BlueprintGraph | Done |
| `add_variable_set_node` | BlueprintGraph | Done |
| `connect_nodes` | BlueprintGraph | Done |
| `disconnect_nodes` | BlueprintGraph | Done |

### Skipped

| Command | Reason |
|---------|--------|
| `focus_viewport` | CRUD 범위 밖 |
| `take_screenshot` | CRUD 범위 밖 |
