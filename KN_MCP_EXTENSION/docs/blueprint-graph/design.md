# Blueprint Graph 설계문서

## 1. 목적

AI 에이전트가 Blueprint의 비주얼 스크립팅(EventGraph)을 조작할 수 있도록
변수/노드/연결 CRUD 커맨드를 구현한다.

## 2. 커맨드 (9개, 2개 CommandGroup)

### BlueprintVariable (CD, 2개)

| 커맨드 | CRUD | 설명 |
|--------|------|------|
| `add_variable_to_blueprint` | C | BP에 변수 추가 |
| `remove_variable_from_blueprint` | D | BP에서 변수 제거 |

### BlueprintGraph (CRD, 7개)

| 커맨드 | CRUD | 설명 |
|--------|------|------|
| `read_blueprint_graph` | R | EventGraph 상세 조회 (노드, 핀, 연결) |
| `add_event_node` | C | 이벤트 노드 추가 (BeginPlay 등) |
| `add_function_call_node` | C | 함수 호출 노드 추가 (PrintString 등) |
| `add_variable_get_node` | C | 변수 Getter 노드 추가 |
| `add_variable_set_node` | C | 변수 Setter 노드 추가 |
| `connect_nodes` | C | 두 핀 연결 |
| `disconnect_nodes` | D | 핀 연결 해제 |

## 3. 아키텍처

### 기존 read_blueprint_content와의 관계

`read_blueprint_content`는 노드의 이름/클래스만 반환한다.
`read_blueprint_graph`는 노드 GUID, 핀 목록, 핀 간 연결 정보를 반환하여
`connect_nodes`에서 참조할 수 있게 한다.

### 노드 식별

모든 노드는 `NodeGuid` (FGuid)로 식별한다.
노드 생성 커맨드는 `node_id` (GUID 문자열)를 반환하며,
`connect_nodes`/`disconnect_nodes`에서 이 값을 사용한다.

### 핀 식별

핀은 `PinName` (문자열)으로 식별한다.

| 핀 이름 | 설명 |
|---------|------|
| `execute` | 실행 입력 (Exec In) |
| `then` | 실행 출력 (Exec Out) |
| `ReturnValue` | 반환값 |
| `{파라미터명}` | 함수 파라미터 (예: `InString`, `Duration`) |
| `{변수명}` | 변수 Get/Set 핀 |

## 4. 커맨드 상세

### 4.1 `add_variable_to_blueprint`

BP에 멤버 변수를 추가한다.

**파라미터:**

| 이름 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `blueprint_name` | str | O | | BP 이름 |
| `variable_name` | str | O | | 변수 이름 |
| `variable_type` | str | O | | 타입 (아래 표 참조) |
| `default_value` | str | X | | 기본값 (문자열) |
| `is_instance_editable` | bool | X | false | Details 패널에 노출 |

**지원 타입:**

| variable_type | UE 타입 | 예시 default_value |
|---------------|---------|-------------------|
| `Bool` | Boolean | `"true"` |
| `Int` | Integer | `"42"` |
| `Float` | Real (Double) | `"3.14"` |
| `String` | String | `"Hello"` |
| `Vector` | FVector | `"1.0,2.0,3.0"` |
| `Rotator` | FRotator | `"0.0,90.0,0.0"` |
| `Transform` | FTransform | |

**응답:** `{ status, variable_name, variable_type }`

**UE API:**
```cpp
FEdGraphPinType PinType;
PinType.PinCategory = UEdGraphSchema_K2::PC_Real; // 타입별 매핑
FBlueprintEditorUtils::AddMemberVariable(Blueprint, VarName, PinType);
```

### 4.2 `remove_variable_from_blueprint`

BP에서 변수를 제거한다.

**파라미터:**

| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `blueprint_name` | str | O | BP 이름 |
| `variable_name` | str | O | 제거할 변수 이름 |

**응답:** `{ status, variable_name }`

**UE API:**
```cpp
FBlueprintEditorUtils::RemoveMemberVariable(Blueprint, VarName);
```

### 4.3 `read_blueprint_graph`

EventGraph의 노드, 핀, 연결을 상세 조회한다.

**파라미터:**

| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `blueprint_name` | str | O | BP 이름 |

