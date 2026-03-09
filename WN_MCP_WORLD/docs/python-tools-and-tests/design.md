# Python Tools & Tests 설계문서

## 1. 목적

WN_MCP_WORLD의 38개 C++ 커맨드에 대응하는 Python MCP Tool을 구현하고,
전체 기능을 검증할 수 있는 3단계 테스트 체계를 구축한다.

## 2. 완료 상태

### Python Tools (38개, 9개 모듈)

| 모듈 | Tool 수 | 파일 | 상태 |
|------|---------|------|------|
| Actor | 6 | `actor_tools.py` | Done |
| ActorComponent | 3 | `actor_component_tools.py` | Done |
| Blueprint | 7 | `blueprint_tools.py` | Done |
| BlueprintComponent | 3 | `blueprint_component_tools.py` | Done |
| Property | 2 | `property_tools.py` | Done |
| Material | 6 | `material_tools.py` | Done |
| StaticMesh | 2 | `static_mesh_tools.py` | Done |
| BlueprintVariable | 2 | `blueprint_variable_tools.py` | Done |
| BlueprintGraph | 7 | `blueprint_graph_tools.py` | Done |

### 테스트 (135개)

| 구분 | 수 | UE 필요 | 상태 |
|------|---|---------|------|
| Unit | 85 | 아니오 | Done |
| Integration | 42 | 예 | Done |
| E2E | 8 | 예 | Done |

### 커버리지

- Tool 모듈 (ue_connection 제외): **100%**
- 전체: **87%**

## 3. 아키텍처

```
AI Agent (stdio) → Python MCP Server (FastMCP) → TCP JSON-RPC 2.0 → UE C++ Plugin
```

### 모듈 구조

```
tools/
├── __init__.py              # register_all_tools() — 전체 Tool 등록
├── ue_connection.py         # UE TCP 연결 (connect, disconnect, execute)
├── actor_tools.py           # Actor CRUD 6개
├── actor_component_tools.py # ActorComponent CRD 3개
├── blueprint_tools.py       # Blueprint CRUD 7개 (스폰 포함)
├── blueprint_component_tools.py # BlueprintComponent CRD 3개
├── property_tools.py        # Property 설정 2개
├── material_tools.py        # Material CRUD 6개
├── static_mesh_tools.py     # StaticMesh R 2개
├── blueprint_variable_tools.py # BlueprintVariable CD 2개
└── blueprint_graph_tools.py # BlueprintGraph CRUD 7개
```

### Tool 등록 패턴

각 모듈은 `register_tools(mcp: FastMCP)` 함수를 노출한다.
`__init__.py`의 `register_all_tools()`에서 순서대로 호출한다.

```python
# tools/some_tools.py
def register_tools(mcp: FastMCP):
    @mcp.tool
    def some_command(param1: str, param2: Optional[str] = None) -> str:
        """Tool docstring (AI가 읽는 설명)."""
        params: Dict[str, Any] = {"param1": param1}
        if param2 is not None:
            params["param2"] = param2
        result = ue_connection.execute("some_command", params)
        return json.dumps(result, indent=2, ensure_ascii=False)
```

### UE 통신

`ue_connection.py`가 TCP 연결을 관리한다.

- `connect()` — TCP 소켓 연결 (127.0.0.1:27777)
- `disconnect()` — 소켓 종료
- `execute(command_name, params)` — JSON-RPC 2.0 요청 전송 + 응답 파싱

## 4. 테스트 설계

### 4.1 디렉토리 구조

```
tests/
├── conftest.py          # sys.path 설정 + call_tool 헬퍼 + UE Mock fixture 3개
├── test_unit_tools.py   # Unit 테스트 85개 (UE Mock)
├── test_integration.py  # 통합 테스트 42개 (실제 UE)
└── test_e2e.py          # E2E 테스트 8개 (MCP Client)
```

### 4.2 공통 인프라 (conftest.py)

```python
# sys.path 설정 (모든 테스트 파일에서 mcp_server import 가능)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Tool 호출 헬퍼 (Unit + Integration 공통)
def call_tool(tool_name, **kwargs) -> str:
    # async tool 함수를 동기로 resolve + cache + 호출

# Mock fixture 3개
# mock_ue_execute — execute()를 mock하여 UE 연결 없이 테스트
# mock_ue_connection_error — ConnectionError 발생
# mock_ue_runtime_error — RuntimeError 발생
```

