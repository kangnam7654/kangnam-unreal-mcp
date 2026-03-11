# WN_MCP_WORLD 코드 컨벤션 리팩터링 설계문서

## 목적

WN_MCP(레퍼런스)와 WN_MCP_WORLD(구현) 사이의 코드 컨벤션 불일치를 해소하고,
WN_MCP_WORLD 내부 9개 CommandGroup 파일 간의 일관성을 확보한다.

**범위**: 리팩터링 전용. 기능 변경 없음. 모든 38개 커맨드의 동작은 동일하게 유지.

---

## 아키텍처

### 변경 전

```
WN_MCP_WORLD/Source/WN_MCP_WORLD/Private/Commands/
  Actor.cpp         ← ActorToJsonValue 클래스 멤버, inline actor 찾기 루프
  ActorComponent.cpp ← inline actor 찾기 루프 3곳

WN_MCP_WORLD/Source/WN_MCP_WORLD_Editor/Private/
  WN_MCP_BlueprintUtils.h/.cpp  ← FindBlueprintByName (유일한 공유 유틸리티)
```

### 변경 후

```
WN_MCP_WORLD/Source/WN_MCP_WORLD/
  Public/WN_MCP_ActorUtils.h     ← FindActorByName (공유 유틸리티, WN_MCP_WORLD_API export)
  Private/WN_MCP_ActorUtils.cpp  ← FindActorByName 구현
  Private/Commands/
    Actor.cpp         ← ActorToJsonValue 파일 스코프 static, FindActorByName 사용
    ActorComponent.cpp ← FindActorByName 사용

WN_MCP_WORLD/Source/WN_MCP_WORLD_Editor/Private/
  WN_MCP_BlueprintUtils.h/.cpp  ← FindBlueprintByName (기존)
```

---

## 변경 항목

### A. 구조적 변경 (2개)

#### A1. FindActorByName 유틸리티 추출

**문제**: "이름으로 액터 찾기" 패턴이 Actor.cpp(2곳) + ActorComponent.cpp(3곳) = 총 5곳에서 8~10줄 복사-붙여넣기로 반복.

**해결**: `FWN_MCP_BlueprintUtils::FindBlueprintByName`과 동일한 패턴으로 `FWN_MCP_ActorUtils::FindActorByName` 추출.

```cpp
// WN_MCP_ActorUtils.h
#pragma once

class AActor;

//-----------------------------------------------------------------------------
// FWN_MCP_ActorUtils
//-----------------------------------------------------------------------------

/// Shared utilities for Actor commands.
class WN_MCP_WORLD_API FWN_MCP_ActorUtils
{
public:

	/// Find an actor in the current world by exact name.
	/// @param InActorName exact name of the actor.
	/// @return the actor, or nullptr if not found.
	static AActor* FindActorByName(const FString& InActorName);
};
```

**배치**: Runtime 모듈 (`WN_MCP_WORLD/Public/`) — Actor, ActorComponent, Material(Editor) 모두 사용하므로 DLL export 필요.

#### A2. Helper 배치 패턴 통일

**문제**: 3가지 패턴 혼재
- Actor.cpp: 클래스 멤버 (`.h`에 선언)
- BlueprintGraph.cpp: 파일 스코프 static
- 나머지: helper 없음

**결정**: 파일 스코프 static 패턴으로 통일.
- `.h` 파일을 깨끗하게 유지 (템플릿과 일치)
- helper가 해당 `.cpp`에서만 사용됨
- Actor.cpp의 `ActorToJsonValue`를 클래스 멤버 → 파일 스코프 static으로 변경
- Actor.h에서 private 멤버 선언 + forward declaration 제거

### B. 코드 컨벤션 통일 (5개)

#### B1. Destructor 빈 줄 제거

**컨벤션**: Constructor는 빈 줄 있음, Destructor는 빈 줄 없음.

```cpp
// Constructor — 빈 줄 있음
FWN_MCP_CommandGroup_XXX::FWN_MCP_CommandGroup_XXX()
{

}

// Destructor — 빈 줄 없음
FWN_MCP_CommandGroup_XXX::~FWN_MCP_CommandGroup_XXX()
{
}
```

**수정 파일**: BlueprintComponent, BlueprintVariable, BlueprintGraph, Blueprint, Property, Material (6개 파일)
**이미 올바른 파일**: Actor, ActorComponent, StaticMesh

#### B2. 인라인 주석 대문자

**컨벤션**: 인라인 주석은 대문자로 시작.

**수정 파일**: Actor.cpp (9곳)
- `// optional transform parameters` → `// Optional transform parameters`
- `// check for duplicate name` → `// Check for duplicate name`
- 등

#### B3. OnExecute 내 커맨드 구분선 추가

