# Python Tools & Tests 설계문서

## 1. 목적

WN_MCP_WORLD의 18개 C++ 커맨드에 대응하는 Python MCP Tool을 완성하고,
전체 기능을 검증할 수 있는 테스트 체계를 구축한다.

## 2. 현재 상태

### Python Tools (mcp_server.py)

| 구분 | Tool | 상태 |
|------|------|------|
| Actor | `get_actors_in_level` | Done |
| Actor | `find_actors_by_name` | Done |
| Actor | `spawn_actor` | Done |
| Actor | `delete_actor` | Done |
| Actor | `set_actor_transform` | Done |
| Actor | `read_actor_content` | **수정 필요** (docstring에 component 언급 제거) |
| Blueprint | `get_blueprints` | Done |
| Blueprint | `find_blueprints_by_name` | Done |
| Blueprint | `create_blueprint` | Done |
| Blueprint | `read_blueprint_content` | **수정 필요** (`include_components` 파라미터 제거) |
| Blueprint | `compile_blueprint` | Done |
| Blueprint | `delete_blueprint` | Done |
| ActorComponent | `add_component_to_actor` | **신규** |
| ActorComponent | `remove_component_from_actor` | **신규** |
| ActorComponent | `read_components_from_actor` | **신규** |
| BlueprintComponent | `add_component_to_blueprint` | **신규** |
| BlueprintComponent | `remove_component_from_blueprint` | **신규** |
| BlueprintComponent | `read_components_from_blueprint` | **신규** |

### 변경 작업 요약

1. **신규 Tool 6개** — Component CRUD
2. **수정 Tool 2개** — component 관련 파라미터/docstring 제거
3. **테스트 체계** — Unit / Integration / E2E

## 3. Python Tool 설계

### 3.1 신규 Tool 시그니처

```python
# --- ActorComponent ---

@mcp.tool
def add_component_to_actor(
    name: str,                              # 액터 이름
    component_class: str,                   # 컴포넌트 클래스명 (e.g. "StaticMeshComponent")
    component_name: Optional[str] = None,   # 컴포넌트 이름 (생략 시 자동 생성)
) -> str

@mcp.tool
def remove_component_from_actor(
    name: str,               # 액터 이름
    component_name: str,     # 제거할 컴포넌트 이름
) -> str

@mcp.tool
def read_components_from_actor(
    name: str,               # 액터 이름
) -> str

# --- BlueprintComponent ---

@mcp.tool
def add_component_to_blueprint(
    blueprint_name: str,                        # 블루프린트 이름 또는 경로
    component_class: str,                       # 컴포넌트 클래스명
    component_name: Optional[str] = None,       # 컴포넌트 이름 (생략 시 자동)
    parent_component: Optional[str] = None,     # 부모 컴포넌트 이름
) -> str

@mcp.tool
def remove_component_from_blueprint(
    blueprint_name: str,     # 블루프린트 이름 또는 경로
    component_name: str,     # 제거할 컴포넌트 이름
) -> str

@mcp.tool
def read_components_from_blueprint(
    blueprint_name: str,     # 블루프린트 이름 또는 경로
) -> str
```

### 3.2 기존 Tool 수정

**`read_actor_content`** — docstring 수정:
- Before: "including its components"
- After: component 관련 문구 제거, `read_components_from_actor` 안내 추가

**`read_blueprint_content`** — 파라미터/docstring 수정:
- `include_components` 파라미터 제거
- docstring에서 "components" 문구 제거, `read_components_from_blueprint` 안내 추가

### 3.3 C++ 커맨드명 ↔ Python Tool 파라미터 매핑

| C++ param | Python param | 비고 |
|-----------|-------------|------|
| `name` (actor) | `name` | Actor 커맨드에서는 `name` |
| `blueprint_name` | `blueprint_name` | Blueprint 커맨드에서 |
| `component_class` | `component_class` | |
| `component_name` | `component_name` | |
| `parent_component` | `parent_component` | Blueprint 전용 |

## 4. 테스트 설계

### 4.1 디렉토리 구조

```
WN_MCP_WORLD/Python/
  mcp_server.py
  pyproject.toml
  tests/
    conftest.py              # pytest fixtures (mock UE connection 등)
    test_unit_tools.py       # Unit tests — _ue_execute를 mock
    test_integration.py      # Integration tests — 실제 UE 연결 필요
    test_e2e.py              # E2E tests — MCP 클라이언트로 전체 흐름
```

### 4.2 Unit Tests (`test_unit_tools.py`)

