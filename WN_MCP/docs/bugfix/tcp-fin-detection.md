# BUG FIX: TCP FIN Detection in is_ue_connected()

## 날짜
2026-03-13

## 영향 범위
**WN_MCP 코어** — UE 연결 상태 감지에 의존하는 모든 Tool/Command

## 증상
- UE 에디터를 종료해도 MCP 클라이언트(Cursor 등)에서 여전히 "CONNECTED"로 표시
- `check_ue_connection` 호출 시 실제로는 끊어진 연결을 "활성"으로 보고
- auto-reconnect 스레드가 끊김을 감지하지 못해 재연결 로직 미작동

## 근본 원인
`WN_MCP/PyMCP/Tools/ue_interaction_tool.py` — `is_ue_connected()`

```python
# BEFORE (buggy)
UE_SOCKET.setblocking(False)
data = UE_SOCKET.recv(1, socket_module.MSG_PEEK)

# If we get here without exception, connection is valid
return True
```

UE가 종료하면 TCP FIN을 전송한다. `recv(1, MSG_PEEK)`는 FIN 수신 시 예외를 발생시키지 않고 **빈 데이터(`b""`)**를 반환한다. 코드는 "예외가 없으면 연결 유효"로 가정하고 `True`를 반환하므로, FIN을 수신해도 연결 끊김을 감지하지 못했다.

참고: `ue_receive_response()`에서는 이미 빈 데이터를 올바르게 처리하고 있었으나, `is_ue_connected()`에는 해당 체크가 누락되어 있었다.

## 수정

```python
# AFTER (fixed)
data = UE_SOCKET.recv(1, socket_module.MSG_PEEK)

if not data:
    # Empty data = connection closed by peer (TCP FIN received)
    log_debug('recv check detected closed connection (empty data from peer)')
    return False

return True
```

빈 데이터 반환 시 `False`를 리턴하여 TCP FIN을 정상 감지한다.

## 영향받는 파일
- `WN_MCP/PyMCP/Tools/ue_interaction_tool.py` (`is_ue_connected()`)

## 테스트
1. MCP 서버 시작 (UE 꺼진 상태) → `check_ue_connection` → OFFLINE 확인
2. UE 실행 → auto-reconnect 감지 → CONNECTED 확인
3. UE 종료 → 1초 내 DISCONNECTED 전환 확인
