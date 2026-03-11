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
│  │ • extract command name         │   │
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
    │   └── "WN_MCP_WORLD_spawn_actor" → FWN_MCP_CommandGroup_Actor
    │   └── "WN_MCP_WORLD_get_blueprints" → FWN_MCP_CommandGroup_Blueprint
    │   └── ...
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
6. Python MCP Server 시작
   └── lifespan → UnrealConnection.connect()
       └── get_user_tool_directories 호출
           └── 확장 플러그인 Tool 동적 발견/등록
```

### 커맨드 디스패치 흐름

```
Python: send_command("spawn_actor", {name: "Cube", ...}, app_name="WN_MCP_WORLD")
    │
    │ TCP JSON-RPC: {"method":"command", "id":"WN_MCP_WORLD_spawn_actor", "params":{...}}
    │
    ▼
ServerThread: recv → parse JSON → extract id="WN_MCP_WORLD_spawn_actor"
    │
    │ AsyncTask(GameThread)
    ▼
FWN_MCP_Module::ExecuteCommand("WN_MCP_WORLD_spawn_actor", params)
    │
    │ CommandGroupPtrMap["WN_MCP_WORLD_spawn_actor"] → FWN_MCP_CommandGroup_Actor
    │
    ▼
FWN_MCP_CommandGroup::Execute("WN_MCP_WORLD_spawn_actor", params)
    │
    │ Strip prefix: "WN_MCP_WORLD_spawn_actor" → "spawn_actor"
    │
    ▼
FWN_MCP_CommandGroup_Actor::OnExecute("spawn_actor", params)
    │
    │ if (InCommandName == "spawn_actor") { ... }
    │
    ▼
WN_RETURN_COMMAND_RESPONSE(result)
    │
    │ JSON-RPC 2.0 응답 구성
    │
    ▼
ServerThread: FTCHARToUTF8 → Send response
```

## Python MCP Server (PyMCP)

### 목표 아키텍처 (확정)

PyMCP가 유일한 MCP Server. 각 플러그인은 `Python/` 폴더에 Tool만 제공한다.

```
PyMCP (유일한 MCP Server)
    │
    ├── 코어 기능: 연결, 프로토콜, Tool 발견, 프롬프트
    │
    └── 동적 Import (AddUserToolDirectories)
        ├── WN_MCP_WORLD/Python/tools/   ← 38개 Tool
        ├── WN_MCP_XXX/Python/tools/     ← 향후 추가 플러그인
        └── ...
```

### 현재 과도기 상태

| 구분 | 위치 | 설명 | 향후 |
|------|------|------|------|
| **PyMCP** | `WN_MCP/PyMCP/src/unreal_mcp/` | 코어 서버. FastMCP 3.x | 유일한 서버로 유지 |
| **PyMCP 내장 UE Tool** | `WN_MCP/PyMCP/src/unreal_mcp/tools/ue/` | Actor/Blueprint/Material (~15개) | **제거** (플러그인으로 이관) |
| **WN_MCP_WORLD Python** | `WN_MCP_WORLD/Python/` | 38개 Tool + 224 테스트 | Tool 모듈만 잔존, mcp_server.py 제거 |
| **PyMCP 레거시** | `WN_MCP/PyMCP/Tools/` | 구 구현 | **제거** |

> 마이그레이션 상세는 [TODO.md](TODO.md) P0 참조

### PyMCP 서버 팩토리

```python
# server.py
def create_app(settings) -> FastMCP:
    mcp = FastMCP("unreal-mcp-server")

    @mcp.lifespan
    async def _lifespan(app):
        connection = UnrealConnection(settings)
        connection.connect()
        yield {"connection": connection}
        connection.disconnect()

    # Tool 등록 (조건부)
    general.register_tools(mcp, get_connection)
    agent.register_tools(mcp, get_connection)
    actors.register_tools(mcp, get_connection)      # Actor CRUD
    blueprints.register_tools(mcp, get_connection)   # Blueprint CRUD
    materials.register_tools(mcp, get_connection)    # Material ops
    # ...

    return mcp
```

### 사용자 Tool 동적 발견

```python
# user_tools.py
# 서버 시작 시 get_user_tool_directories → 디렉토리 목록 수신
# 각 디렉토리의 .py 파일을 importlib로 동적 로드
# register_tools(mcp, get_connection) 패턴으로 등록
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
├── mcp_server.py          # 별도 FastMCP 서버 (독립 실행)
└── tools/
    ├── __init__.py        # register_all_tools()
    ├── ue_connection.py   # TCP 연결 유틸리티
    └── actor_tools.py     # @mcp.tool 데코레이터로 등록
```

> 현재 WN_MCP_WORLD는 자체 MCP 서버(`mcp_server.py`)로 운영 중이지만,
> 종래에는 PyMCP의 동적 Import로 전환하고 자체 서버는 제거할 예정이다.
