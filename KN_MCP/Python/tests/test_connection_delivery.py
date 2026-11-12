"""Delivery-semantics tests for UnrealConnection.send_command().

A command must be dispatched at most once: after sending has started, a lost,
late or malformed reply is reported as an uncertain outcome and never replayed
automatically. Connection failures before sending are reported as "not_sent".

Hermetic: uses a scripted loopback TCP peer on 127.0.0.1 (a stand-in for the
UE TCP server, not the engine) or in-memory fake sockets.
"""
import json
import socket
import threading

import pytest

from kn_mcp.connection import OUTCOME_NOT_SENT, OUTCOME_UNKNOWN, UnrealConnection


# =============================================================================
# Helpers
# =============================================================================


class FakeUnrealPeer:
    """Scripted loopback TCP server that records every request it receives.

    Each received request consumes one action:
      ("drop",)            close the connection without replying
      ("hold",)            never reply (keep the connection open)
      ("result", payload)  reply with a JSON-RPC result
      ("error", err_obj)   reply with a JSON-RPC error object
      ("raw", data)        send raw bytes, keep the connection open
      ("partial", data)    send raw bytes, then close the connection
    Requests beyond the script are recorded and dropped.
    """

    def __init__(self, actions):
        self._actions = list(actions)
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.requests: list[dict] = []
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.bind(("127.0.0.1", 0))
        self._server.listen(8)
        self._server.settimeout(0.05)
        self.port = self._server.getsockname()[1]
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    @property
    def dispatch_count(self) -> int:
        with self._lock:
            return len(self.requests)

    def _next_action(self):
        with self._lock:
            return self._actions.pop(0) if self._actions else ("drop",)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                conn, _ = self._server.accept()
            except TimeoutError:
                continue
            except OSError:
                return
            with conn:
                try:
                    self._handle(conn)
                except OSError:
                    pass  # client went away mid-reply; nothing to record

    def _handle(self, conn: socket.socket) -> None:
        conn.settimeout(0.05)
        buffer = bytearray()
        while not self._stop.is_set():
            try:
                chunk = conn.recv(65536)
            except TimeoutError:
                continue
            except OSError:
                return
            if not chunk:
                return
            buffer.extend(chunk)
            try:
                request = json.loads(buffer)
            except ValueError:
                continue  # incomplete request so far
            buffer.clear()
            with self._lock:
                self.requests.append(request)
            kind, *args = self._next_action()
            if kind == "drop":
                return
            if kind == "hold":
                continue
            if kind == "result":
                reply = {"jsonrpc": "2.0", "result": args[0], "id": request.get("id")}
                conn.sendall(json.dumps(reply).encode("utf-8"))
            elif kind == "error":
                reply = {"jsonrpc": "2.0", "error": args[0], "id": request.get("id")}
                conn.sendall(json.dumps(reply).encode("utf-8"))
            elif kind == "raw":
                conn.sendall(args[0])
            elif kind == "partial":
                conn.sendall(args[0])
                return
            else:
                raise AssertionError(f"unknown action {kind!r}")

    def close(self) -> None:
        self._stop.set()
        try:
            self._server.close()
        except OSError:
            pass
        self._thread.join(timeout=2)


class FakeSocket:
    """In-memory socket double for failure modes hard to provoke over real TCP."""

    def __init__(self, *, peek=None, sendall_error=None, reply=b""):
        self._peek = peek  # None -> nothing pending; bytes -> returned by MSG_PEEK
        self._sendall_error = sendall_error
        self._reply = reply
        self.sent: list[bytes] = []
        self.closed = False

    def connect(self, address):
        pass

    def settimeout(self, value):
        pass

    def setblocking(self, flag):
        pass

    def recv(self, size, flags=0):
        if flags & socket.MSG_PEEK:
            if self._peek is None:
                raise BlockingIOError()
            return self._peek
        data, self._reply = self._reply, b""
        return data

    def sendall(self, data):
        self.sent.append(bytes(data))
        if self._sendall_error is not None:
            raise self._sendall_error
        if self._reply:
            response = json.loads(self._reply)
            response["id"] = json.loads(data)["id"]
            self._reply = json.dumps(response).encode("utf-8")

    def shutdown(self, how):
        pass

    def close(self):
        self.closed = True


def _quick_connection(port: int) -> UnrealConnection:
    conn = UnrealConnection(host="127.0.0.1", port=port, connect_timeout=2, default_recv_timeout=2)
    conn.MAX_RETRIES = 1
    conn.BASE_RETRY_DELAY = 0.01
    return conn


@pytest.fixture
def make_peer():
    peers: list[FakeUnrealPeer] = []

    def _make(*actions) -> FakeUnrealPeer:
        peer = FakeUnrealPeer(actions)
        peers.append(peer)
        return peer

    yield _make
    for peer in peers:
        peer.close()


@pytest.fixture
def make_conn():
    conns: list[UnrealConnection] = []

    def _make(port: int) -> UnrealConnection:
        conn = _quick_connection(port)
        conns.append(conn)
        return conn

    yield _make
    for conn in conns:
        conn.disconnect()


def _assert_uncertain(response: dict) -> None:
    assert response["status"] == "error"
    assert response["outcome"] == OUTCOME_UNKNOWN
    assert "NOT retried" in response["error"]


SPAWN_PARAMS = {"name": "Cube_1", "type": "StaticMeshActor"}


# =============================================================================
# Lost / ambiguous replies over loopback TCP
# =============================================================================


