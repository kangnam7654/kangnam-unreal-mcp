# Logging 설계서

## 목적

FastMCP는 stdio transport를 사용하므로 stdout/stderr를 MCP 프로토콜이 점유한다. 디버깅 시 로그 확인이 매우 어렵기 때문에 **파일 기반 로깅 + Agent 로그 조회** 시스템을 구현한다.

## 요구사항

1. **파일 로깅**: `logs/mcp_YYYY-MM-DD.log` 형식으로 일별 로그 파일 생성
2. **로그 레벨**: ERROR, WARNING, INFO, DEBUG + 커스텀 MISC (DEBUG보다 낮음)
3. **Settings.ini**: 로그 설정을 외부 설정 파일로 관리
4. **자동 정리**: 보존 기간/최대 파일 수 기반으로 오래된 로그 삭제
5. **런타임 변경**: Agent가 `set_log_level` Tool로 로그 레벨 변경 가능
6. **Agent 로그 조회**: Agent가 `get_recent_logs` Tool로 최근 로그를 직접 조회/분석 가능

## 로그 레벨

| Level | 값 | 용도 |
|-------|-----|------|
| ERROR | 40 | 에러만 |
| WARNING | 30 | 에러 + 경고 |
| INFO | 20 | 에러 + 경고 + 정보 (기본값) |
| DEBUG | 10 | 모든 메시지 |
| MISC | 5 | DEBUG + JSON 요청/응답 전문 (가장 상세) |

MISC는 Python `logging`에 없는 커스텀 레벨. `logging.addLevelName(5, "MISC")`로 등록한다.

## Settings.ini

위치: `KN_MCP_EXTENSION/Python/Settings.ini`

```ini
[Logging]
# Log level: ERROR, WARNING, INFO, DEBUG, MISC (default: INFO)
LOG_LEVEL = INFO

# Log retention period in days (default: 7)
LOG_RETENTION_DAYS = 7

# Maximum number of log files to keep (default: 2)
# Keep latest n files (including current). 0 = unlimited
MAX_LOG_FILES = 2

# Enable automatic cleanup of old logs (default: true)
LOG_AUTO_CLEANUP = true
```

파일이 없으면 기본값으로 동작한다 (에러 없음).

## 로그 파일

- **위치**: `KN_MCP_EXTENSION/Python/logs/`
- **파일명**: `mcp_2026-03-11.log` (날짜 기반, 일별 1개)
- **인코딩**: UTF-8

### 포맷

```
2026-03-11 14:30:00 [INFO] [mcp_server] Server started
2026-03-11 14:30:00 [INFO] [ue_connection] Connected to UE at 127.0.0.1:27777
2026-03-11 14:30:01 [INFO] [ue_connection] >> KN_MCP_EXTENSION_spawn_actor
2026-03-11 14:30:01 [MISC] [ue_connection] >> {"jsonrpc":"2.0","method":"command","id":"KN_MCP_EXTENSION_spawn_actor","params":{...}}
2026-03-11 14:30:01 [MISC] [ue_connection] << {"jsonrpc":"2.0","result":{...},"id":"KN_MCP_EXTENSION_spawn_actor"}
2026-03-11 14:30:01 [ERROR] [ue_connection] UE communication failed: Connection refused
```

- INFO: 커맨드 이름만 (간결)
- MISC: JSON 전문 (디버깅용)

## 듀얼 출력: 파일 + 인메모리 Ring Buffer

로그를 **파일**과 **인메모리 Ring Buffer** 두 곳에 동시 출력한다.

```
logging.getLogger("kn_mcp_extension")
    │
    ├─ FileHandler        → logs/mcp_YYYY-MM-DD.log (영속 저장)
    │
    └─ RingBufferHandler  → collections.deque(maxlen=1000) (Agent 조회용)
```

### RingBufferHandler

- `logging.Handler` 서브클래스
- `collections.deque(maxlen=1000)` 사용 (thread-safe append)
- 각 엔트리 저장 형식: `{"timestamp", "level", "logger", "message"}`
- 서버 재시작 시 초기화됨 (영속성은 파일이 담당)

### Agent 조회 흐름

```
Agent: "방금 에러 뭐였어?"
    │
    ▼
get_recent_logs(count=10, level="ERROR")
    │
    ▼
RingBufferHandler.get_entries(count=10, level="ERROR")
    │ deque에서 역순 스캔, 레벨/키워드 필터
    │
    ▼
Agent: 로그를 분석해서 원인 설명
```

## 아키텍처 (구현 완료)

### 디렉터리 구조