UE 연결 없이 Python Tool 로직만 검증.
`_ue_execute`를 mock하여 파라미터 전달과 응답 파싱을 테스트.

```python
# 테스트 항목 (18 tools × 2~3 cases = 40~50 tests)

# Actor Tools
- test_get_actors_in_level_calls_correct_command
- test_find_actors_by_name_passes_search_text
- test_spawn_actor_required_params
- test_spawn_actor_optional_params
- test_delete_actor_passes_name
- test_set_actor_transform_partial_params
- test_read_actor_content_passes_name

# ActorComponent Tools
- test_add_component_to_actor_required_params
- test_add_component_to_actor_optional_name
- test_remove_component_from_actor_params
- test_read_components_from_actor_params

# Blueprint Tools
- test_get_blueprints_default
- test_get_blueprints_with_search_path
- test_find_blueprints_by_name_params
- test_create_blueprint_required_params
- test_create_blueprint_with_parent_class
- test_read_blueprint_content_no_component_param  # include_components 제거 확인
- test_compile_blueprint_params
- test_delete_blueprint_default
- test_delete_blueprint_force

# BlueprintComponent Tools
- test_add_component_to_blueprint_required_params
- test_add_component_to_blueprint_with_parent
- test_remove_component_from_blueprint_params
- test_read_components_from_blueprint_params

# Error Handling
- test_ue_connection_error_raises
- test_ue_error_response_raises
```

### 4.3 Integration Tests (`test_integration.py`)

실제 UE 에디터가 실행 중일 때만 수행. `pytest.mark.integration` 마커 사용.

```python
# 전제조건: UE 에디터 실행 + WN_MCP 플러그인 로드 + TCP 27777 수신 대기

# Actor 통합 테스트
- test_spawn_and_delete_actor        # 생성 → 존재 확인 → 삭제 → 부재 확인
- test_actor_transform_roundtrip     # 위치 설정 → 읽기 → 값 일치 확인
- test_read_actor_content            # 액터 읽기 → 필드 존재 확인

# ActorComponent 통합 테스트
- test_add_and_remove_component      # 컴포넌트 추가 → 조회 → 삭제 → 조회
- test_read_components_from_actor    # 기본 컴포넌트 존재 확인

# Blueprint 통합 테스트
- test_create_compile_delete_blueprint  # 생성 → 컴파일 → 삭제
- test_read_blueprint_content          # 읽기 → 필드 존재 확인

# BlueprintComponent 통합 테스트
- test_add_and_remove_blueprint_component  # 추가 → 조회 → 삭제
- test_read_components_from_blueprint      # 기본 SceneRoot 존재 확인
```

### 4.4 E2E Tests (`test_e2e.py`)

MCP 클라이언트(FastMCP TestClient)로 stdio transport를 통해 전체 흐름 테스트.

```python
# FastMCP의 TestClient 또는 in-process client 사용
# mcp_server.py의 mcp 인스턴스를 직접 import하여 테스트

- test_tool_list_contains_all_18_tools   # 등록된 tool 목록 확인
- test_actor_crud_e2e                    # Actor 생성→조회→수정→삭제 전체 흐름
- test_component_crud_e2e               # Component 추가→조회→삭제 전체 흐름
- test_blueprint_crud_e2e               # Blueprint 생성→읽기→컴파일→삭제 전체 흐름
```

### 4.5 실행 방법

```bash
# Unit tests (UE 불필요)
cd WN_MCP_WORLD/Python
uv run python -m pytest tests/test_unit_tools.py -v

# Integration tests (UE 실행 필수)
uv run python -m pytest tests/test_integration.py -v -m integration

# E2E tests (UE 실행 필수)
uv run python -m pytest tests/test_e2e.py -v -m e2e

# 전체
uv run python -m pytest tests/ -v
```

### 4.6 pytest 설정

```toml
# pyproject.toml에 추가
[tool.pytest.ini_options]
markers = [
    "integration: requires running UE editor (deselect with '-m not integration')",
    "e2e: end-to-end tests requiring UE editor (deselect with '-m not e2e')",
]
testpaths = ["tests"]
```

## 5. 작업 순서

1. **기존 Tool 수정** — `read_actor_content`, `read_blueprint_content`
2. **Component Tool 6개 추가** — ActorComponent 3 + BlueprintComponent 3
3. **pyproject.toml 업데이트** — pytest 의존성, 마커 설정
4. **Unit Tests** — mock 기반, 모든 tool 커버
5. **Integration Tests** — UE 연결 필요, CRUD 시나리오
6. **E2E Tests** — MCP 클라이언트 전체 흐름
