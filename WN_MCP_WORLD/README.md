# WN_MCP_WORLD

Unreal Engine 5 씬 조작을 위한 MCP(Model Context Protocol) 플러그인.
AI 에이전트(Claude Code, Cursor 등)가 UE 에디터의 액터, 블루프린트, 컴포넌트, 머티리얼을 CRUD 조작할 수 있게 해준다.

## 아키텍처

```
AI Agent (Claude/Cursor)
    │ stdio
    ▼
Python MCP Server (FastMCP)          ← WN_MCP_WORLD/Python/
    │ TCP JSON-RPC 2.0 (port 27777)
    ▼
UE C++ Plugin (CommandGroup)         ← WN_MCP_WORLD/Source/
    │ UE Engine API
    ▼
Unreal Engine Editor
```

- **Python Tool**: `@mcp.tool` 데코레이터로 등록. AI 에이전트가 직접 호출하는 함수.
- **C++ Command**: `FWN_MCP_CommandGroup` 서브클래스에 구현. UE API에 접근하는 함수.
- Python Tool이 TCP를 통해 C++ Command를 호출하여 UE를 조작한다.

## 설치 및 실행

### 사전 요구사항

- Unreal Engine 5 (WN_MCP 플러그인 포함)
- Python 3.11+ (`uv` 패키지 매니저)

### Python MCP Server 설정

```bash
cd WN_MCP_WORLD/Python
uv sync                    # 의존성 설치
uv run python mcp_server.py   # MCP 서버 실행 (stdio transport)
```

### VS Code MCP 설정

`.vscode/mcp.json`:

```json
{
    "servers": {
        "wn-mcp-world": {
            "type": "stdio",
            "command": "uv",
            "args": ["run", "python", "mcp_server.py"],
            "cwd": "${workspaceFolder}/WN_MCP_WORLD/Python"
        }
    }
}
```

### Claude Code MCP 설정

`~/.claude/settings.json`:

```json
{
    "mcpServers": {
        "ue-world": {
            "command": "uv",
            "args": ["run", "python", "mcp_server.py"],
            "cwd": "<프로젝트경로>/WN_MCP_WORLD/Python"
        }
    }
}
```

## 커맨드 목록 (27개)

### Actor (6개) — 레벨 내 액터 조작

| 커맨드 | 설명 |
|--------|------|
| `get_actors_in_level` | 레벨의 모든 액터 목록 조회 |
| `find_actors_by_name` | 이름으로 액터 검색 (부분 일치) |
| `spawn_actor` | 새 액터를 레벨에 스폰 |
| `delete_actor` | 레벨에서 액터 삭제 |
| `set_actor_transform` | 액터의 위치/회전/스케일 변경 |
| `read_actor_content` | 액터의 상세 정보 조회 |

#### `get_actors_in_level`

레벨에 있는 모든 액터를 반환한다.

- 파라미터: 없음
- 응답: `{ count, actors: [{ name, class, location, rotation, scale }] }`

#### `find_actors_by_name`

이름의 일부로 액터를 검색한다.

- 파라미터:
  - `search_text` (str, 필수) — 검색할 텍스트 (대소문자 구분)
- 응답: `{ count, actors: [{ name, class, location, rotation, scale }] }`

#### `spawn_actor`

지정한 클래스의 액터를 레벨에 스폰한다.

- 파라미터:
  - `type` (str, 필수) — 액터 클래스명 (예: `"StaticMeshActor"`, `"PointLight"`, `"CameraActor"`)
  - `name` (str, 필수) — 고유한 액터 이름
  - `location` (list[float], 선택) — `[x, y, z]` 월드 좌표 (기본: `[0, 0, 0]`)
  - `rotation` (list[float], 선택) — `[pitch, yaw, roll]` 도 단위 (기본: `[0, 0, 0]`)
  - `scale` (list[float], 선택) — `[x, y, z]` 스케일 (기본: `[1, 1, 1]`)
- 응답: `{ status: "success" }`

#### `delete_actor`

레벨에서 액터를 삭제한다.

