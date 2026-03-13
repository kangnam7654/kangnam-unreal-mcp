# dev/kangnam 브랜치 마이그레이션 분석

> 작성: 2026-03-13
> 비교 대상: `main` (커밋 `9989cbd`) vs `origin/dev/kangnam`
> dev/kangnam은 구 `WN_MCP` 네이밍 사용. main은 `KN_MCP`로 리네이밍 완료.

## 이미 포팅 완료된 항목

| 항목 | 설명 | 포팅 커밋 |
|------|------|-----------|
| TCP FIN 감지 | `recv()` 빈 데이터 = 연결 종료 처리 | `9989cbd` (connection.py:173) |
| Dual-socket 통합 | Extension이 core 소켓 공유 | `9989cbd` (ue_connection.py → send_command) |
| category_name 파라미터 | `send_command(cmd, category_name=)` | `9989cbd` |
| KN_MCP_REGISTER_COMMAND 2-param | Description 제거 | `9989cbd` |
| JSON-RPC method 필드 | 요청에 method 필드 포함 | `9989cbd` (protocol.py) |
| 로깅 인프라 | settings.ini 기반 로그 레벨/보존/정리 | `9989cbd` (tools/logging.py) |
| Agent-Chain Result 매크로 | C++ 7개 result 빌더 매크로 | `30aecb6` (KN_MCP_CommandGroup.h) |
| Python Schemas 모듈 | 매크로 대응 빌더/검증 헬퍼 | `ef647ac` (kn_mcp/core/schemas.py) |
| 연결 확장 기능 | 포트 스캔, 리스닝 체크, 상태 콜백 | `0907fc3` (connection.py) |
| KN_MCPTest 플러그인 | 확장 플러그인 데모 + 테스트 | `c03527a` (KN_MCPTest/) |
| Agent 파라미터 컨텍스트 | ContextVar 기반 Tool 파라미터 접근 | `b45e4d7` (kn_mcp/params.py) |
| MISC 로그 레벨 | DEBUG보다 상세한 진단용 레벨 | `481979a` (tools/logging.py) |

---

## 포팅 대상 항목

### 1. Agent-Chain Result 매크로 (C++)

**출처**: `WN_MCP/Source/WN_MCP/Public/WN_MCP_CommandGroup.h` (L300–L590)
**대상**: `KN_MCP/Source/KN_MCP/Public/KN_MCP_CommandGroup.h`
**유형**: KN_MCP 코어 변경 (사전 승인 필요)

비동기/다단계 Agent 워크플로우를 위한 result 빌더 매크로 7개:

| 매크로 | 용도 | Case Study |
|--------|------|------------|
| `KN_MCP_CREATE_RESULT_RUN_REQUIRED(cmd, msg)` | Agent에게 외부 커맨드 실행 후 결과 보고 요청 | Case 2/7 |
| `KN_MCP_CREATE_RESULT_ACCEPTED(reqId, msg)` | 비동기 작업 시작됨 (폴링 가능) | Case 3 |
| `KN_MCP_CREATE_RESULT_RUNNING(reqId, progress)` | 진행 중 (0.0~1.0 진행률) | Case 3 |
| `KN_MCP_CREATE_RESULT_COMPLETED(reqId)` | 완료됨 (결과 데이터 추가 가능) | Case 3 |
| `KN_MCP_CREATE_RESULT_RECEIVED()` | 결과 수신 확인 (`{"received": true}`) | Case 2 |
| `KN_MCP_CREATE_RESULT_FOLLOW_UP_REQUIRED(method)` | 후속 Tool 호출 필요 | §3 |
| `KN_MCP_CREATE_RESULT_WITH_SUGGESTED_TOOL(tool)` | 다음 Tool 제안 (힌트) | Case 4 |

**구현 패턴**: 각 매크로는 IIFE 람다로 `TSharedPtr<FJsonObject>` 반환. `KN_RETURN_COMMAND_RESPONSE()`와 조합 사용.