class TestAmbiguousFailuresAreNotReplayed:
    def test_dropped_reply_dispatches_once_and_is_uncertain(self, make_peer, make_conn):
        peer = make_peer(("drop",), ("result", {"actor": "Cube_1"}))
        conn = make_conn(peer.port)

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        _assert_uncertain(response)
        assert peer.dispatch_count == 1
        assert peer.requests[0]["method"] == "Actor_spawn_actor"
        assert conn.socket is None
        assert conn.connected is False

    def test_later_explicit_command_reconnects_and_succeeds(self, make_peer, make_conn):
        peer = make_peer(("drop",), ("result", {"actor": "Cube_1"}))
        conn = make_conn(peer.port)

        first = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)
        _assert_uncertain(first)
        assert peer.dispatch_count == 1

        second = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)
        assert second == {"actor": "Cube_1"}
        assert peer.dispatch_count == 2

    def test_response_timeout_is_uncertain(self, make_peer, make_conn):
        peer = make_peer(("hold",))
        conn = make_conn(peer.port)
        conn.default_recv_timeout = 0.3

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        _assert_uncertain(response)
        assert peer.dispatch_count == 1
        assert conn.socket is None

    def test_partial_reply_then_disconnect_is_uncertain(self, make_peer, make_conn):
        peer = make_peer(("partial", b'{"jsonrpc": "2.0", "resu'))
        conn = make_conn(peer.port)

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        _assert_uncertain(response)
        assert peer.dispatch_count == 1

    def test_malformed_reply_is_uncertain_and_discards_socket(self, make_peer, make_conn):
        peer = make_peer(("raw", b'{"jsonrpc": "2.0", "id": "x"}'))
        conn = make_conn(peer.port)

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        _assert_uncertain(response)
        assert peer.dispatch_count == 1
        assert conn.socket is None

    def test_wrong_response_id_is_not_accepted_as_success(self, make_peer, make_conn):
        peer = make_peer(("raw", b'{"jsonrpc": "2.0", "id": "previous-command", "result": {"actor": "Cube_1"}}'))
        conn = make_conn(peer.port)

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        _assert_uncertain(response)
        assert "response id" in response["error"]
        assert peer.dispatch_count == 1
        assert conn.socket is None


# =============================================================================
# Normal contract is preserved
# =============================================================================


class TestResponseContract:
    def test_success_returns_result_payload(self, make_peer, make_conn):
        peer = make_peer(("result", {"actor": "Cube_1", "location": [0, 0, 0]}))
        conn = make_conn(peer.port)

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        assert response == {"actor": "Cube_1", "location": [0, 0, 0]}
        assert peer.dispatch_count == 1
        assert peer.requests[0]["params"] == SPAWN_PARAMS
        assert conn.connected is True

    def test_jsonrpc_application_error_is_propagated(self, make_peer, make_conn):
        error = {"code": -32602, "message": "Blueprint not found", "data": {"name": "BP_X"}}
        peer = make_peer(("error", error))
        conn = make_conn(peer.port)

        response = conn.send_command("Blueprint_compile", {"name": "BP_X"})

        assert response == {
            "status": "error",
            "error": "Blueprint not found",
            "code": -32602,
            "data": {"name": "BP_X"},
        }
        assert "outcome" not in response
        assert peer.dispatch_count == 1


# =============================================================================
# Send failures and pre-send connection handling (fake sockets)
# =============================================================================


class TestSendAndConnectFailures:
    def test_unserializable_request_is_not_sent(self, make_peer, make_conn):
        peer = make_peer(("result", {"actor": "Cube_1"}))
        conn = make_conn(peer.port)

        response = conn.send_command("Actor_spawn_actor", {"name": object()})

        assert response["status"] == "error"
        assert response["outcome"] == OUTCOME_NOT_SENT
        assert peer.dispatch_count == 0
        assert conn.socket is None

    def test_sendall_failure_is_uncertain_and_not_replayed(self, monkeypatch):
        failing = FakeSocket(sendall_error=BrokenPipeError("simulated failure after partial send"))
        healthy = FakeSocket(reply=b'{"jsonrpc": "2.0", "result": {"ok": true}, "id": "1"}')
        created = iter([failing, healthy])
        conn = _quick_connection(port=1)
        monkeypatch.setattr(conn, "_create_socket", lambda: next(created))

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        _assert_uncertain(response)
        assert len(failing.sent) == 1
        assert failing.closed is True
        assert conn.socket is None
        assert healthy.sent == []

        # An explicit new call reconnects and dispatches exactly once.
        assert conn.send_command("Actor_spawn_actor", SPAWN_PARAMS) == {"ok": True}
        assert len(failing.sent) == 1
        assert len(healthy.sent) == 1

    def test_stale_idle_socket_is_replaced_before_sending(self, monkeypatch):
        stale = FakeSocket(peek=b"")  # peer already closed the idle connection
        fresh = FakeSocket(reply=b'{"jsonrpc": "2.0", "result": {"ok": true}, "id": "1"}')
        created = iter([stale, fresh])
        conn = _quick_connection(port=1)
        monkeypatch.setattr(conn, "_create_socket", lambda: next(created))
        assert conn.connect() is True

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        assert response == {"ok": True}
        assert stale.sent == []
        assert stale.closed is True
        assert len(fresh.sent) == 1

    def test_connection_refused_is_not_sent(self, make_conn):
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()  # nothing listens on this port now
        conn = make_conn(port)

        response = conn.send_command("Actor_spawn_actor", SPAWN_PARAMS)

        assert response["status"] == "error"
        assert response["outcome"] == OUTCOME_NOT_SENT
        assert response["outcome"] != OUTCOME_UNKNOWN
        assert "not sent" in response["error"]
        assert conn.socket is None
        assert conn.connected is False
