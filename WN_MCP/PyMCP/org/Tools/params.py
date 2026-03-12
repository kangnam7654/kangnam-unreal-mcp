"""
MCP Parameters storage and access.

This module provides thread-safe storage for MCP request parameters
using Python's ContextVar for async/threaded environments.
"""

from contextvars import ContextVar
from typing import Dict, Any, Optional
from functools import wraps
import inspect

# ============================================================================
# MCP PARAMETERS CONTEXT (Thread-safe storage of current request params)
# ============================================================================
_current_mcp_params: ContextVar[Dict[str, Any]] = ContextVar('mcp_params', default={})


def get_mcp_params() -> Dict[str, Any]:
    """Get the current MCP request parameters set by the tool wrapper.
    
    Returns:
        dict: Parameters passed to the MCP tool by the Agent
        
    Example:
        def my_tool():
            params = get_mcp_params()
            user_input = params.get('user_input', '')
            # Use params...
    """
    return _current_mcp_params.get()


def _set_mcp_params(params: Dict[str, Any]) -> None:
    """Internal: Set the current MCP request parameters."""
    _current_mcp_params.set(params)


# ============================================================================
# FASTMCP INTEGRATION - Auto-capture tool arguments
# ============================================================================

def enable_mcp_params_capture(mcp) -> None:
    """Enable automatic parameter capture for all @mcp.tool decorated functions.
    
    Call this ONCE right after creating the FastMCP instance:
    
        mcp = FastMCP(...)
        enable_mcp_params_capture(mcp)
    
    After this, every tool will automatically capture its arguments in get_mcp_params().
    
    Args:
        mcp: FastMCP server instance
    """
    original_tool_decorator = mcp.tool
    
    # Signature with single 'options' parameter for parameterless tools
    _options_param = inspect.Parameter(
        'options',
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
        default=None,
        annotation=Optional[Dict[str, Any]]
    )
    _options_sig = inspect.Signature(parameters=[_options_param])

    def mcp_tool_with_params_capture(func):
        orig_sig = inspect.signature(func)
        has_params = len(orig_sig.parameters) > 0
        
        if inspect.iscoroutinefunction(func):
            if not has_params:
                @wraps(func)
                async def async_wrapper_noparams(options: Optional[Dict[str, Any]] = None):
                    _set_mcp_params(options or {})
                    return await func()
                # Override __wrapped__ so inspect.signature() uses our signature (with options)
                # instead of following __wrapped__ back to the original parameterless function
                del async_wrapper_noparams.__wrapped__
                setattr(async_wrapper_noparams, '__signature__', _options_sig)
                async_wrapper_noparams.__annotations__ = {'options': Optional[Dict[str, Any]]}
                original_tool_decorator(async_wrapper_noparams)
                return async_wrapper_noparams
            else:
                @wraps(func)
                async def async_wrapper_withparams(*args, **kwargs):
                    _set_mcp_params(kwargs)
                    filtered = {k: v for k, v in kwargs.items() if k in orig_sig.parameters}
                    return await func(**filtered)
                setattr(async_wrapper_withparams, '__signature__', orig_sig)
                original_tool_decorator(async_wrapper_withparams)
                return async_wrapper_withparams
        else:
            if not has_params:
                @wraps(func)
                def sync_wrapper_noparams(options: Optional[Dict[str, Any]] = None):
                    _set_mcp_params(options or {})
                    return func()
                # Override __wrapped__ so inspect.signature() uses our signature (with options)
                # instead of following __wrapped__ back to the original parameterless function
                del sync_wrapper_noparams.__wrapped__
                setattr(sync_wrapper_noparams, '__signature__', _options_sig)
                sync_wrapper_noparams.__annotations__ = {'options': Optional[Dict[str, Any]]}
                original_tool_decorator(sync_wrapper_noparams)
                return sync_wrapper_noparams
            else:
                @wraps(func)
                def sync_wrapper_withparams(*args, **kwargs):
                    _set_mcp_params(kwargs)
                    filtered = {k: v for k, v in kwargs.items() if k in orig_sig.parameters}
                    return func(**filtered)
                setattr(sync_wrapper_withparams, '__signature__', orig_sig)
                original_tool_decorator(sync_wrapper_withparams)
                return sync_wrapper_withparams
    
    # Replace mcp.tool with our wrapped version
    mcp.tool = mcp_tool_with_params_capture
