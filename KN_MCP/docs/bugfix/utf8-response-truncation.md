# BUG FIX: UTF-8 Response Truncation

## 날짜
2026-03-11

## 영향 범위
**KN_MCP 코어** — TCP 응답을 보내는 모든 커맨드에 영향

## 증상
- `read_blueprint_graph` 등 **non-ASCII 문자**(한국어 로컬라이즈 텍스트)를 포함하는 응답이 잘려서 전송됨
- Python 클라이언트가 불완전한 JSON을 수신 → `JSONDecodeError` → 추가 데이터를 기다리며 `recv` 대기 → 30초 후 타임아웃
- 순수 ASCII 응답만 반환하는 커맨드(Actor, Blueprint CRUD 등)는 영향 없음

## 근본 원인
`KN_MCP_ServerThread.cpp:78`

```cpp
// BEFORE (buggy)
ClientSocketPtr->Send((uint8*)TCHAR_TO_UTF8(*response), response.Len(), bytesSend)
```

- `response.Len()` → TCHAR **문자 수** (FString의 character count)
- `TCHAR_TO_UTF8(*response)` → UTF-8 **바이트 스트림**

ASCII 문자는 UTF-8에서 1바이트이므로 문자 수 == 바이트 수. 그러나 한국어 등 non-ASCII 문자는 UTF-8에서 **3바이트**를 차지하므로, 실제 UTF-8 바이트 수 > 문자 수. `Send()`에 문자 수를 전달하면 응답 끝이 잘린다.

### 예시

| 텍스트 | TCHAR 문자 수 | UTF-8 바이트 수 | 차이 |
|--------|-------------|---------------|------|
| `"BeginPlay 이벤트"` | 13 | 19 | +6 |
| `"ActorBeginOverlap 이벤트"` | 22 | 28 | +6 |
| `"Tick 이벤트"` | 8 | 14 | +6 |

3개 노드 타이틀에서 총 18바이트가 부족 → 응답 JSON 끝 18바이트가 잘림 → `"id": "read_b`에서 끊김.

## 수정

```cpp
// AFTER (fixed)
FTCHARToUTF8 utf8Response(*response);
ClientSocketPtr->Send((uint8*)utf8Response.Get(), utf8Response.Length(), bytesSend)
```

`FTCHARToUTF8`를 명시적으로 생성하여:
1. UTF-8 변환 결과의 **수명**을 Send 호출까지 보장
2. `.Length()`로 실제 **UTF-8 바이트 수**를 전달

## 진단 과정

1. `read_blueprint_graph`가 30초 타임아웃으로 실패
2. 다른 그래프 커맨드(add_event_node, connect_nodes 등)는 정상 → read만 문제
3. 직접 소켓 연결(5초 타임아웃)로 테스트 → 0.13초만에 응답 도착, 그러나 JSON 잘림 확인
4. `node_title`에 한국어 로컬라이즈 텍스트 포함 → UTF-8 바이트 수 불일치 발견
5. `Send()`의 길이 인자가 `response.Len()` (문자 수)인 것이 원인

## 영향받는 파일
- `KN_MCP/Source/KN_MCP/Private/KN_MCP_ServerThread.cpp` (line 76-78)

## 테스트
- 수정 후 UE 에디터 재빌드 필요
- `read_blueprint_graph` 통합 테스트 + E2E 테스트로 검증
