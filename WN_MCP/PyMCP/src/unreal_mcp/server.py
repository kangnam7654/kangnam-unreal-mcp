"""
MCP server: FastMCP app with lifespan and tool registration.
Connection is created in lifespan and set globally so tools/helpers can use get_unreal_connection().
"""
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict, Optional

from mcp.server.fastmcp import FastMCP

from unreal_mcp.config import Settings, load_config
from unreal_mcp.connection import UnrealConnection, get_unreal_connection, set_current_connection
from unreal_mcp.tools import (
    agent, 
    general, 
    logging as logging_tools, 
    user_tools
)
from unreal_mcp.tools.ue import (
    actors,
    blueprints,
    blueprints_graph,
    materials,
)
from unreal_mcp.prompts import register_prompts

logger = logging.getLogger("UnrealMCP.Server")


def _lifespan(settings: Settings):
    @asynccontextmanager
    async def _inner(server: FastMCP) -> AsyncIterator[Dict[str, Any]]:
        logger.info("Unreal Engine MCP WemadeNext server starting up")
        conn = UnrealConnection(
            host=settings.unreal_host,
            port=settings.unreal_port,
            connect_timeout=settings.connect_timeout,
            default_recv_timeout=settings.default_recv_timeout,
            large_op_recv_timeout=settings.large_op_recv_timeout,
        )
        set_current_connection(conn)
        try:
            # Register user tool directories from UE
            if conn.connect():
                logger.info("Unreal connected; registering user tool directories from UE...")
                try:
                    register_user_tool_directories(server)
                except Exception as e:
                    logger.error("Error registering user tool directories from UE: %s", e)
            else:
                logger.info("Unreal not connected; skipping user tool directories registration")
            yield {}
        
        finally:
            set_current_connection(None)
            conn.disconnect()
            logger.info("Unreal Engine MCP WemadeNext server shut down")

    return _inner


def create_app(settings: Optional[Settings] = None) -> FastMCP:
    """Create FastMCP app with lifespan and all tools registered."""
    settings = settings or load_config()
    mcp = FastMCP("UnrealMCP_WemadeNext", lifespan=_lifespan(settings))
    get_conn = get_unreal_connection

    enabled = set(settings.enabled_tools) if settings.enabled_tools else None

    def register_if_enabled(name: str, register_fn):
        if enabled is None or name in enabled:
            register_fn(mcp, get_conn)

    # Register general tools (UE status, connection check, reconnect)
    register_if_enabled("general", general.register_tools)
    # Register agent tools (notifications, questions, confirmations)
    register_if_enabled("agent", agent.register_tools)
    # Register logging tools (set_log_level, persisted to settings.ini)
    register_if_enabled("logging", logging_tools.register_tools)

    # Register Unreal Engine Command tools
    # TODO: Dynamically register tools based on the enabled tools and local plugin paths
    register_if_enabled("actors", actors.register_tools)
    register_if_enabled("blueprints", blueprints.register_tools)
    register_if_enabled("blueprints_graph", blueprints_graph.register_tools)
    register_if_enabled("materials", materials.register_tools)

    # Register prompts
    # TODO: Dynamically register prompts based on the enabled tools and local plugin paths
    register_prompts(mcp)

    # Register Resources
    # TODO: Dynamically register resources based on the enabled tools and local plugin paths

    return mcp
