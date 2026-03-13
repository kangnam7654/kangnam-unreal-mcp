"""
JSON-RPC 2.0 protocol layer for Unreal Engine communication.
Result/error payload schemas (Case Study) live in kn_mcp.core.schemas.

Send (request):
  { "jsonrpc": "2.0", "method": <command_name>, "params": <params>, "id": <uuid> }

Success Receive (response):
  { "jsonrpc": "2.0", "result": <result>, "id": <uuid> }

Failure Receive (response):
  { "jsonrpc": "2.0", "error": { "code": <code>, "message": <message>, "data": <any> }, "id": <uuid> }
"""
import json
import logging
import uuid
from typing import Any

logger = logging.getLogger("UnrealMCP.Protocol")

# --- JSON-RPC 2.0 key constants ---
KEY_JSONRPC = "jsonrpc"
KEY_METHOD = "method"
KEY_PARAMS = "params"
KEY_ID = "id"
KEY_RESULT = "result"
KEY_ERROR = "error"
KEY_ERROR_CODE = "code"
KEY_ERROR_MESSAGE = "message"
KEY_ERROR_DATA = "data"

# Normalized error response shape for callers (used by connection/tools)
KEY_STATUS = "status"
KEY_ERROR_PLAIN = "error"

JSONRPC_VERSION = "2.0"


def build_request(method: str, params: dict[str, Any]) -> bytes:
    """
    Build a JSON-RPC 2.0 request (Send protocol).

    Payload: { "jsonrpc": "2.0", "method": command_name, "params": params, "id": <uuid> }

    Args:
        method: Command name (e.g. "Actor_get_actors_in_level").
        params: Parameters object (any).

    Returns:
        UTF-8 encoded JSON bytes to send.
    """
    request = {
        KEY_JSONRPC: JSONRPC_VERSION,
        KEY_METHOD: method,
        KEY_PARAMS: params,
        KEY_ID: uuid.uuid4().hex,
    }
    return json.dumps(request).encode("utf-8")


def parse_response(raw: bytes) -> dict[str, Any]:
    """
    Parse a JSON-RPC 2.0 response (Receive protocol) and normalize for callers.

    Success Receive: { "jsonrpc": "2.0", "result": <result>, "id": <uuid> }
      -> returns the "result" payload (dict or wrapped in {"result": ...} if not dict).

    Failure Receive: { "jsonrpc": "2.0", "error": { "code", "message", "data" }, "id": <uuid> }
      -> returns {"status": "error", "error": "<message>", "code": ..., "data": ...}.

    Args:
        raw: UTF-8 encoded JSON response bytes.

    Returns:
        Normalized dict: result payload or error dict with status/error/code/data.

    Raises:
        json.JSONDecodeError: If raw is not valid JSON.
        ValueError: If response has neither "result" nor "error" (invalid JSON-RPC).
    """
    data = json.loads(raw.decode("utf-8"))

    if KEY_ERROR in data:
        err = data[KEY_ERROR]
        if isinstance(err, dict):
            message = err.get(KEY_ERROR_MESSAGE) or str(err.get(KEY_ERROR_CODE, "")) or str(err)
            code = err.get(KEY_ERROR_CODE)
            additional = err.get(KEY_ERROR_DATA)
            out = {KEY_STATUS: "error", KEY_ERROR_PLAIN: message}
            if code is not None:
                out["code"] = code
            if additional is not None:
                out[KEY_ERROR_DATA] = additional
            logger.debug("JSON-RPC error response: code=%s message=%s", code, message)
            return out
        message = str(err)
        logger.debug("JSON-RPC error response: %s", message)
        return {KEY_STATUS: "error", KEY_ERROR_PLAIN: message}

    if KEY_RESULT in data:
        result = data[KEY_RESULT]
        return result if isinstance(result, dict) else {"result": result}

    raise ValueError(
        f"Invalid JSON-RPC response: missing both '{KEY_RESULT}' and '{KEY_ERROR}'"
    )