```cpp
// 사용 예시
auto result = KN_MCP_CREATE_RESULT_RUN_REQUIRED(cmd, TEXT("Run and report via result tool"));
result->SetStringField(TEXT("fbx_path"), fbxPath);
KN_RETURN_COMMAND_RESPONSE(result);
```

**포팅 우선순위**: HIGH
**근거**: 현재 사용처 없으나, Agent-Chain Case Study 문서가 이미 존재하고 향후 비동기 작업(Bake, Import 등) 구현 시 즉시 필요.

---

### 2. Python Schemas 모듈

**출처**: `WN_MCP/PyMCP/src/unreal_mcp/core/schemas.py` (173줄)
**대상**: `KN_MCP/Python/kn_mcp/core/schemas.py` (신규)
**유형**: KN_MCP Python 코어 변경 (사전 승인 필요)

위 C++ 매크로의 Python 대응. Agent-Chain 결과 구조를 Python 쪽에서도 일관되게 생성/검증.

**상수**:
- 상태값: `run_required`, `accepted`, `completed`, `running`, `follow_up_required`, `failed`
- 필드명: `command`, `params`, `then_method`, `then_params`, `request_id`, `data`, `progress`
- 에러코드: `-32602` (Invalid params), `-32000` (Server), `-32603` (Internal)

**빌더 함수**:
| 함수 | 용도 |
|------|------|
| `build_result_run_required(cmd, params, msg)` | run_required 결과 생성 |
| `build_result_accepted(reqId, msg)` | accepted 결과 생성 |
| `build_result_running(reqId, progress)` | running 결과 생성 |
| `build_result_completed(reqId, data)` | completed 결과 생성 |
| `build_result_follow_up_required(method, params)` | follow_up 결과 생성 |
| `build_error(code, msg, data)` | JSON-RPC 에러 객체 생성 |

**검증 헬퍼**: `is_run_required_result()`, `validate_run_required_result()` 등

**포팅 우선순위**: HIGH
**근거**: C++ 매크로와 1:1 대응. 함께 포팅해야 일관성 유지.

---

### 3. Agent 파라미터 컨텍스트 시스템

**출처**: `WN_MCP/PyMCP/Tools/params.py` (117줄)
**대상**: `KN_MCP/Python/kn_mcp/params.py` (신규)
**유형**: KN_MCP Python 코어 변경 (사전 승인 필요)

`ContextVar` 기반 thread-safe MCP 요청 파라미터 저장:

```python
# Tool 내부에서 Agent가 전달한 파라미터 접근
params = get_mcp_params()
user_input = params.get('user_input', '')
```

**핵심 기능**:
- `get_mcp_params()` / `_set_mcp_params()` — ContextVar 기반 저장/조회
- `enable_mcp_params_capture(mcp)` — FastMCP `@mcp.tool` 데코레이터를 래핑하여 모든 Tool 호출 시 자동으로 파라미터 캡처

**포팅 우선순위**: LOW
**근거**: 현재 사용처 없음. Agent introspection이 필요해질 때 포팅.

---

### 4. 확장 로깅 기능

**출처**: `WN_MCP/PyMCP/Tools/log_tool.py` (476줄)
**대상**: `KN_MCP/Python/kn_mcp/tools/logging.py` (현재 219줄)
**유형**: KN_MCP Python 코어 변경

dev/kangnam에만 있는 추가 기능:

| 기능 | 설명 | 현재 상태 |
|------|------|-----------|
| `MISC_LEVEL = 5` | DEBUG보다 상세한 커스텀 로그 레벨 | 미포팅 |
| Ring buffer | 메모리 내 최근 로그 접근 | 미포팅 |
| `log_misc()` | MISC 레벨 로그 함수 | 미포팅 |