**응답:**
```json
{
  "blueprint_name": "MyBP",
  "graph_name": "EventGraph",
  "node_count": 2,
  "nodes": [
    {
      "node_id": "A1B2C3D4...",
      "node_class": "K2Node_Event",
      "node_title": "Event BeginPlay",
      "position": [0, 0],
      "pins": [
        {
          "pin_name": "then",
          "pin_type": "exec",
          "direction": "output",
          "connected_to": [
            { "node_id": "E5F6G7H8...", "pin_name": "execute" }
          ]
        }
      ]
    }
  ]
}
```

### 4.4 `add_event_node`

EventGraph에 이벤트 노드를 추가한다.

**파라미터:**

| 이름 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `blueprint_name` | str | O | | BP 이름 |
| `event_type` | str | O | | 이벤트 타입 (아래 표) |
| `node_position` | list[int] | X | [0, 0] | 그래프 내 [X, Y] 위치 |

**지원 이벤트:**

| event_type | UE 내부 이름 | 설명 |
|------------|-------------|------|
| `BeginPlay` | ReceiveBeginPlay | 플레이 시작 시 |
| `Tick` | ReceiveTick | 매 프레임 |
| `EndPlay` | ReceiveEndPlay | 플레이 종료 시 |
| `ActorBeginOverlap` | ReceiveActorBeginOverlap | 오버랩 시작 |
| `ActorEndOverlap` | ReceiveActorEndOverlap | 오버랩 종료 |
| `AnyDamage` | ReceiveAnyDamage | 데미지 수신 |
| `Hit` | ReceiveHit | 충돌 |

**응답:** `{ status, node_id, event_type, pins: [{ pin_name, pin_type, direction }] }`

**UE API:**
```cpp
UK2Node_Event* EventNode = NewObject<UK2Node_Event>(EventGraph);
EventNode->EventReference.SetExternalMember(
    FName("ReceiveBeginPlay"), AActor::StaticClass());
EventNode->bOverrideFunction = true;
EventNode->AllocateDefaultPins();
EventGraph->AddNode(EventNode, false, false);
```

### 4.5 `add_function_call_node`

EventGraph에 함수 호출 노드를 추가한다.

**파라미터:**

| 이름 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `blueprint_name` | str | O | | BP 이름 |
| `function_name` | str | O | | 함수명 (예: `PrintString`) |
| `target_class` | str | X | (자동 검색) | 함수 소유 클래스 (예: `KismetSystemLibrary`) |
| `node_position` | list[int] | X | [0, 0] | [X, Y] 위치 |

`target_class` 생략 시 다음 순서로 검색:
1. BP의 부모 클래스 계층
2. `UKismetSystemLibrary`
3. `UKismetMathLibrary`
4. `UGameplayStatics`

**응답:** `{ status, node_id, function_name, pins: [{ pin_name, pin_type, direction }] }`

**UE API:**
```cpp
UK2Node_CallFunction* CallNode = NewObject<UK2Node_CallFunction>(EventGraph);
CallNode->FunctionReference.SetExternalMember(
    FName("PrintString"), UKismetSystemLibrary::StaticClass());
CallNode->AllocateDefaultPins();
EventGraph->AddNode(CallNode, false, false);
```

### 4.6 `add_variable_get_node`

변수의 Getter 노드를 EventGraph에 추가한다.

**파라미터:**

| 이름 | 타입 | 필수 | 기본값 | 설명 |
|------|------|------|--------|------|
| `blueprint_name` | str | O | | BP 이름 |
| `variable_name` | str | O | | BP에 존재하는 변수 이름 |
| `node_position` | list[int] | X | [0, 0] | [X, Y] 위치 |

**응답:** `{ status, node_id, variable_name, pins }`

**UE API:**
```cpp
UK2Node_VariableGet* GetNode = NewObject<UK2Node_VariableGet>(EventGraph);
GetNode->VariableReference.SetSelfMember(FName(*VariableName));
GetNode->AllocateDefaultPins();
EventGraph->AddNode(GetNode, false, false);
```

### 4.7 `add_variable_set_node`

변수의 Setter 노드를 EventGraph에 추가한다.

**파라미터:** `add_variable_get_node`와 동일

**응답:** `{ status, node_id, variable_name, pins }`

**UE API:**
```cpp
UK2Node_VariableSet* SetNode = NewObject<UK2Node_VariableSet>(EventGraph);
SetNode->VariableReference.SetSelfMember(FName(*VariableName));
SetNode->AllocateDefaultPins();
EventGraph->AddNode(SetNode, false, false);
```

