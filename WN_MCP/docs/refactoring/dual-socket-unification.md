# 듀얼 소켓 통합 리팩터링

## 문제

PyMCP에 TCP 소켓이 2개 존재:

1. **Core** (`ue_interaction_tool.py`): `UE_SOCKET` - auto-reconnect, callback 지원, Lock 없음
2. **WORLD** (`ue_connection.py`): `_socket` - `threading.Lock`, `category_name` prefix

C++ 서버는 **단일 클라이언트만 처리** -> 소켓 2개 동시 연결 시 충돌 위험.
WORLD가 독립 MCP 서버였을 때의 잔재.

## Before

```
Agent -> PyMCP -> ue_interaction_tool.py (UE_SOCKET)  -> UE C++ Server
                  ue_connection.py (_socket)           -> UE C++ Server  (충돌!)
```

- Core Tool (check_ue_connection 등): `ue_interaction_tool.ue_send_command()` 사용
- WORLD Tool 38개: `ue_connection.execute()` 사용 (별도 소켓)
- 두 소켓이 동시에 같은 TCP 포트 접근 -> 응답 혼선

## After

```
Agent -> PyMCP -> ue_interaction_tool.py (UE_SOCKET)  -> UE C++ Server
```

- 모든 Tool이 `ue_interaction_tool.ue_send_command()` 사용
- `ue_connection.py` 삭제
- `ue_send_command()`에 `category_name` 파라미터 추가 (하위 호환)

## 결정 근거

1. **단일 소켓**: C++ 서버가 단일 클라이언트 설계 -> 소켓 1개가 올바름
2. **Core가 상위**: auto-reconnect, callback 등 인프라가 Core에 있음
3. **category_name 추가**: `ue_connection.execute()`의 `category_name` 기능을 Core에 이식
4. **하위 호환**: `category_name=""` 기본값 -> 기존 Core Tool 호출자 변경 없음

## 변경 범위

| 파일 | 변경 |
|------|------|
| `WN_MCP/PyMCP/Tools/ue_interaction_tool.py` | `ue_send_command()` category_name 추가 |
| `WN_MCP_WORLD/Python/tools/ue_connection.py` | **삭제** |
| `WN_MCP_WORLD/Python/tools/*_tools.py` (9개) | import + call 패턴 변경 |
| `WN_MCPTest/Python/test_tool.py` | import + call 패턴 변경 |
| `WN_MCP_WORLD/Python/tests/conftest.py` | mock fixture 타겟 변경 |
