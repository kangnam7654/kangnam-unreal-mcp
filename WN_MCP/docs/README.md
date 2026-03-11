# WN_MCP — Core MCP Plugin

Unreal Engine 5용 MCP(Model Context Protocol) 코어 플러그인.
AI 에이전트(Claude Code, Cursor 등)가 UE 에디터를 제어할 수 있는 TCP 서버 + 커맨드 그룹 시스템을 제공한다.

> **이 플러그인은 수정 금지.** 기능 확장은 WN_MCP_WORLD 같은 별도 플러그인으로 수행한다.

## 아키텍처

```
AI Agent (Claude/Cursor)
    │ stdio
    ▼
Python MCP Server (FastMCP)     ← WN_MCP/PyMCP/
    │ TCP JSON-RPC 2.0
    ▼
UE C++ TCP Server               ← WN_MCP/Source/
    │ GameThread dispatch
    ▼
Unreal Engine API
```

### 핵심 구성요소

| 구성요소 | 역할 |
|----------|------|
| **FWN_MCP_Module** | 모듈 싱글톤. 커맨드 그룹 레지스트리 관리, TCP 서버 시작/중지 |
| **FWN_MCP_ServerThread** | TCP 서버 스레드. JSON-RPC 2.0 수신 → GameThread 디스패치 → 응답 전송 |
| **FWN_MCP_CommandGroup** | 커맨드 그룹 베이스 클래스. 모든 커맨드 구현의 부모 |
| **FWN_MCP_CommandInfo** | 커맨드 메타데이터 구조체 (Name, Description, bIsSimple) |
| **PyMCP Server** | Python FastMCP 서버. Agent ↔ UE 중계 (stdio transport) |

## 파일 구조

```
WN_MCP/
├── WN_MCP.uplugin                              # 플러그인 설정 (Runtime, Win64)
├── Source/WN_MCP/
│   ├── WN_MCP.build.cs                         # 빌드 설정 (의존성, 예외 처리 활성화)
│   ├── Public/
│   │   ├── WN_MCP_Module.h                     # 모듈 인터페이스 (싱글톤, Public API)
│   │   └── WN_MCP_CommandGroup.h               # 베이스 클래스 + 매크로 + JSON-RPC 에러코드
│   └── Private/
│       ├── WN_MCP_Module.cpp                   # 모듈 구현 (서버 시작, 커맨드 디스패치)
│       ├── WN_MCP_CommandGroup.cpp             # 베이스 클래스 구현 (Execute → OnExecute)
│       ├── WN_MCP_ServerThread.h/.cpp          # TCP 서버 스레드 (GameThread 디스패치)
│       └── Commands/
│           └── WN_MCP_CommandGroup_Application.h/.cpp  # get_user_tool_directories
├── PyMCP/                                       # Python MCP Server
│   ├── main.py                                 # 진입점 (FastMCP stdio transport)
│   ├── pyproject.toml                          # Python 의존성
│   ├── src/unreal_mcp/
│   │   ├── server.py                           # FastMCP 앱 팩토리 + lifespan
│   │   ├── config.py                           # 환경변수 기반 설정
│   │   ├── connection.py                       # UE TCP 연결 (재시도 로직)
│   │   ├── core/protocol.py                    # JSON-RPC 2.0 프로토콜 계층
│   │   ├── helpers/                            # 유틸리티 (actor_name_manager 등)
│   │   ├── tools/                              # 내장 Tool 모듈
│   │   │   ├── general.py                      # UE 상태 확인, 연결 체크
│   │   │   ├── agent.py                        # Agent 알림/질문
│   │   │   ├── logging.py                      # 로그 레벨 제어
│   │   │   ├── user_tools.py                   # 사용자 Tool 동적 발견/등록
│   │   │   └── ue/                             # UE 조작 Tool
│   │   │       ├── actors.py                   # Actor CRUD
│   │   │       ├── blueprints.py               # Blueprint CRUD
│   │   │       ├── blueprints_graph.py         # Blueprint 그래프
│   │   │       └── materials.py                # Material 조작
│   │   └── prompts.py                          # MCP 프롬프트 (Agent 가이드)
│   └── Tools/                                  # (레거시 — 미사용)
└── docs/
    ├── README.md                               # 이 문서
    ├── architecture.md                         # 상세 아키텍처 문서
    └── bugfix/
        └── utf8-response-truncation.md         # UTF-8 응답 잘림 버그 수정 기록
```

## 핵심 메커니즘

### 1. 커맨드 등록 시스템

```cpp
// 1. CommandGroup 서브클래스 생성
class FWN_MCP_CommandGroup_Actor : public FWN_MCP_CommandGroup { ... };

// 2. 자동 등록 매크로 (static 초기화 시점에 실행)
WN_MCP_REGISTER_COMMAND_GROUP(FWN_MCP_CommandGroup_Actor);

// 3. GetApplicationName() → prefix 반환 (충돌 방지)
FString GetApplicationName() const override { return "WN_MCP_WORLD"; }

// 4. 커맨드 등록 (prefix 자동 부여: "WN_MCP_WORLD_spawn_actor")
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const override {
    WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "spawn_actor", "Spawn an actor");
}

// 5. OnExecute에서는 prefix 없는 원래 이름으로 매칭
if (InCommandName == FString(TEXT("spawn_actor"))) { ... }
```

