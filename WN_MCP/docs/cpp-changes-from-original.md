# WN_MCP C++ 변경 이력 (원본 대비)

원본 코드: `org/` 디렉터리 (git commit `36fb611`, 도경님 작성)
변경자: 강남
날짜: 2026-03-06 ~ 2026-03-12

---

## 변경 요약

| 요구사항 | 설명 | 관련 파일 |
|----------|------|-----------|
| R1 | 커맨드 prefix를 `GetApplicationName()` → `GetName()` 으로 변경 | WN_MCP_CommandGroup.h/.cpp |
| R2 | JSON-RPC 응답에 `method` 필드 추가 | WN_MCP_CommandGroup.h |
| R3 | Simple command 자동 등록 (`get_simple_commands` 커맨드) | WN_MCP_Module.h/.cpp, CommandGroup_Application.cpp/.h |
| BugFix | UTF-8 응답 바이트 수 계산 오류 수정 | WN_MCP_ServerThread.cpp |
| 경로 | `AddUserToolDirectories`에 절대경로 전달 | WN_MCPTest_Module.cpp |

---

## 1. WN_MCP_CommandGroup.h (Public)

### R1: 커맨드 등록 시스템 변경

**OnRegisterCommands 시그니처 변경**
```
// 원본: 커맨드 이름만 문자열로 전달
void OnRegisterCommands(TArray<FString>& InOutCommandNames) const;

// 변경: FWN_MCP_CommandInfo 구조체 (Name, Description, bIsSimple)
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const;
```

**FWN_MCP_CommandInfo 구조체 추가**
```cpp
struct FWN_MCP_CommandInfo
{
    FString Name;
    FString Description;
    bool bIsSimple;
};
```

**WN_MCP_REGISTER_COMMAND 매크로 추가**
```cpp
// GetName() prefix를 자동으로 붙여서 등록
#define WN_MCP_REGISTER_COMMAND(InOutList, CmdName, CmdDesc)
#define WN_MCP_REGISTER_SIMPLE_COMMAND(InOutList, CmdName, CmdDesc)
```

**GetApplicationName() 가상함수 추가**
```cpp
virtual FString GetApplicationName() const;
```

### R2: 응답 매크로에 method 필드 추가

WN_RETURN_COMMAND_RESPONSE 등 응답 매크로에서 JSON 응답에 `"method"` 필드를 포함하도록 변경.

---

## 2. WN_MCP_CommandGroup.cpp (Private)

### R1: Execute()에서 prefix 제거 로직 추가

```cpp
// 원본: InCommandName을 그대로 OnExecute에 전달
return OnExecute(InCommandName, InParamsPtr, InClientSocketPtr);

// 변경: GetName() prefix를 제거한 후 OnExecute에 전달
FString appName = GetName();
FString rawCommandName = InCommandName;
if (!appName.IsEmpty())
{
    FString prefix = appName + TEXT("_");
    rawCommandName.RemoveFromStart(prefix);
}
return OnExecute(rawCommandName, InParamsPtr, InClientSocketPtr);
```

**GetApplicationName() 기본 구현 추가**
```cpp
FString FWN_MCP_CommandGroup::GetApplicationName() const
{
    return FString("");
}
```

**OnRegisterCommands 시그니처 변경**
```
// 원본
void OnRegisterCommands(TArray<FString>& InOutCommandNames) const

// 변경
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
```

---

## 3. WN_MCP_Module.h (Public)

### R3: GetAllCommandInfos() 추가

```cpp
#include "WN_MCP_CommandGroup.h"  // 추가 (FWN_MCP_CommandInfo 타입 참조)

WN_MCP_API static const TArray<FWN_MCP_CommandInfo>& GetAllCommandInfos();
```

---

## 4. WN_MCP_Module.cpp (Private)

### R1: RegisterCommandGroup() 시그니처 변경

```cpp
// 원본: 커맨드 이름 문자열 배열로 등록
TArray<FString> commandNames;
InGroupPtr->OnRegisterCommands(commandNames);
for (const FString& name : commandNames)
{
    CommandGroupPtrMap.Add(name, InGroupPtr);
}

// 변경: FWN_MCP_CommandInfo 배열로 등록, AllCommandInfos에도 저장
TArray<FWN_MCP_CommandInfo> commandInfos;
InGroupPtr->OnRegisterCommands(commandInfos);
for (const FWN_MCP_CommandInfo& info : commandInfos)
{
    FString fullName = info.Name;
    CommandGroupPtrMap.Add(fullName, InGroupPtr);
    AllCommandInfos.Add(info);
}
```

