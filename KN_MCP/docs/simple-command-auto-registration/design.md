# SimpleCommand 자동 등록 설계

> 작성: 2026-03-13
> 대상: `KN_MCP/Python/kn_mcp/` (코어 변경)

## 목적

C++에서 `KN_MCP_REGISTER_SIMPLE_COMMAND`로 등록한 커맨드를 Python MCP 서버 시작 시 자동으로 `@mcp.tool()`로 등록하여, Python Tool 코드를 작성하지 않아도 Agent가 직접 호출 가능하게 한다.

## 현재 상태 (문제)

```
C++ (OK)                              Python (MISSING)
─────────────                         ──────────────
KN_MCP_REGISTER_SIMPLE_COMMAND        ???
  ↓ bIsSimple=true
get_simple_commands → JSON            No code calls get_simple_commands
  {"commands": [{name, desc}]}        No dynamic @mcp.tool() creation
```

- C++: `bIsSimple=true` 등록 + `get_simple_commands`로 목록 반환 → 완성
- Python: `get_simple_commands`를 호출하는 코드 없음. 동적 Tool 등록 코드 없음 → **미구현**

## 아키텍처

```
Agent ←stdio→ Python MCP Server (Tool) ←TCP JSON-RPC→ UE C++ Plugin (Command)
                    │
         ┌──────────┴──────────┐
         │ server.py lifespan  │
         │                     │
         │ 1. UE 연결          │
         │ 2. get_simple_commands 호출
         │ 3. 각 command → @mcp.tool() 동적 등록
         │ 4. user_tool_directories 등록
         └─────────────────────┘
```

## 데이터 흐름

1. Python lifespan → `conn.send_command("Application_get_simple_commands", {})`
2. C++ → `{"commands": [{"name": "Test_get_hello_message", "description": "Get hello message from UE"}]}`
3. Python: 각 command에 대해:
   - `name = "Test_get_hello_message"` → Tool 이름: `"Test_get_hello_message"`
   - `description = "Get hello message from UE"` → Tool docstring
   - 동적으로 `@mcp.tool()` 등록: Agent 호출 시 `conn.send_command(name, {})` 실행

## API 설계

### 새 모듈: `kn_mcp/tools/simple_commands.py`

```python
def get_simple_commands() -> list[dict[str, str]]:
    """UE에서 SimpleCommand 목록 조회. Returns [{"name": ..., "description": ...}]."""

def register_simple_commands(server: FastMCP) -> None:
    """SimpleCommand 목록을 조회하고 각각을 @mcp.tool()로 동적 등록."""
```

### 동적 Tool 생성 패턴

```python
def _make_simple_tool(cmd_name: str, cmd_desc: str):
    """SimpleCommand를 위한 Tool 함수 생성."""
    def tool_fn() -> str:
        conn = get_unreal_connection()
        if conn is None:
            return json.dumps({"status": "error", "error": "Not connected to UE"})
        result = conn.send_command(cmd_name, {})
        if result is None:
            return json.dumps({"status": "error", "error": "No response from UE"})
        return json.dumps(result, indent=2, ensure_ascii=False)

    tool_fn.__name__ = cmd_name
    tool_fn.__doc__ = cmd_desc
    return tool_fn
```

### server.py lifespan 변경

```python
if conn.connect():
    # 1. SimpleCommand 자동 등록 (C++ 에서 등록한 Simple 커맨드)
    simple_commands.register_simple_commands(server)
    # 2. User tool directories (확장 플러그인 Python Tool)
    user_tools.register_user_tool_directories(server)
```

## 파일 구조

```
KN_MCP/Python/kn_mcp/
  tools/
    simple_commands.py    ← 신규
  server.py              ← 수정 (import + lifespan에 호출 추가)
```

## 의사결정 근거

1. **별도 모듈(`simple_commands.py`)**: `user_tools.py`와 역할이 다름 (파일 스캔 vs UE 쿼리). 분리가 명확.
2. **파라미터 없는 Tool**: SimpleCommand는 정의상 파라미터 없이 호출 → 결과 반환. C++ 쪽에서 모든 로직 처리.
3. **Tool 이름 = Command 이름**: `Test_get_hello_message` 그대로 사용. 이미 `{GroupName}_{command_name}` 형태로 네임스페이스가 포함됨.
4. **JSON string 반환**: 기존 Extension Tool 패턴(`json.dumps(result)`)과 동일.
5. **lifespan에서 user_tools보다 먼저 등록**: SimpleCommand가 기본 기능이므로 먼저 등록. user_tools가 같은 이름의 Tool을 등록하면 그것이 우선.