### 2. TCP 서버 & GameThread 디스패치

```
ServerThread (백그라운드)          GameThread (메인)
    │                                │
    │ recv JSON-RPC request          │
    │ ──────────────────────────►    │
    │                                │ ExecuteCommand()
    │                                │ → CommandGroupPtrMap 조회
    │                                │ → OnExecute() 호출
    │                                │ → 결과 JSON 생성
    │ ◄──────────────────────────    │
    │ send JSON-RPC response         │
```

- **포트 자동 탐색**: 27777~27787 범위에서 사용 가능한 포트 자동 선택
- **localhost 전용**: 127.0.0.1 바인딩 (보안)
- **버퍼**: 수신 8KB, 소켓 64KB

### 3. JSON-RPC 2.0 프로토콜

**요청** (Python → UE):
```json
{"jsonrpc": "2.0", "method": "command", "id": "WN_MCP_WORLD_spawn_actor", "params": {...}}
```

**성공 응답** (UE → Python):
```json
{"jsonrpc": "2.0", "result": {...}, "id": "WN_MCP_WORLD_spawn_actor"}
```

**에러 응답** (UE → Python):
```json
{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": "..."}
```

### 4. 응답 매크로

| 매크로 | 용도 |
|--------|------|
| `WN_RETURN_COMMAND_RESPONSE(InResultPtr)` | 오브젝트 결과 |
| `WN_RETURN_COMMAND_ARRAY_RESPONSE(array)` | 배열 결과 |
| `WN_RETURN_COMMAND_TEXT_RESPONSE(TEXT("msg"))` | 텍스트 결과 |
| `WN_RETURN_COMMAND_ERROR_TEXT_RESPONSE(code, TEXT("msg"))` | 에러 + 텍스트 |
| `WN_RETURN_COMMAND_ERROR_RESPONSE(code, errorObj)` | 에러 + 오브젝트 |

### 5. 플러그인 확장 패턴

외부 플러그인(WN_MCP_WORLD 등)이 커맨드를 추가하는 방법:

1. `.build.cs`에서 `WN_MCP` 모듈 의존
2. `StartupModule()`에서 `FWN_MCP_Module::Get().AddUserToolDirectories()` 호출
3. C++ CommandGroup은 `WN_MCP_REGISTER_COMMAND_GROUP` 매크로로 자동 등록
4. Python Tool은 `Python/tools/` 디렉토리에 배치 → 서버가 동적 발견

## 설정

### 환경변수 (Python MCP Server)

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `UNREAL_HOST` | `127.0.0.1` | UE TCP 서버 호스트 |
| `UNREAL_PORT` | (자동 감지) | UE TCP 서버 포트 |
| `UNREAL_CONNECT_TIMEOUT` | `10` | 연결 타임아웃 (초) |
| `UNREAL_RECV_TIMEOUT` | `30` | 수신 타임아웃 (초) |
| `UNREAL_LARGE_OP_TIMEOUT` | `300` | 대용량 작업 타임아웃 (초) |
| `UNREAL_ENABLED_TOOLS` | (전체) | 활성화할 Tool 그룹 (CSV) |

### 빌드 의존성

| 구분 | 모듈 |
|------|------|
| **Public** | Core, CoreUObject, Engine, InputCore, Networking, Sockets, HTTP, Json, JsonUtilities, DeveloperSettings |
| **Private** | Slate, SlateCore, UMG, Projects, AssetRegistry |
| **Editor 전용** | Kismet, KismetCompiler, BlueprintGraph |

## 에러 코드

| 코드 | 이름 | 용도 |
|------|------|------|
| -32700 | Parse error | 잘못된 JSON |
| -32600 | Invalid Request | 유효하지 않은 요청 |
| -32601 | Method not found | 커맨드 미등록 |
| -32602 | Invalid params | 잘못된 파라미터 |
| -32603 | Internal error | 서버 내부 오류 |
| -32000 | Server error | 서버 오류 |
| -32001 | Command failed | 커맨드 실행 실패 |
| -32002 | Invalid arguments | 잘못된 인자 |
| -32003 | UE Communication error | UE 통신 오류 |

## 알려진 이슈 (수정 완료)

| 이슈 | 원인 | 수정 | 상세 |
|------|------|------|------|
| UTF-8 응답 잘림 | `response.Len()` = TCHAR 수 ≠ UTF-8 바이트 수 | `FTCHARToUTF8` 명시적 변환 | [bugfix/utf8-response-truncation.md](bugfix/utf8-response-truncation.md) |