### R3: AllCommandInfos static 변수 및 getter 추가

```cpp
static TArray<FWN_MCP_CommandInfo> AllCommandInfos;

const TArray<FWN_MCP_CommandInfo>& FWN_MCP_Module::GetAllCommandInfos()
{
    return AllCommandInfos;
}
```

---

## 5. WN_MCP_ServerThread.cpp (Private)

### BugFix: UTF-8 응답 바이트 수 계산 오류

```cpp
// 원본: response.Len() (TCHAR 문자 수)을 바이트 수로 사용 → non-ASCII 응답 잘림
ClientSocketPtr->Send((uint8*)TCHAR_TO_UTF8(*response), response.Len(), bytesSend);

// 변경: FTCHARToUTF8로 실제 UTF-8 바이트 수 사용
FTCHARToUTF8 utf8Response(*response);
ClientSocketPtr->Send((uint8*)utf8Response.Get(), utf8Response.Length(), bytesSend);
```

---

## 6. WN_MCP_ServerThread.h (Private)

BOM 마크(﻿) 제거 외 실질 변경 없음.

---

## 7. WN_MCP_CommandGroup_Application.cpp (Private/Commands)

### R1: OnRegisterCommands 시그니처 변경

```cpp
// 원본
void OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
    InOutCommandNames.Add(FString(TEXT("get_user_tool_directories")));
}

// 변경
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
    WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_user_tool_directories", "Get user tool directories");
    WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_simple_commands", "Get all registered simple commands");
}
```

### R3: get_simple_commands 커맨드 추가

`AllCommandInfos`에서 `bIsSimple == true`인 항목을 JSON 배열로 반환하는 커맨드 추가.

### 스타일: 72-dash 구분선 추가

각 커맨드 블록 앞에 `//-----` 구분선 + 커맨드 이름 추가 (코드 컨벤션).

---

## 8. WN_MCP_CommandGroup_Application.h (Private/Commands)

### R1: OnRegisterCommands 시그니처 변경

```
// 원본
void OnRegisterCommands(TArray<FString>& InOutCommandNames) const override;

// 변경
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const override;
```

---

## 9. WN_MCPTest_Module.cpp (WN_MCPTest)

### 경로: 절대경로 변환 추가

```cpp
// 원본: 상대경로 그대로 전달
FString pythonDir = FPaths::ProjectPluginsDir() + TEXT("WN_MCPTest/Python");

// 변경: 절대경로로 변환 후 전달
FString pythonDir = FPaths::ConvertRelativePathToFull(FPaths::ProjectPluginsDir() + TEXT("WN_MCPTest/Python"));
```

---

## 10. WN_MCPTest_Module.h (WN_MCPTest)

BOM 마크(﻿) 제거 외 실질 변경 없음.

---

## 11. WN_MCP_CommandGroup_Test.cpp (WN_MCPTest)

### R1: GetApplicationName() 추가 및 시그니처 변경

```cpp
// 추가
FString FWN_MCP_CommandGroup_Test::GetApplicationName() const
{
    return FString("WN_MCPTest");
}

// 원본
void OnRegisterCommands(TArray<FString>& InOutCommandNames) const
{
    InOutCommandNames.Add("get_hello_message");
    InOutCommandNames.Add("get_hello_message_array");
}

// 변경
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const
{
    WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_hello_message", "Get hello message from UE");
    WN_MCP_REGISTER_COMMAND(InOutCommandInfos, "get_hello_message_array", "Get hello message array from UE");
}
```

---

## 12. WN_MCP_CommandGroup_Test.h (WN_MCPTest)

### R1: GetApplicationName() 및 시그니처 변경

```cpp
// 추가
FString GetApplicationName() const override;

// 원본
void OnRegisterCommands(TArray<FString>& InOutCommandNames) const override;

// 변경
void OnRegisterCommands(TArray<FWN_MCP_CommandInfo>& InOutCommandInfos) const override;
```