```
Python/
├── Settings.ini                    # 로그 설정
├── mcp_logging/                    # 로깅 인프라 (tools/와 분리)
│   ├── __init__.py                 # Public API: initialize, set_level, get_level, get_recent_entries
│   ├── config.py                   # Settings.ini 로딩, 레벨 파싱
│   └── ring_buffer.py              # RingBufferHandler (인메모리 Ring Buffer)
├── tools/
│   ├── log_tools.py                # Agent용 Tool (set_log_level, get_recent_logs)
│   └── ue_connection.py            # 로깅 호출 추가
├── tests/
│   └── test_unit_logging.py        # 로깅 전용 테스트 (26개)
└── logs/                           # 런타임 생성
    └── mcp_YYYY-MM-DD.log
```

### 모듈 관계

```
mcp_server.py
    │
    │ startup: mcp_logging.initialize()
    │
    ├─ mcp_logging/                     # 인프라 (Agent가 직접 접근 안 함)
    │   ├─ config.py                    # Settings.ini → Dict, parse_level()
    │   ├─ ring_buffer.py               # RingBufferHandler (deque 기반)
    │   └─ __init__.py                  # initialize / set_level / get_recent_entries
    │
    ├─ tools/log_tools.py               # Agent용 Tool (2개)
    │   ├─ set_log_level(level) -> str  # 로그 레벨 변경
    │   └─ get_recent_logs(...) -> str  # 최근 로그 조회
    │
    └─ tools/ue_connection.py           # 로깅 호출 추가
        ├─ connect()    → INFO: "Connected to UE"
        ├─ disconnect() → INFO: "Disconnected from UE"
        └─ execute()    → INFO: command name / MISC: JSON 전문 / ERROR: 실패
```

## Agent Tools

### set_log_level

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `level` | str | O | 로그 레벨 (ERROR/WARNING/INFO/DEBUG/MISC) |

응답 예:
```json
{"log_level": "DEBUG"}
```

### get_recent_logs

| 파라미터 | 타입 | 필수 | 기본값 | 설명 |
|---------|------|------|--------|------|
| `count` | int | X | 20 | 반환할 엔트리 수 (max 200) |
| `level` | str | X | "INFO" | 최소 로그 레벨 필터 |
| `keyword` | str | X | "" | 메시지 내 키워드 필터 (대소문자 무시) |

응답 예:
```json
{
  "total_in_buffer": 157,
  "returned": 3,
  "filter": {"level": "ERROR", "keyword": ""},
  "entries": [
    {"timestamp": "2026-03-11 14:30:05", "level": "ERROR", "logger": "ue_connection", "message": "UE communication failed: Connection refused"},
    {"timestamp": "2026-03-11 14:29:50", "level": "ERROR", "logger": "ue_connection", "message": "UE communication failed: timeout"}
  ]
}
```

### 활용 시나리오

| Agent 요청 | Tool 호출 |
|------------|-----------|
| "방금 뭐가 실패했어?" | `get_recent_logs(count=5, level="ERROR")` |
| "spawn_actor 호출 기록 보여줘" | `get_recent_logs(count=10, keyword="spawn_actor")` |
| "디버그 모드로 바꿔" | `set_log_level(level="DEBUG")` |
| "JSON 통신 내용도 보고 싶어" | `set_log_level(level="MISC")` |
| "최근 통신 전문 보여줘" | `get_recent_logs(count=5, level="MISC", keyword="<<")` |

## 파일 변경 목록

### 신규 파일

| 파일 | 설명 |
|------|------|
| `Python/Settings.ini` | 로그 설정 (INI 포맷) |
| `Python/mcp_logging/__init__.py` | Public API (initialize, set_level, get_recent_entries) |
| `Python/mcp_logging/config.py` | Settings.ini 로딩, 레벨 파싱 |
| `Python/mcp_logging/ring_buffer.py` | RingBufferHandler 클래스 |
| `Python/tools/log_tools.py` | Agent용 Tool 2개 (`set_log_level`, `get_recent_logs`) |
| `Python/tests/test_unit_logging.py` | 로깅 전용 Unit 테스트 (26개) |

### 수정 파일

| 파일 | 변경 |
|------|------|
| `Python/mcp_server.py` | `mcp_logging.initialize()` 호출 추가 (2줄) |
| `Python/tools/__init__.py` | `log_tools` import + `register_tools()` 추가 (2줄) |
| `Python/tools/ue_connection.py` | `logger` 인스턴스 + 로깅 호출 (8줄) |
| `Python/tests/test_unit_tools.py` | 도구 수 38 → 40, log tools 추가 (3줄) |

## 로그 정리 정책

1. `LOG_RETENTION_DAYS`: 지정 일수보다 오래된 로그 삭제
2. `MAX_LOG_FILES`: 최신 N개만 유지, 나머지 삭제
3. 두 정책 모두 적용 (각각 독립 실행)
4. 오늘 로그는 절대 삭제하지 않음

## C++ 변경

없음. 로깅은 순수 Python 기능이므로 C++ 커맨드 불필요.
