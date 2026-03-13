"""
MCP-UE-Agent-Chain-Case-Study result/error schemas.

Defines status values, result field names, error codes, and helpers for building
or validating payloads that conform to the Case Study (run_required, follow_up_required,
accepted/completed, error shape). Wire format is handled by protocol (JSON-RPC 2.0).
"""
from typing import Any, Dict, Optional

from unreal_mcp.core.protocol import (
    KEY_ERROR_CODE,
    KEY_ERROR_DATA,
    KEY_ERROR_MESSAGE,
    KEY_STATUS,
)

# --- Case Study 」3, 」13: allowed status values (result.status) ---
STATUS_RUN_REQUIRED = "run_required"
STATUS_ACCEPTED = "accepted"
STATUS_COMPLETED = "completed"
STATUS_RUNNING = "running"
STATUS_FOLLOW_UP_REQUIRED = "follow_up_required"
STATUS_FAILED = "failed"

# --- Case Study 」3: fixed result fields for chain execution ---
RESULT_FIELD_COMMAND = "command"
RESULT_FIELD_PARAMS = "params"
RESULT_FIELD_THEN_METHOD = "then_method"
RESULT_FIELD_THEN_PARAMS = "then_params"
RESULT_FIELD_REQUEST_ID = "request_id"
RESULT_FIELD_MESSAGE = "message"
RESULT_FIELD_DATA = "data"
RESULT_FIELD_PROGRESS = "progress"

# --- Case Study 」6: standard error codes ---
ERROR_INVALID_PARAMS = -32602
ERROR_SERVER_EXECUTION = -32000
ERROR_INTERNAL = -32603


# --- Result payload builders (Case 2, 3, 」7) ---


def build_result_run_required(
    command: str,
    params: Dict[str, Any],
    message: str = "",
) -> Dict[str, Any]:
    """
    Build result payload for Case 2 (run_required). Agent must run command then report via result tool.

    Required: result.command, result.params. Optional: result.message.
    """
    out: Dict[str, Any] = {
        KEY_STATUS: STATUS_RUN_REQUIRED,
        RESULT_FIELD_COMMAND: command,
        RESULT_FIELD_PARAMS: params,
    }
    if message:
        out[RESULT_FIELD_MESSAGE] = message
    return out


def build_result_follow_up_required(
    then_method: str,
    then_params: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build result payload for follow-up chain. Agent must call then_method with then_params.
    """
    return {
        KEY_STATUS: STATUS_FOLLOW_UP_REQUIRED,
        RESULT_FIELD_THEN_METHOD: then_method,
        RESULT_FIELD_THEN_PARAMS: then_params,
    }


def build_result_accepted(
    request_id: str,
    message: str = "",
) -> Dict[str, Any]:
    """Build result payload for Case 3 (accepted). Agent may poll get_task_result(request_id)."""
    out: Dict[str, Any] = {
        KEY_STATUS: STATUS_ACCEPTED,
        RESULT_FIELD_REQUEST_ID: request_id,
    }
    if message:
        out[RESULT_FIELD_MESSAGE] = message
    return out


def build_result_completed(
    request_id: str,
    data: Dict[str, Any],
) -> Dict[str, Any]:
    """Build result payload for Case 3 (completed)."""
    return {
        KEY_STATUS: STATUS_COMPLETED,
        RESULT_FIELD_REQUEST_ID: request_id,
        RESULT_FIELD_DATA: data,
    }


def build_result_running(
    request_id: str,
    progress: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build result payload for Case 3 (still running)."""
    out: Dict[str, Any] = {
        KEY_STATUS: STATUS_RUNNING,
        RESULT_FIELD_REQUEST_ID: request_id,
    }
    if progress is not None:
        out[RESULT_FIELD_PROGRESS] = progress
    return out


def build_error(
    code: int,
    message: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build JSON-RPC 2.0 error object (for the "error" key). Case Study 」6.

    Standard codes: ERROR_INVALID_PARAMS (-32602), ERROR_SERVER_EXECUTION (-32000), ERROR_INTERNAL (-32603).
    """
    out: Dict[str, Any] = {
        KEY_ERROR_CODE: code,
        KEY_ERROR_MESSAGE: message,
    }
    if data is not None:
        out[KEY_ERROR_DATA] = data
    return out


# --- Validation helpers ---


def is_run_required_result(result: Dict[str, Any]) -> bool:
    """True if result indicates agent must run command then report (Case 2)."""
    return result.get(KEY_STATUS) == STATUS_RUN_REQUIRED


def is_follow_up_required_result(result: Dict[str, Any]) -> bool:
    """True if result indicates agent must call then_method with then_params."""
    return result.get(KEY_STATUS) == STATUS_FOLLOW_UP_REQUIRED


def validate_run_required_result(result: Dict[str, Any]) -> Optional[str]:
    """
    Validate result has required fields for run_required. Returns None if valid, else error message.
    """
    if result.get(KEY_STATUS) != STATUS_RUN_REQUIRED:
        return None
    if RESULT_FIELD_COMMAND not in result:
        return "run_required result missing 'command'"
    if RESULT_FIELD_PARAMS not in result:
        return "run_required result missing 'params'"
    return None


def validate_follow_up_required_result(result: Dict[str, Any]) -> Optional[str]:
    """
    Validate result has required fields for follow_up_required. Returns None if valid, else error message.
    """
    if result.get(KEY_STATUS) != STATUS_FOLLOW_UP_REQUIRED:
        return None
    if RESULT_FIELD_THEN_METHOD not in result:
        return "follow_up_required result missing 'then_method'"
    if RESULT_FIELD_THEN_PARAMS not in result:
        return "follow_up_required result missing 'then_params'"
    return None