**포팅 우선순위**: LOW
**근거**: 현재 로깅 모듈이 이미 핵심 기능(레벨 설정, 파일 핸들러, 정리)을 포함. MISC 레벨과 ring buffer는 디버깅 시 필요할 때 추가.

---

### 5. 연결 확장 기능

**출처**: `WN_MCP/PyMCP/Tools/ue_interaction_tool.py` (1575줄)
**대상**: `KN_MCP/Python/kn_mcp/connection.py` (현재 ~280줄)
**유형**: KN_MCP Python 코어 변경

| 기능 | 설명 | 현재 상태 |
|------|------|-----------|
| `find_available_ue_ports()` | 27777~27787 포트 스캔 | 미포팅 |
| `register_connection_callback()` | 연결 상태 변경 콜백 | 미포팅 |
| `register_ue_connected_callback()` | 연결 성공 콜백 | 미포팅 |
| `register_notification_callback()` | UI 알림 콜백 | 미포팅 |
| `start_auto_reconnect()` | 자동 재연결 제어 | 미포팅 |
| `LAST_STATUS_CHANGE` | 마지막 연결 상태 변경 기록 | 미포팅 |

**포팅 우선순위**: MEDIUM
**근거**: 멀티 인스턴스 지원과 Agent에게 연결 상태 노출에 유용. 다만 현재 connection.py가 이미 재시도/재연결을 내장하고 있어 즉시 필요하지 않음.

---

### 6. 테스트 플러그인 (KN_MCPTest)

**출처**: `WN_MCPTest/` (C++ + Python)
**대상**: `KN_MCPTest/` (신규)
**유형**: 별도 플러그인

Extension 플러그인 작성 방법을 보여주는 예시 + C++ 커맨드 테스트:
- `FKN_MCP_CommandGroup_Test` — `REGISTER_COMMAND` + `REGISTER_SIMPLE_COMMAND` 사용 예시
- `test_tool.py` — Python Tool에서 C++ 커맨드 호출 예시

**포팅 우선순위**: MEDIUM
**근거**: 새 확장 플러그인 작성 시 참조 템플릿. 현재는 CLAUDE.md의 템플릿이 그 역할을 대신함.

---

## 요약 — 포팅 우선순위 정리

| 우선순위 | 항목 | 유형 | 변경 대상 |
|----------|------|------|-----------|
| ~~**HIGH**~~ | ~~Agent-Chain Result 매크로 (C++)~~ | ~~KN_MCP 코어~~ | ~~`KN_MCP_CommandGroup.h`~~ ✅ `30aecb6` |
| ~~**HIGH**~~ | ~~Python Schemas 모듈~~ | ~~KN_MCP Python 코어~~ | ~~`kn_mcp/core/schemas.py`~~ ✅ `ef647ac` |
| ~~**MEDIUM**~~ | ~~연결 확장 기능~~ | ~~KN_MCP Python 코어~~ | ~~`kn_mcp/connection.py`~~ ✅ `0907fc3` |
| ~~**MEDIUM**~~ | ~~테스트 플러그인~~ | ~~별도 플러그인~~ | ~~`KN_MCPTest/`~~ ✅ `c03527a` |
| ~~**LOW**~~ | ~~Agent 파라미터 컨텍스트~~ | ~~KN_MCP Python 코어~~ | ~~`kn_mcp/params.py`~~ ✅ `b45e4d7` |
| ~~**LOW**~~ | ~~확장 로깅 (MISC)~~ | ~~KN_MCP Python 코어~~ | ~~`kn_mcp/tools/logging.py`~~ ✅ `481979a` |

## 참고: KN_MCP 코어 변경 원칙

HIGH 항목은 모두 KN_MCP 코어 변경이므로 다음 원칙을 준수:
1. 목적 외 코드 변경 금지
2. 기존 동작 보존 (KN_MCP_EXTENSION 수정 없이 동작)
3. 변경 단위 커밋 (다른 변경과 혼합 금지)
4. 사전 승인 후 작업
