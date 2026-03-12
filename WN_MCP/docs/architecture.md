# WN_MCP 상세 아키텍처

## 통신 흐름

```
┌──────────────────┐
│   AI Agent       │
│  (Claude/Cursor) │
└────────┬─────────┘
         │ stdio (stdin/stdout)
         │
┌────────▼─────────────────────────────┐
│  Python MCP Server (FastMCP)         │
│                                      │
│  ┌─────────────┐  ┌───────────────┐  │
│  │ @mcp.tool() │  │ @mcp.tool()   │  │
│  │ spawn_actor │  │ get_blueprints│  │
│  └──────┬──────┘  └──────┬────────┘  │
│         │                │           │
│  ┌──────▼────────────────▼────────┐  │
│  │ UnrealConnection               │  │
│  │ send_command(name, params)     │  │
│  │ → JSON-RPC 2.0 request        │  │
│  └──────┬─────────────────────────┘  │
└─────────┼────────────────────────────┘
          │ TCP (127.0.0.1:27777~27787)
          │
┌─────────▼────────────────────────────┐
│  UE C++ TCP Server                    │
│                                       │
│  ┌────────────────────────────────┐   │
│  │ FWN_MCP_ServerThread           │   │
│  │ • recv JSON-RPC request        │   │
│  │ • extract "id" as command name │   │
│  │ • AsyncTask → GameThread       │   │
│  └────────────┬───────────────────┘   │
│               │                       │
│  ┌────────────▼───────────────────┐   │
│  │ GameThread                     │   │
│  │ FWN_MCP_Module::ExecuteCommand │   │
│  │ • CommandGroupPtrMap 조회      │   │
│  │ • OnExecute() 호출             │   │
│  │ • JSON 결과 생성               │   │
│  └────────────┬───────────────────┘   │
│               │                       │
│  ┌────────────▼───────────────────┐   │
│  │ FWN_MCP_ServerThread           │   │
│  │ • FTCHARToUTF8 변환            │   │
│  │ • send JSON-RPC response       │   │
│  └────────────────────────────────┘   │
└───────────────────────────────────────┘
```

## 모듈 시스템

### FWN_MCP_Module (싱글톤)

```
FWN_MCP_Module::Get()
    │
    ├── CommandGroupPtrs: TArray<TSharedPtr<FWN_MCP_CommandGroup>>
    │   └── 등록된 모든 커맨드 그룹 (순서 보장)
    │
    ├── CommandGroupPtrMap: TMap<FString, TSharedPtr<FWN_MCP_CommandGroup>>
    │   └── "Actor_spawn_actor" → FWN_MCP_CommandGroup_Actor
    │   └── "Blueprint_get_blueprints" → FWN_MCP_CommandGroup_Blueprint
    │   └── ...
    │
    ├── AllCommandInfos: TArray<FWN_MCP_CommandInfo>
    │   └── 등록된 모든 커맨드의 메타데이터 (Name, Description, bIsSimple)
    │
    ├── ListenerSocketPtr: TSharedPtr<FSocket>
    │   └── TCP 리스닝 소켓 (127.0.0.1:27777~27787)
    │
    ├── ServerThreadPtr: TSharedPtr<FWN_MCP_ServerThread>
    │   └── 백그라운드 TCP 수신 스레드
    │
    ├── UserToolDirectories: TArray<FString>
    │   └── 확장 플러그인이 등록한 Python Tool 디렉토리
    │
    └── Public API
        ├── RegisterCommandGroup(group)    // 커맨드 그룹 등록
        ├── ExecuteCommand(name, params)   // 커맨드 실행
        ├── GetListenerPort()              // 현재 포트 조회
        ├── IsRunningServer()              // 서버 상태
        ├── GetAllCommandInfos()           // 등록된 커맨드 메타데이터
        └── AddUserToolDirectories(dirs)   // Tool 디렉토리 추가
```

### 시작 순서

```
1. UE 엔진 시작
2. WN_MCP 모듈 로드
   └── static 초기화: WN_MCP_REGISTER_COMMAND_GROUP 매크로 실행
       └── 각 CommandGroup 인스턴스 생성 → RegisterCommandGroup() 호출
3. StartupModule()
   └── OnPostEngineInit 콜백 등록
4. 엔진 초기화 완료
   └── OnPostEngineInit 발동
       └── StartServer()
           ├── 포트 자동 탐색 (27777~27787)
           ├── TCP 리스닝 소켓 생성
           └── FWN_MCP_ServerThread 생성 및 시작
5. 확장 플러그인 로드 (WN_MCP_WORLD 등)
   └── StartupModule()에서 AddUserToolDirectories() 호출
6. Python MCP Server 시작 (wn_mcp_server.py lifespan)
   ├── _register_tools()          — 정적 Tool 등록 (UE 연결/해제, 로그 등)
   ├── ue_connect()               — UE TCP 연결 (listening 중이면)
   ├── register_user_tool_dirs()  — 확장 플러그인 Tool 동적 발견/등록 (yield 전)
   ├── register callback          — 재연결 시 Tool 재등록용 콜백 등록
   └── yield                      — MCP 클라이언트 요청 수신 시작
```

> **주의**: Tool 등록은 반드시 `yield` 전에 완료해야 한다.
> MCP 클라이언트(Claude Code 등)는 `yield` 직후 `tools/list`를 요청하고 결과를 캐시하기 때문에,
> `yield` 이후에 등록된 Tool은 클라이언트에 보이지 않는다.
> 재연결 시에는 `refresh_tools` Tool을 호출하여 `tools/list_changed` 알림을 보낼 수 있다.