### 4.3 Unit Tests (test_unit_tools.py)

UE 연결 없이 Python Tool 로직만 검증한다.
`ue_connection.execute()`를 mock하여 파라미터 전달과 응답 포맷을 테스트한다.

테스트 카테고리:
- 필수 파라미터만 전달 시 정확한 커맨드 호출 확인
- 선택 파라미터 포함 시 params dict에 추가 확인
- 선택 파라미터 생략 시 params dict에 미포함 확인
- JSON 응답 문자열 파싱 확인
- 에러 전파 확인 (ConnectionError, RuntimeError)
- 38개 Tool 등록 확인

### 4.4 Integration Tests (test_integration.py)

실제 UE 에디터에 연결하여 CRUD 시나리오를 검증한다.
`pytest.mark.integration` 마커 사용.

테스트 클래스 (7개):
- `TestActorCRUD` — 액터 생성 → 검색 → 읽기 → 트랜스폼 → 삭제
- `TestActorComponentCRD` — 컴포넌트 추가 → 읽기 → 제거
- `TestBlueprintCRUD` — 블루프린트 생성 → 검색 → 읽기 → 컴파일 → 삭제
- `TestBlueprintComponentCRD` — BP 컴포넌트 추가 → 읽기 → 제거
- `TestPropertyCommands` — BP + 컴포넌트 → 메시 설정 → 물리 설정
- `TestBlueprintSpawn` — BP 생성 → 컴파일 → 스폰 → 존재 확인
- `TestMaterialCommands` — 머티리얼 목록 → 액터 적용 → BP 적용 → 색상 변경

### 4.5 E2E Tests (test_e2e.py)

FastMCP Client를 통해 MCP 프로토콜 전체 흐름을 검증한다.
`pytest.mark.e2e` 마커 사용.

테스트 함수 (8개):
- `test_all_38_tools_registered` — 38개 Tool 등록 확인
- `test_actor_crud_e2e` — Actor 전체 라이프사이클
- `test_actor_component_crud_e2e` — Component 전체 라이프사이클
- `test_blueprint_crud_e2e` — Blueprint + Component 전체 라이프사이클
- `test_property_e2e` — Property 설정 라이프사이클
- `test_blueprint_spawn_e2e` — Blueprint 스폰 라이프사이클
- `test_material_e2e` — Material 조회/적용/색상 라이프사이클
- `test_static_mesh_e2e` — StaticMesh 조회/검색 라이프사이클

### 4.6 실행 방법

```bash
cd WN_MCP_WORLD/Python

# Unit (UE 불필요)
uv run python -m pytest tests/test_unit_tools.py -v

# Integration (UE 실행 필수)
uv run python -m pytest tests/test_integration.py -v

# E2E (UE 실행 필수)
uv run python -m pytest tests/test_e2e.py -v

# 전체
uv run python -m pytest tests/ -v

# 커버리지
uv run python -m pytest tests/test_unit_tools.py --cov=tools --cov-report=term-missing -q
```

## 5. 의사결정 기록

| 결정 | 근거 |
|------|------|
| Tool 모듈 분리 (9개 파일) | 용도별 분리로 파일당 2~7개 함수, 사람이 읽기 쉬움 |
| `register_tools(mcp)` 패턴 | 각 모듈이 자체 등록 — `__init__.py`에서 호출만 하면 됨 |
| `ue_connection.execute()` 공개 API | `_ue_execute` 접두어 제거 — 모든 모듈이 사용하는 공개 함수이므로 |
| `if X is not None` 패턴 유지 | 헬퍼 추출 대신 반복 — 읽기 쉽고, 각 함수가 자기 완결적 |
| `json.dumps()` 래핑 안 함 | 각 함수에서 리턴 형태가 명시적으로 보임 |
| `call_tool()` conftest 통합 | Unit/Integration에서 중복 제거 — 하나의 소스 |
| `delete_blueprint` force를 `Optional[bool]` | 다른 optional 파라미터와 패턴 통일 |
| E2E `safe_delete_*` 헬퍼 | 이전 실행 잔여물 정리 + try/finally 보장 |