- 파라미터:
  - `name` (str, 필수) — 삭제할 액터의 정확한 이름
- 응답: `{ status: "success" }`

#### `set_actor_transform`

액터의 트랜스폼(위치/회전/스케일)을 변경한다. 제공한 값만 변경되고 나머지는 유지된다.

- 파라미터:
  - `name` (str, 필수) — 액터 이름
  - `location` (list[float], 선택) — `[x, y, z]`
  - `rotation` (list[float], 선택) — `[pitch, yaw, roll]`
  - `scale` (list[float], 선택) — `[x, y, z]`
- 응답: `{ status: "success" }`

#### `read_actor_content`

액터의 이름, 클래스, 트랜스폼 정보를 반환한다.

- 파라미터:
  - `name` (str, 필수) — 액터 이름
- 응답: `{ name, class, location, rotation, scale }`

---

### Actor Component (3개) — 레벨 액터의 컴포넌트 조작

| 커맨드 | 설명 |
|--------|------|
| `add_component_to_actor` | 액터에 컴포넌트 추가 |
| `remove_component_from_actor` | 액터에서 컴포넌트 제거 |
| `read_components_from_actor` | 액터의 컴포넌트 목록 조회 |

#### `add_component_to_actor`

레벨 내 액터에 새 컴포넌트를 추가한다.

- 파라미터:
  - `name` (str, 필수) — 대상 액터 이름
  - `component_class` (str, 필수) — 컴포넌트 클래스명 (예: `"StaticMeshComponent"`, `"PointLightComponent"`)
  - `component_name` (str, 선택) — 컴포넌트 이름 (생략 시 자동 생성)
- 응답: `{ status: "success", component_class, component_name }`

#### `remove_component_from_actor`

액터에서 컴포넌트를 제거한다. 루트 컴포넌트는 제거할 수 없다.

- 파라미터:
  - `name` (str, 필수) — 대상 액터 이름
  - `component_name` (str, 필수) — 제거할 컴포넌트 이름
- 응답: `{ status: "success" }`

#### `read_components_from_actor`

액터에 붙어있는 모든 컴포넌트를 반환한다.

- 파라미터:
  - `name` (str, 필수) — 액터 이름
- 응답: `{ actor_name, count, components: [{ name, class, is_root, relative_location, ... }] }`

---

### Blueprint (6개) — 블루프린트 에셋 관리

| 커맨드 | 설명 |
|--------|------|
| `get_blueprints` | 프로젝트의 블루프린트 목록 조회 |
| `find_blueprints_by_name` | 이름으로 블루프린트 검색 |
| `create_blueprint` | 새 블루프린트 생성 |
| `read_blueprint_content` | 블루프린트 내용 조회 |
| `compile_blueprint` | 블루프린트 컴파일 |
| `delete_blueprint` | 블루프린트 삭제 |

#### `get_blueprints`

프로젝트 내 모든 블루프린트 에셋을 반환한다.

- 파라미터:
  - `search_path` (str, 선택) — 검색 경로 (기본: `"/Game/"`)
- 응답: `{ count, blueprints: [{ name, path, package_path }] }`

#### `find_blueprints_by_name`

이름의 일부로 블루프린트를 검색한다.

- 파라미터:
  - `search_text` (str, 필수) — 검색할 텍스트 (대소문자 구분)
- 응답: `{ count, blueprints: [{ name, path, package_path }] }`

#### `create_blueprint`

새 블루프린트 에셋을 `/Game/Blueprints/` 경로에 생성한다.

- 파라미터:
  - `name` (str, 필수) — 블루프린트 이름
  - `parent_class` (str, 선택) — 부모 클래스명 (기본: `"Actor"`)
- 응답: `{ name, path }`

#### `read_blueprint_content`

블루프린트의 변수, 함수, 이벤트 그래프, 인터페이스 정보를 반환한다.

- 파라미터:
  - `blueprint_path` (str, 필수) — 에셋 경로 (예: `"/Game/Blueprints/MyBP"`)
  - `include_event_graph` (bool, 선택) — 이벤트 그래프 포함 (기본: true)
  - `include_functions` (bool, 선택) — 함수 목록 포함 (기본: true)
  - `include_variables` (bool, 선택) — 변수 목록 포함 (기본: true)
  - `include_interfaces` (bool, 선택) — 인터페이스 포함 (기본: true)