### 커맨드 디스패치 흐름

```
Python: ue_connection.execute("spawn_actor", params, category_name="Actor")
    │
    │ → UnrealConnection.send_command("Actor_spawn_actor", params)
    │
    │ TCP JSON-RPC: {"jsonrpc":"2.0", "method":"Actor_spawn_actor", "id":"Actor_spawn_actor", "params":{...}}
    │
    ▼
ServerThread: recv → parse JSON → extract id="Actor_spawn_actor"
    │
    │ AsyncTask(GameThread)
    ▼
FWN_MCP_Module::ExecuteCommand("Actor_spawn_actor", params)
    │
    │ CommandGroupPtrMap["Actor_spawn_actor"] → FWN_MCP_CommandGroup_Actor
    │
    ▼
FWN_MCP_CommandGroup::Execute("Actor_spawn_actor", params)
    │
    │ Strip prefix: "Actor_spawn_actor" → "spawn_actor"
    │
    ▼
FWN_MCP_CommandGroup_Actor::OnExecute("spawn_actor", params)
    │
    │ if (InCommandName == "spawn_actor") { ... }
    │
    ▼
WN_RETURN_COMMAND_RESPONSE(result)
    │
    │ JSON-RPC 2.0 응답 구성 (id, method = "spawn_actor")
    │
    ▼
Execute(): 응답의 id/method를 원래 이름으로 복원
    │
    │ id, method = "Actor_spawn_actor" (요청과 일치)
    │
    ▼
ServerThread: FTCHARToUTF8 → Send response
```

## Python MCP Server (PyMCP)

PyMCP(`WN_MCP/PyMCP/`)가 유일한 MCP Server.
각 플러그인은 `Python/tools/` 폴더에 Tool만 제공하고, PyMCP가 `AddUserToolDirectories()`로 동적 Import한다.

```
PyMCP (유일한 MCP Server)
    │
    ├── wn_mcp_server.py          — FastMCP 앱 + lifespan (서버 진입점)
    │
    ├── Tool 엔진: Tools/ (ue_interaction_tool.py)
    │   ├── UE 연결/해제/재연결 (auto-reconnect 스레드)
    │   ├── 동적 Tool 발견 (AddUserToolDirectories → @mcp.tool 자동 등록)
    │   ├── Simple Command 자동 래핑
    │   ├── refresh_tools — tools/list_changed 알림 전송 (재연결 대응)
    │   └── UE 종료 시 Tool 해제 (MCP_SERVER.remove_tool)
    │
    └── 동적 Import (AddUserToolDirectories)
        ├── WN_MCP_WORLD/Python/tools/   ← 38개 Tool
        ├── WN_MCP_XXX/Python/tools/     ← 향후 추가 플러그인
        └── ...
```

### WORLD Tool 연결

WORLD Tool은 `ue_connection.execute()` 호출 → 자체 TCP 소켓으로 UE에 JSON-RPC 2.0 커맨드를 전송한다.

```python
# WN_MCP_WORLD/Python/tools/ue_connection.py (자체 TCP 연결)
def execute(command_name, params=None, category_name=""):
    connect()  # 127.0.0.1:27777 자체 소켓
    full_name = f"{category_name}_{command_name}" if category_name else command_name
    # JSON-RPC 2.0 요청 전송 → 응답 수신 → 결과 반환
    return result

# WN_MCP_WORLD/Python/tools/actor_tools.py (Tool)
_CATEGORY = "Actor"
@mcp.tool
def spawn_actor(type, name, ...):
    result = ue_connection.execute("spawn_actor", params, category_name=_CATEGORY)
    return json.dumps(result, ...)
```

## 확장 플러그인 패턴

### C++ 측

```
WN_MCP_WORLD/
├── WN_MCP_WORLD.uplugin
│   └── Plugins: [{"Name": "WN_MCP", "Enabled": true}]
│
├── Source/WN_MCP_WORLD/
│   ├── WN_MCP_WORLD.build.cs
│   │   └── PrivateDependencyModuleNames: ["WN_MCP"]
│   │
│   └── Private/
│       └── WN_MCP_WORLD_Module.cpp
│           └── StartupModule()
│               └── FWN_MCP_Module::Get().AddUserToolDirectories({PythonDir})
│
└── Source/WN_MCP_WORLD_Editor/
    └── Private/Commands/
        └── WN_MCP_CommandGroup_XXX.h/.cpp
            └── WN_MCP_REGISTER_COMMAND_GROUP(...)  // 자동 등록
```

### Python 측

```
WN_MCP_WORLD/Python/
└── tools/
    ├── __init__.py            # register_all_tools()
    ├── ue_connection.py       # 자체 TCP 연결 유틸리티
    ├── actor_tools.py         # @mcp.tool (6개, _CATEGORY = "Actor")
    ├── blueprint_tools.py     # @mcp.tool (7개, _CATEGORY = "Blueprint")
    └── ...                    # 9개 모듈, 38개 Tool
```

WORLD Tool은 PyMCP 프로세스 내에서 실행되며, `ue_connection.py`의 자체 TCP 소켓으로 UE와 통신한다. (PyMCP의 `UnrealConnection`은 커맨드마다 소켓을 열고 닫으므로 충돌하지 않는다.)