**컨벤션**: 각 커맨드 블록 앞에 72-dash 구분선.

```cpp
TSharedPtr<FJsonObject> OnExecute(...) const
{
	//-------------------------------------------------------------------------
	// command_name_here
	//-------------------------------------------------------------------------

	if (InCommandName == FString(TEXT("command_name_here")))
	{
		...
	}
```

**수정 파일**: Actor.cpp, ActorComponent.cpp, Blueprint.cpp, BlueprintComponent.cpp (4개)
**이미 올바른 파일**: BlueprintVariable, BlueprintGraph, Property, Material, StaticMesh

#### B4. 자명한 주석 제거

**제거 대상**:
- `// Get required parameters` — TryGetStringField 호출 앞에 반복 (자명)
- `// Return result` — WN_RETURN_COMMAND_RESPONSE 앞에 반복 (자명)

**수정 파일**: ActorComponent.cpp (5곳), BlueprintVariable.cpp (2곳)

#### B5. read_actor_content 커맨드 구현

**문제**: Python tool, docs, tests는 존재하지만 C++ Command가 누락.

**해결**: Actor.cpp에 `read_actor_content` 커맨드 추가.
- OnRegisterCommands에 등록
- OnExecute에 구현 (ActorToJsonObject helper 활용)
- param: `name` (actor name)
- 응답: actor의 상세 정보 JSON (name, class, location, rotation, scale)

---

## 수정 파일 요약

### 신규 파일

| 파일 | 내용 |
|------|------|
| `WN_MCP_WORLD/Public/WN_MCP_ActorUtils.h` | FindActorByName 선언 (WN_MCP_WORLD_API export) |
| `WN_MCP_WORLD/Private/WN_MCP_ActorUtils.cpp` | FindActorByName 구현 |

### 수정 파일 (C++)

| 파일 | 적용 항목 |
|------|-----------|
| `Actor.h` | A2: private 멤버 + forward decl 제거 |
| `Actor.cpp` | A1(FindActorByName), A2(static helper), B2(주석 대문자), B3(구분선), B5(read_actor_content) |
| `ActorComponent.cpp` | A1(FindActorByName), B1(destructor), B3(구분선), B4(주석 제거) |
| `Blueprint.cpp` | B1(destructor), B3(구분선) |
| `BlueprintComponent.cpp` | B1(destructor), B3(구분선) |
| `Property.cpp` | B1(destructor) |
| `Material.cpp` | B1(destructor) |
| `BlueprintVariable.cpp` | B1(destructor), B4(주석 제거) |
| `BlueprintGraph.cpp` | B1(destructor) |
| `StaticMesh.cpp` | (변경 없음 — 이미 올바름) |

### 수정 파일 (문서)

| 파일 | 내용 |
|------|------|
| `CLAUDE.md` | File Structure + Shared Utilities + Code Style Details 업데이트 |
| `README.md` | 파일 구조 트리에 WN_MCP_ActorUtils 추가 |

---

## 검증 기준

1. UE 에디터에서 C++ 빌드 성공
2. `uv run python -m pytest tests/test_unit_tools.py -v` — 85개 전부 통과
3. 기능 변경 없음 (리팩터링 only)
4. 모든 9개 .cpp 파일에서:
   - Destructor에 빈 줄 없음
   - OnExecute 내 모든 커맨드 블록에 72-dash 구분선 있음
   - 인라인 주석 대문자 시작
   - `// Get required parameters`, `// Return result` 주석 없음
5. Actor.h가 다른 CommandGroup .h 파일과 동일한 구조
6. Actor.cpp, ActorComponent.cpp에서 inline actor 찾기 루프 없음 (FindActorByName 사용)
7. `read_actor_content` C++ 커맨드 등록 및 구현 완료

---

## 의사결정 근거

### FindActorByName을 Runtime 모듈에 배치한 이유

Actor와 ActorComponent는 모두 Runtime 모듈에 속한다. Editor 모듈의 `FindBlueprintByName`처럼,
같은 모듈 내 공유 유틸리티로 배치하는 것이 자연스럽다.

### 파일 스코프 static을 선택한 이유

- `.h` 파일을 깨끗하게 유지 (forward declaration, private 멤버 불필요)
- helper가 해당 `.cpp`에서만 사용됨 → 외부 노출 불필요
- BlueprintGraph.cpp에서 이미 이 패턴 사용 중 → 선례 있음

### Destructor 규칙을 분리한 이유

WN_MCP 레퍼런스 코드에서 constructor는 빈 줄 있고 destructor는 빈 줄 없는 패턴이 확인됨.
Actor.cpp(가장 먼저 작성된 파일)이 이미 이 패턴을 따르고 있었음.
나머지 파일들이 일관성 없이 작성되어 통일이 필요했음.
