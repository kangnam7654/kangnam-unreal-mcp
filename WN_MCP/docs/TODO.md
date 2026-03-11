# WN_MCP TODO

> 우선순위: P0 (즉시) > P1 (단기) > P2 (중기) > P3 (장기)

---

## P0 — 즉시

### Python 이중 시스템 통합 방향 결정

**현황**: PyMCP(`WN_MCP/PyMCP/`)와 WN_MCP_WORLD Python(`WN_MCP_WORLD/Python/`) 두 시스템이 공존.

| 구분 | PyMCP (WN_MCP) | WN_MCP_WORLD Python |
|------|---------------|---------------------|
| 위치 | `WN_MCP/PyMCP/` | `WN_MCP_WORLD/Python/` |
| 프레임워크 | FastMCP 3.x | FastMCP 2.x |
| Tool 수 | ~15개 (actor, blueprint, material) | 38개 (전체 CRUD) |
| 테스트 | 없음 | 224개 (Unit+Integration+E2E, 100% 커버리지) |
| 구조 | `src/unreal_mcp/` 모듈화 | `tools/` 플랫 구조 |
| 헬퍼 | actor_name_manager, blueprint_graph 등 | ue_connection.py |

**문제점**:
- 기능 중복 (Actor, Blueprint, Material Tool이 양쪽에 존재)
- 버전 관리 이중화 (pyproject.toml 2개)
- 사용자 혼란 (어떤 서버를 실행해야 하는지)

**선택지**:
1. **PyMCP 중심 통합**: WN_MCP_WORLD Tool을 PyMCP의 사용자 Tool로 편입. PyMCP가 유일한 진입점
2. **WN_MCP_WORLD 중심 유지**: PyMCP는 코어 기능만 제공, WN_MCP_WORLD가 실제 Tool 서빙
3. **완전 분리**: PyMCP 내장 Tool 제거, 코어 연결 기능만 유지. 모든 도메인 Tool은 확장 플러그인에서 제공

**권장**: 선택지 3 — PyMCP는 연결/발견/프로토콜만 담당, 도메인 로직은 확장 플러그인에 위임

### PyMCP 레거시 정리

- [ ] `WN_MCP/PyMCP/Tools/` 디렉토리 제거 (레거시, 미사용)
- [ ] 내장 UE Tool(`tools/ue/actors.py`, `blueprints.py`, `materials.py`)과 WN_MCP_WORLD Tool 중복 해소

---

## P1 — 단기

### 포트 공유 메커니즘

**현황**: UE C++ 서버가 27777~27787 범위에서 자동 선택한 포트를 Python이 알아내는 방법이 명확하지 않음.

- [ ] 포트 정보를 파일(`{ProjectDir}/Saved/WN_MCP_Port.txt`)에 기록
- [ ] 또는 환경변수로 전달
- [ ] Python 서버가 자동으로 포트를 발견하는 표준 메커니즘 확립

### 연결 안정성 강화

- [ ] 하트비트/핑 메커니즘 추가 (연결 끊김 감지)
- [ ] 자동 재연결 로직 개선 (현재 3회 재시도 후 포기)
- [ ] 연결 상태 변경 이벤트 (콜백 또는 이벤트 시스템)

### 에러 처리 표준화

- [ ] C++ 에러 코드 `-32003` (UE Communication Error) 실제 사용처 추가
- [ ] Python 측 에러 응답 포맷 통일 (현재 `{"status": "error"}` vs `{"success": False}` 혼재)
- [ ] 에러 로깅 레벨 표준화 (C++ UE_LOG + Python logging)

---

## P2 — 중기

### 테스트 인프라

**현황**: WN_MCP 코어에 대한 테스트가 전무.

- [ ] C++ 유닛 테스트 추가 (JSON-RPC 파싱, 커맨드 디스패치)
- [ ] PyMCP 유닛 테스트 추가 (connection, protocol, server factory)
- [ ] 통합 테스트: PyMCP ↔ UE TCP 서버 연동

### 문서화

- [x] 아키텍처 문서 (`docs/README.md`, `docs/architecture.md`)
- [ ] API 레퍼런스: 모든 Public 클래스/함수의 상세 설명
- [ ] 확장 가이드: 새 플러그인 작성 step-by-step 튜토리얼
- [ ] 트러블슈팅 가이드: 자주 발생하는 문제와 해결법

### 성능 최적화

- [ ] 대용량 응답 스트리밍 지원 (현재 8KB 버퍼로 분할 수신)
- [ ] 배치 커맨드 실행 (여러 커맨드를 한 번의 TCP 왕복으로)
- [ ] 응답 캐싱 (get_available_materials 등 변경 빈도 낮은 조회)

### 다중 클라이언트 지원

**현황**: TCP 서버가 단일 클라이언트만 처리.

- [ ] 동시 다중 연결 지원
- [ ] 클라이언트별 세션 관리
- [ ] 커맨드 실행 큐잉 (GameThread 충돌 방지)

---

## P3 — 장기

### 보안

- [ ] 로컬 인증 토큰 (localhost라도 무단 접근 방지)
- [ ] 커맨드별 권한 제어 (읽기 전용 vs 쓰기)
- [ ] 감사 로그 (누가 어떤 커맨드를 실행했는지)

### 크로스 플랫폼

- [ ] macOS 지원 (현재 Win64 전용)
- [ ] Linux 지원

### 고급 기능

- [ ] 이벤트 구독 시스템 (UE → Python 방향 푸시 알림)
- [ ] 바이너리 프로토콜 옵션 (대용량 데이터 전송 효율화)
- [ ] WebSocket 전환 (TCP 대비 관리 편의성)
- [ ] 원격 접속 지원 (현재 localhost 한정)

### PyMCP 현대화

- [ ] FastMCP 3.x 최신 기능 활용 (현재 부분적 사용)
- [ ] async/await 전면 도입 (현재 sync 기반)
- [ ] MCP 프롬프트 시스템 활용 확대

---

## 완료 항목

| 항목 | 완료일 | 상세 |
|------|--------|------|
| UTF-8 응답 잘림 수정 | 2026-03-11 | [bugfix/utf8-response-truncation.md](bugfix/utf8-response-truncation.md) |
| 커맨드 등록 시스템 리디자인 | 2026-03-11 | FWN_MCP_CommandInfo + AppName prefix |
| WN_MCP_WORLD 38개 커맨드 구현 | 2026-03-11 | 10 그룹, 224 테스트, 100% 커버리지 |
| IWYU 준수 | 2026-03-11 | CoreMinimal.h, ModuleManager.h 등 |
| 코드 컨벤션 통일 | 2026-03-11 | 9개 CommandGroup 파일 |