- 응답: `{ blueprint_name, parent_class, variables, functions, event_graph, interfaces }`

#### `compile_blueprint`

블루프린트를 컴파일하여 GeneratedClass를 업데이트한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
- 응답: `{ name, compiled: true }`

#### `delete_blueprint`

블루프린트 에셋을 프로젝트에서 삭제한다.

- 파라미터:
  - `blueprint_path` (str, 필수) — 에셋 경로 (예: `"/Game/Blueprints/MyBP"`)
  - `force` (bool, 선택) — 다른 에셋이 참조 중이어도 강제 삭제 (기본: false)
- 응답: `{ status: "success" }`

---

### Blueprint Component (3개) — 블루프린트 SCS 컴포넌트 조작

| 커맨드 | 설명 |
|--------|------|
| `add_component_to_blueprint` | 블루프린트에 컴포넌트 추가 |
| `remove_component_from_blueprint` | 블루프린트에서 컴포넌트 제거 |
| `read_components_from_blueprint` | 블루프린트의 컴포넌트 목록 조회 |

#### `add_component_to_blueprint`

블루프린트의 컴포넌트 계층(SCS)에 새 컴포넌트를 추가한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_class` (str, 필수) — 컴포넌트 클래스명
  - `component_name` (str, 선택) — 컴포넌트 이름 (생략 시 자동)
  - `parent_component` (str, 선택) — 부모 컴포넌트 이름 (생략 시 루트에 추가)
- 응답: `{ status: "success" }`

#### `remove_component_from_blueprint`

블루프린트에서 컴포넌트를 제거한다. 자식은 부모로 재배치된다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_name` (str, 필수) — 제거할 컴포넌트 이름
- 응답: `{ status: "success" }`

#### `read_components_from_blueprint`

블루프린트의 SCS 컴포넌트 계층을 반환한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
- 응답: `{ blueprint_name, count, components: [{ name, class, is_root, parent }] }`

---

### Property (2개) — 블루프린트 컴포넌트 속성 설정

| 커맨드 | 설명 |
|--------|------|
| `set_static_mesh_properties` | StaticMeshComponent에 메시/머티리얼 설정 |
| `set_physics_properties` | PrimitiveComponent에 물리 속성 설정 |

#### `set_static_mesh_properties`

블루프린트 내 StaticMeshComponent에 스태틱 메시와 머티리얼을 설정한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_name` (str, 필수) — 대상 StaticMeshComponent 이름
  - `static_mesh` (str, 선택) — 메시 에셋 경로 (예: `"/Engine/BasicShapes/Cube.Cube"`)
  - `material` (str, 선택) — 머티리얼 에셋 경로
- 응답: `{ status: "success" }`

#### `set_physics_properties`

블루프린트 내 PrimitiveComponent의 물리 속성을 설정한다. 제공한 값만 변경된다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_name` (str, 필수) — 대상 PrimitiveComponent 이름
  - `simulate_physics` (bool, 선택) — 물리 시뮬레이션 활성화
  - `mass` (float, 선택) — 질량 (kg)
  - `linear_damping` (float, 선택) — 선형 감쇠
  - `angular_damping` (float, 선택) — 각도 감쇠
- 응답: `{ status: "success" }`

---

### Blueprint Spawn (1개) — 블루프린트 인스턴스 스폰

| 커맨드 | 설명 |
|--------|------|
| `spawn_blueprint_actor` | 블루프린트를 레벨에 스폰 |

#### `spawn_blueprint_actor`

블루프린트의 인스턴스를 레벨에 스폰한다. 블루프린트는 사전에 컴파일되어 있어야 한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `name` (str, 필수) — 스폰할 액터의 고유 이름
  - `location` (list[float], 선택) — `[x, y, z]` (기본: `[0, 0, 0]`)
  - `rotation` (list[float], 선택) — `[pitch, yaw, roll]` (기본: `[0, 0, 0]`)
  - `scale` (list[float], 선택) — `[x, y, z]` (기본: `[1, 1, 1]`)