### 4.8 `connect_nodes`

두 노드의 핀을 연결한다.

**파라미터:**

| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `blueprint_name` | str | O | BP 이름 |
| `source_node_id` | str | O | 출력 핀이 있는 노드 GUID |
| `source_pin_name` | str | O | 출력 핀 이름 |
| `target_node_id` | str | O | 입력 핀이 있는 노드 GUID |
| `target_pin_name` | str | O | 입력 핀 이름 |

**응답:** `{ status }`

**UE API:**
```cpp
const UEdGraphSchema_K2* Schema = GetDefault<UEdGraphSchema_K2>();
Schema->TryCreateConnection(SourcePin, TargetPin);
```

### 4.9 `disconnect_nodes`

노드의 특정 핀에서 모든 연결을 해제한다.

**파라미터:**

| 이름 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `blueprint_name` | str | O | BP 이름 |
| `node_id` | str | O | 노드 GUID |
| `pin_name` | str | O | 연결 해제할 핀 이름 |

**응답:** `{ status, disconnected_count }`

**UE API:**
```cpp
Pin->BreakAllPinLinks();
```

## 5. 파일 구조

### C++ (Editor 모듈)

```
KN_MCP_EXTENSION_Editor/Private/Commands/
├── KN_MCP_CommandGroup_BlueprintVariable.h/.cpp  # 변수 CD 2개
└── KN_MCP_CommandGroup_BlueprintGraph.h/.cpp     # 그래프 CRD 7개
```

### Python

```
tools/
├── blueprint_variable_tools.py   # 변수 Tool 2개
└── blueprint_graph_tools.py      # 그래프 Tool 7개
```

### 테스트

```
tests/
├── test_unit_tools.py   # +18개 예상 (9커맨드 × 2 평균)
└── test_e2e.py          # +1~2개 (그래프 라이프사이클)
```

## 6. 구현 순서

| Phase | 커맨드 | 이유 |
|-------|--------|------|
| 1 | `add_variable_to_blueprint`, `remove_variable_from_blueprint` | 독립적, 단순 |
| 2 | `read_blueprint_graph` | Phase 3에서 핀/노드 확인에 필요 |
| 3 | `add_event_node`, `add_function_call_node`, `add_variable_get_node`, `add_variable_set_node` | 노드 생성 |
| 4 | `connect_nodes`, `disconnect_nodes` | 노드 간 연결 |

## 7. AI 사용 시나리오

### "BeginPlay에서 HP 변수를 출력"

```
1. add_variable_to_blueprint(blueprint_name="MyBP", variable_name="HP", variable_type="Float", default_value="100.0")
2. add_event_node(blueprint_name="MyBP", event_type="BeginPlay")
   → node_id: "AAA..."
3. add_variable_get_node(blueprint_name="MyBP", variable_name="HP")
   → node_id: "BBB..."
4. add_function_call_node(blueprint_name="MyBP", function_name="PrintString")
   → node_id: "CCC..."
5. connect_nodes(blueprint_name="MyBP", source_node_id="AAA...", source_pin_name="then", target_node_id="CCC...", target_pin_name="execute")
6. connect_nodes(blueprint_name="MyBP", source_node_id="BBB...", source_pin_name="HP", target_node_id="CCC...", target_pin_name="InString")
7. compile_blueprint(blueprint_name="MyBP")
```

## 8. 의사결정 기록

| 결정 | 근거 |
|------|------|
| 2 CommandGroup으로 분리 | Variable(2)과 Graph(7)는 UE API 계층이 다름 |
| NodeGuid로 노드 식별 | UE의 고유 식별자, 문자열 변환 용이 |
| PinName으로 핀 식별 | UE 표준, 각 핀이 고유한 이름 보유 |
| event_type에 친숙한 이름 사용 | "BeginPlay"가 "ReceiveBeginPlay"보다 AI가 이해하기 쉬움 |
| function의 target_class 자동 검색 | AI가 클래스 계층을 몰라도 PrintString 같은 함수를 바로 사용 |
| read_blueprint_graph 별도 추가 | 기존 read_blueprint_content 수정 불가 (규칙: 기존 파일 수정 금지) |
| Phase별 구현 | 의존성 순서대로 — 변수 → 읽기 → 노드 → 연결 |
