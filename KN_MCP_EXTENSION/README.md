# KN_MCP_EXTENSION

Unreal Engine 5 씬 조작을 위한 MCP(Model Context Protocol) 플러그인.
AI 에이전트(Claude Code, Cursor 등)가 UE 에디터의 액터, 블루프린트, 컴포넌트, 머티리얼을 CRUD 조작할 수 있게 해준다.

## 아키텍처

```
AI Agent (Claude/Cursor)
    │ stdio
    ▼
Python MCP Server (FastMCP)              ← KN_MCP/Python/
    │ 동적 Import (AddUserToolDirectories)
    ▼
WORLD Python Tools                  ← KN_MCP_EXTENSION/Python/tools/
    │ ue_connection (자체 TCP 소켓)
    │ TCP JSON-RPC 2.0 (port 27777~27787)
    ▼
UE C++ Plugin (CommandGroup)        ← KN_MCP_EXTENSION/Source/
    │ UE Engine API
    ▼
Unreal Engine Editor
```

- **Python Tool**: `@mcp.tool` 데코레이터로 등록. AI 에이전트가 직접 호출하는 함수.
- **C++ Command**: `FKN_MCP_CommandGroup` 서브클래스에 구현. UE API에 접근하는 함수.
- Python Tool이 `ue_connection.execute()` → 자체 TCP 소켓 → JSON-RPC 2.0을 통해 C++ Command를 호출하여 UE를 조작한다.
- Python MCP Server는 서버 시작(lifespan) 시 UE 연결 + Tool 등록을 `yield` 전에 완료하여, MCP 클라이언트가 즉시 전체 Tool 목록을 받을 수 있다.
- UE 재연결 시에는 `refresh_tools` Tool로 `tools/list_changed` 알림을 보내 클라이언트 목록을 갱신한다.

## 커맨드 (38개)

> 상세 파라미터/응답은 [docs/commands.md](docs/commands.md) 참조

| 그룹 | 수 | CRUD | 커맨드 |
|------|---|------|--------|
| Actor | 6 | CRUD | `get_actors_in_level`, `find_actors_by_name`, `spawn_actor`, `delete_actor`, `set_actor_transform`, `read_actor_content` |
| ActorComponent | 3 | CRD | `add_component_to_actor`, `read_components_from_actor`, `remove_component_from_actor` |
| Blueprint | 7 | CRUD | `get_blueprints`, `find_blueprints_by_name`, `create_blueprint`, `read_blueprint_content`, `compile_blueprint`, `delete_blueprint`, `spawn_blueprint_actor` |
| BlueprintComponent | 3 | CRD | `add_component_to_blueprint`, `read_components_from_blueprint`, `remove_component_from_blueprint` |
| Property | 2 | U | `set_static_mesh_properties`, `set_physics_properties` |
| Material | 6 | RU | `get_available_materials`, `get_actor_material_info`, `get_blueprint_material_info`, `apply_material_to_actor`, `apply_material_to_blueprint`, `set_mesh_material_color` |
| StaticMesh | 2 | R | `get_static_meshes`, `find_static_meshes_by_name` |
| BlueprintVariable | 2 | CD | `add_variable_to_blueprint`, `remove_variable_from_blueprint` |
| BlueprintGraph | 7 | CRUD | `read_blueprint_graph`, `add_event_node`, `add_function_call_node`, `add_variable_get_node`, `add_variable_set_node`, `connect_nodes`, `disconnect_nodes` |

## 파일 구조

```
KN_MCP_EXTENSION/
├── Source/
│   ├── KN_MCP_EXTENSION/                          # Runtime 모듈
│   │   ├── Public/
│   │   │   └── KN_MCP_ActorUtils.h                        # 공유 유틸리티 (FindActorByName)
│   │   └── Private/
│   │       ├── KN_MCP_ActorUtils.cpp                      # FindActorByName 구현
│   │       └── Commands/
│   │           ├── KN_MCP_CommandGroup_Actor.h/.cpp           # Actor CRUD 6개
│   │           └── KN_MCP_CommandGroup_ActorComponent.h/.cpp  # ActorComponent CRD 3개
│   └── KN_MCP_EXTENSION_Editor/                   # Editor 모듈
│       └── Private/
│           ├── KN_MCP_BlueprintUtils.h/.cpp               # 공유 유틸리티
│           └── Commands/
│               ├── KN_MCP_CommandGroup_Blueprint.h/.cpp          # Blueprint CRUD 7개
│               ├── KN_MCP_CommandGroup_BlueprintComponent.h/.cpp # BlueprintComponent CRD 3개
│               ├── KN_MCP_CommandGroup_Property.h/.cpp           # Property U 2개
│               ├── KN_MCP_CommandGroup_Material.h/.cpp           # Material RU 6개
│               ├── KN_MCP_CommandGroup_StaticMesh.h/.cpp         # StaticMesh R 2개
│               ├── KN_MCP_CommandGroup_BlueprintVariable.h/.cpp  # BlueprintVariable CD 2개
│               └── KN_MCP_CommandGroup_BlueprintGraph.h/.cpp     # BlueprintGraph CRUD 7개
├── Python/
│   ├── pyproject.toml                         # Python 프로젝트 설정
│   ├── tools/
│   │   ├── __init__.py                        # 전체 Tool 등록
│   │   ├── ue_connection.py                   # UE TCP 연결 유틸리티
│   │   ├── actor_tools.py                     # Actor Tool 6개
│   │   ├── actor_component_tools.py           # ActorComponent Tool 3개
│   │   ├── blueprint_tools.py                 # Blueprint Tool 7개
│   │   ├── blueprint_component_tools.py       # BlueprintComponent Tool 3개
│   │   ├── property_tools.py                  # Property Tool 2개
│   │   ├── material_tools.py                  # Material Tool 6개
│   │   ├── static_mesh_tools.py               # StaticMesh Tool 2개
│   │   ├── blueprint_variable_tools.py        # BlueprintVariable Tool 2개
│   │   └── blueprint_graph_tools.py           # BlueprintGraph Tool 7개
│   └── tests/
│       ├── conftest.py                        # 공통 fixture + call_tool 헬퍼
│       ├── test_unit_tools.py                 # Unit 테스트 (UE Mock, 103개)
│       ├── test_integration.py                # 통합 테스트 (UE 필요, 111개)
│       └── test_e2e.py                        # E2E 테스트 (UE 필요, 10개)
└── docs/
    ├── commands.md                            # 커맨드 레퍼런스 (상세)
    └── python-tools-and-tests/
        └── design.md                          # 설계문서
```

## 테스트

### 실행 방법

```bash
cd KN_MCP_EXTENSION/Python

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
| Unit | 85개 | 아니오 | Tool 파라미터 전달 + 응답 포맷 검증 (UE Mock) |
| Integration | 111개 | 예 | 실제 UE 에디터에서 CRUD 시나리오 검증 |
| E2E | 10개 | 예 | MCP Client를 통한 전체 프로토콜 흐름 검증 |
| **합계** | **206개** | | |

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