- 응답: `{ status: "success" }`

---

### Material (6개) — 머티리얼 조회 및 적용

| 커맨드 | 설명 |
|--------|------|
| `get_available_materials` | 프로젝트의 머티리얼 목록 조회 |
| `apply_material_to_actor` | 레벨 액터에 머티리얼 적용 |
| `apply_material_to_blueprint` | 블루프린트 컴포넌트에 머티리얼 적용 |
| `get_actor_material_info` | 액터의 머티리얼 슬롯 정보 조회 |
| `get_blueprint_material_info` | 블루프린트 컴포넌트의 머티리얼 슬롯 정보 조회 |
| `set_mesh_material_color` | 블루프린트 컴포넌트의 머티리얼 색상 변경 |

#### `get_available_materials`

프로젝트에서 사용 가능한 머티리얼 에셋 목록을 반환한다.

- 파라미터:
  - `search_path` (str, 선택) — 검색 경로 (기본: `"/Game/"`)
  - `include_engine_materials` (bool, 선택) — 엔진 내장 머티리얼 포함 (기본: true)
- 응답: `{ count, materials: [{ name, path, package, class }] }`

#### `apply_material_to_actor`

레벨 내 액터의 StaticMeshComponent에 머티리얼을 적용한다.

- 파라미터:
  - `actor_name` (str, 필수) — 대상 액터 이름
  - `material_path` (str, 필수) — 머티리얼 에셋 경로
  - `material_slot` (int, 선택) — 머티리얼 슬롯 인덱스 (기본: 0)
- 응답: `{ status: "success" }`

#### `apply_material_to_blueprint`

블루프린트 내 PrimitiveComponent에 머티리얼을 적용한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_name` (str, 필수) — 대상 PrimitiveComponent 이름
  - `material_path` (str, 필수) — 머티리얼 에셋 경로
  - `material_slot` (int, 선택) — 머티리얼 슬롯 인덱스 (기본: 0)
- 응답: `{ status: "success" }`

#### `get_actor_material_info`

액터의 메시 컴포넌트에 적용된 머티리얼 정보를 반환한다.

- 파라미터:
  - `actor_name` (str, 필수) — 대상 액터 이름
- 응답: `{ actor_name, total_slots, material_slots: [{ slot_index, material_name, material_path, material_class }] }`

#### `get_blueprint_material_info`

블루프린트 내 StaticMeshComponent의 머티리얼 슬롯 정보를 반환한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_name` (str, 필수) — 대상 StaticMeshComponent 이름
- 응답: `{ blueprint_name, component_name, has_static_mesh, material_slots: [{ slot_index, material_name, material_path }] }`

#### `set_mesh_material_color`

블루프린트 컴포넌트의 머티리얼에 색상 파라미터를 설정한다. Dynamic Material Instance를 생성하여 적용한다.

- 파라미터:
  - `blueprint_name` (str, 필수) — 블루프린트 이름 또는 경로
  - `component_name` (str, 필수) — 대상 PrimitiveComponent 이름
  - `color` (list[float], 필수) — `[R, G, B]` 또는 `[R, G, B, A]` (0.0~1.0)
  - `material_slot` (int, 선택) — 머티리얼 슬롯 인덱스 (기본: 0)
  - `parameter_name` (str, 선택) — 셰이더 파라미터 이름 (기본: `"BaseColor"`)
  - `material_path` (str, 선택) — 기본 머티리얼 경로
- 응답: `{ status: "success" }`

---

## 파일 구조

