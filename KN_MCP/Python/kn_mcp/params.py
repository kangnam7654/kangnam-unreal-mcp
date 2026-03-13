"""
MCP Parameters storage and access.

Thread-safe storage for MCP request parameters using Python's ContextVar.
Tools can access agent-provided parameters without explicit passing.

Usage:
    from kn_mcp.params import get_mcp_params, enable_mcp_params_capture

    # At server startup (once):
    mcp = FastMCP(...)
    enable_mcp_params_capture(mcp)

    # Inside any tool:
    def my_tool():
        params = get_mcp_params()
        user_input = params.get('user_input', '')
"""
import inspect
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from typing import Any

_current_mcp_params: ContextVar[dict[str, Any]] = ContextVar("mcp_params", default={})


def get_mcp_params() -> dict[str, Any]:
    """Get the current MCP request parameters set by the tool wrapper."""
    return _current_mcp_params.get()


def _set_mcp_params(params: dict[str, Any]) -> None:
    """Internal: Set the current MCP request parameters."""
    _current_mcp_params.set(params)


def enable_mcp_params_capture(mcp: Any) -> None:
    """Enable automatic parameter capture for all @mcp.tool decorated functions.

    Call this ONCE right after creating the FastMCP instance.
    After this, every tool will automatically capture its arguments in get_mcp_params().
    """
    original_tool_decorator = mcp.tool

    _options_param = inspect.Parameter(
        "options",
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        default=None,
        annotation=dict[str, Any] | None,
    )
    _options_sig = inspect.Signature(parameters=[_options_param])

    def mcp_tool_with_params_capture(func: Callable) -> Callable:
        orig_sig = inspect.signature(func)
        has_params = len(orig_sig.parameters) > 0

        if inspect.iscoroutinefunction(func):
            if not has_params:
                @wraps(func)
                async def async_wrapper_noparams(options: dict[str, Any] | None = None):
                    _set_mcp_params(options or {})
                    return await func()

                del async_wrapper_noparams.__wrapped__
                async_wrapper_noparams.__signature__ = _options_sig
                async_wrapper_noparams.__annotations__ = {"options": dict[str, Any] | None}
                original_tool_decorator(async_wrapper_noparams)
                return async_wrapper_noparams
            else:
                @wraps(func)
                async def async_wrapper_withparams(*args: Any, **kwargs: Any):
                    _set_mcp_params(kwargs)
                    filtered = {k: v for k, v in kwargs.items() if k in orig_sig.parameters}
                    return await func(**filtered)

                async_wrapper_withparams.__signature__ = orig_sig
                original_tool_decorator(async_wrapper_withparams)
                return async_wrapper_withparams
        else:
            if not has_params:
                @wraps(func)
                def sync_wrapper_noparams(options: dict[str, Any] | None = None):
                    _set_mcp_params(options or {})
                    return func()

                del sync_wrapper_noparams.__wrapped__
                sync_wrapper_noparams.__signature__ = _options_sig
                sync_wrapper_noparams.__annotations__ = {"options": dict[str, Any] | None}
                original_tool_decorator(sync_wrapper_noparams)
                return sync_wrapper_noparams
            else:
                @wraps(func)
                def sync_wrapper_withparams(*args: Any, **kwargs: Any):
                    _set_mcp_params(kwargs)
                    filtered = {k: v for k, v in kwargs.items() if k in orig_sig.parameters}
                    return func(**filtered)

                sync_wrapper_withparams.__signature__ = orig_sig
                original_tool_decorator(sync_wrapper_withparams)
                return sync_wrapper_withparams

    mcp.tool = mcp_tool_with_params_capture
