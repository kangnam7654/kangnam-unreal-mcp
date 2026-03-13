"""
Agent-Chain result/error schemas.

Defines status values, result field names, error codes, and helpers for building
or validating payloads that conform to the Agent-Chain Case Study
(run_required, follow_up_required, accepted/completed, error shape).
Wire format is handled by protocol (JSON-RPC 2.0).

C++ counterpart: KN_MCP_CREATE_RESULT_* macros in KN_MCP_CommandGroup.h
"""
from typing import Any

from kn_mcp.core.protocol import (
    KEY_ERROR_CODE,
    KEY_ERROR_DATA,
    KEY_ERROR_MESSAGE,
    KEY_STATUS,
)

# --- Allowed status values (result.status) ---
STATUS_RUN_REQUIRED = "run_required"
STATUS_ACCEPTED = "accepted"
STATUS_COMPLETED = "completed"
STATUS_RUNNING = "running"
STATUS_FOLLOW_UP_REQUIRED = "follow_up_required"
STATUS_FAILED = "failed"

# --- Fixed result fields for chain execution ---
RESULT_FIELD_COMMAND = "command"
RESULT_FIELD_PARAMS = "params"
RESULT_FIELD_THEN_METHOD = "then_method"
RESULT_FIELD_THEN_PARAMS = "then_params"
RESULT_FIELD_REQUEST_ID = "request_id"
RESULT_FIELD_MESSAGE = "message"
RESULT_FIELD_DATA = "data"
RESULT_FIELD_PROGRESS = "progress"

# --- Standard error codes ---
ERROR_INVALID_PARAMS = -32602
ERROR_SERVER_EXECUTION = -32000
ERROR_INTERNAL = -32603


# --- Result payload builders ---


def build_result_run_required(
    command: str,
    params: dict[str, Any],
    message: str = "",
) -> dict[str, Any]:
    """Build result payload for run_required.

    Agent must run command then report via result tool.
    """
    out: dict[str, Any] = {
        KEY_STATUS: STATUS_RUN_REQUIRED,
        RESULT_FIELD_COMMAND: command,
        RESULT_FIELD_PARAMS: params,
    }
    if message:
        out[RESULT_FIELD_MESSAGE] = message
    return out


def build_result_follow_up_required(
    then_method: str,
    then_params: dict[str, Any],
) -> dict[str, Any]:
    """Build result payload for follow_up_required.

    Agent must call then_method with then_params.
    """
    return {
        KEY_STATUS: STATUS_FOLLOW_UP_REQUIRED,
        RESULT_FIELD_THEN_METHOD: then_method,
        RESULT_FIELD_THEN_PARAMS: then_params,
    }


def build_result_accepted(
    request_id: str,
    message: str = "",
) -> dict[str, Any]:
    """Build result payload for accepted. Agent may poll get_task_result(request_id)."""
    out: dict[str, Any] = {
        KEY_STATUS: STATUS_ACCEPTED,
        RESULT_FIELD_REQUEST_ID: request_id,
    }
    if message:
        out[RESULT_FIELD_MESSAGE] = message
    return out


def build_result_completed(
    request_id: str,
    data: dict[str, Any],
) -> dict[str, Any]:
    """Build result payload for completed."""
    return {
        KEY_STATUS: STATUS_COMPLETED,
        RESULT_FIELD_REQUEST_ID: request_id,
        RESULT_FIELD_DATA: data,
    }


def build_result_running(
    request_id: str,
    progress: Any | None = None,
) -> dict[str, Any]:
    """Build result payload for running (still in progress)."""
    out: dict[str, Any] = {
        KEY_STATUS: STATUS_RUNNING,
        RESULT_FIELD_REQUEST_ID: request_id,
    }
    if progress is not None:
        out[RESULT_FIELD_PROGRESS] = progress
    return out


def build_error(
    code: int,
    message: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build JSON-RPC 2.0 error object (for the "error" key).

    Standard codes: ERROR_INVALID_PARAMS (-32602), ERROR_SERVER_EXECUTION (-32000),
    ERROR_INTERNAL (-32603).
    """
    out: dict[str, Any] = {
        KEY_ERROR_CODE: code,
        KEY_ERROR_MESSAGE: message,
    }
    if data is not None:
        out[KEY_ERROR_DATA] = data
    return out


# --- Validation helpers ---


def is_run_required_result(result: dict[str, Any]) -> bool:
    """True if result indicates agent must run command then report."""
    return result.get(KEY_STATUS) == STATUS_RUN_REQUIRED


def is_follow_up_required_result(result: dict[str, Any]) -> bool:
    """True if result indicates agent must call then_method with then_params."""
    return result.get(KEY_STATUS) == STATUS_FOLLOW_UP_REQUIRED


def validate_run_required_result(result: dict[str, Any]) -> str | None:
    """Validate run_required result has required fields. Returns None if valid, else error."""
    if result.get(KEY_STATUS) != STATUS_RUN_REQUIRED:
        return None
    if RESULT_FIELD_COMMAND not in result:
        return "run_required result missing 'command'"
    if RESULT_FIELD_PARAMS not in result:
        return "run_required result missing 'params'"
    return None


def validate_follow_up_required_result(result: dict[str, Any]) -> str | None:
    """Validate follow_up_required result has required fields. Returns None if valid, else error."""
    if result.get(KEY_STATUS) != STATUS_FOLLOW_UP_REQUIRED:
        return None
    if RESULT_FIELD_THEN_METHOD not in result:
        return "follow_up_required result missing 'then_method'"
    if RESULT_FIELD_THEN_PARAMS not in result:
        return "follow_up_required result missing 'then_params'"
    return None