```
WN_MCP_WORLD/
├── Source/
│   ├── WN_MCP_WORLD/                          # Runtime 모듈
│   │   └── Private/Commands/
│   │       ├── WN_MCP_CommandGroup_Actor.h/.cpp           # Actor 6개
│   │       └── WN_MCP_CommandGroup_ActorComponent.h/.cpp  # ActorComponent 3개
│   └── WN_MCP_WORLD_Editor/                   # Editor 모듈
│       └── Private/
│           ├── WN_MCP_BlueprintUtils.h/.cpp               # 공유 유틸리티
│           └── Commands/
│               ├── WN_MCP_CommandGroup_Blueprint.h/.cpp          # Blueprint 6개
│               ├── WN_MCP_CommandGroup_BlueprintComponent.h/.cpp # BlueprintComponent 3개
│               ├── WN_MCP_CommandGroup_Property.h/.cpp           # Property 2개
│               ├── WN_MCP_CommandGroup_BlueprintSpawn.h/.cpp     # BlueprintSpawn 1개
│               └── WN_MCP_CommandGroup_Material.h/.cpp           # Material 6개
├── Python/
│   ├── mcp_server.py                          # FastMCP 서버 진입점
│   ├── pyproject.toml                         # Python 프로젝트 설정
│   ├── tools/
│   │   ├── __init__.py                        # 전체 Tool 등록
│   │   ├── ue_connection.py                   # UE TCP 연결 유틸리티
│   │   ├── actor_tools.py                     # Actor Tool 6개
│   │   ├── actor_component_tools.py           # ActorComponent Tool 3개
│   │   ├── blueprint_tools.py                 # Blueprint Tool 6개
│   │   ├── blueprint_component_tools.py       # BlueprintComponent Tool 3개
│   │   ├── property_tools.py                  # Property Tool 2개
│   │   ├── blueprint_spawn_tools.py           # BlueprintSpawn Tool 1개
│   │   └── material_tools.py                  # Material Tool 6개
│   └── tests/
│       ├── conftest.py                        # 공통 fixture + call_tool 헬퍼
│       ├── test_unit_tools.py                 # Unit 테스트 (UE Mock, 59개)
│       ├── test_integration.py                # 통합 테스트 (UE 필요, 42개)
│       └── test_e2e.py                        # E2E 테스트 (UE 필요, 7개)
└── docs/
    └── python-tools-and-tests/
        └── design.md                          # 설계문서
```

## 테스트

### 실행 방법

```bash
cd WN_MCP_WORLD/Python

# Unit 테스트 (UE 불필요)
uv run python -m pytest tests/test_unit_tools.py -v

# 통합 테스트 (UE 에디터 실행 필수)
uv run python -m pytest tests/test_integration.py -v

# E2E 테스트 (UE 에디터 실행 필수)
uv run python -m pytest tests/test_e2e.py -v

# 전체
uv run python -m pytest tests/ -v

# 커버리지 확인
uv run python -m pytest tests/test_unit_tools.py --cov=tools --cov-report=term-missing -q
```

### 테스트 현황

| 구분 | 테스트 수 | UE 필요 | 설명 |
|------|----------|---------|------|
| Unit | 59개 | 아니오 | Tool 파라미터 전달 + 응답 포맷 검증 (UE Mock) |
| Integration | 42개 | 예 | 실제 UE 에디터에서 CRUD 시나리오 검증 |
| E2E | 7개 | 예 | MCP Client를 통한 전체 프로토콜 흐름 검증 |
| **합계** | **108개** | | |

### 커버리지

- Tool 모듈 전체: **100%** (ue_connection.py 제외)
- ue_connection.py: 20% (TCP 소켓 코드는 Integration/E2E에서 검증)
- 전체: **86%**

## 사용 예시

AI 에이전트가 UE에서 빨간 큐브를 만드는 흐름:

```
1. create_blueprint(name="RedCube")
2. add_component_to_blueprint(blueprint_name="RedCube", component_class="StaticMeshComponent", component_name="Mesh")
3. set_static_mesh_properties(blueprint_name="RedCube", component_name="Mesh", static_mesh="/Engine/BasicShapes/Cube.Cube")
4. set_mesh_material_color(blueprint_name="RedCube", component_name="Mesh", color=[1.0, 0.0, 0.0])
5. compile_blueprint(blueprint_name="RedCube")
6. spawn_blueprint_actor(blueprint_name="RedCube", name="RedCube_1", location=[0, 0, 100])
```
