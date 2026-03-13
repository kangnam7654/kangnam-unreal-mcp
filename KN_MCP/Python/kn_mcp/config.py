"""
Configuration for Unreal MCP Server.
Loads from environment variables with defaults.
"""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Unreal connection and server settings."""
    unreal_host: str
    unreal_port: int
    connect_timeout: int
    default_recv_timeout: int
    large_op_recv_timeout: int
    enabled_tools: list[str]  # e.g. ["actors", "blueprints", "building", ...]


def load_config() -> Settings:
    """Load settings from environment with defaults."""
    return Settings(
        unreal_host=os.environ.get("UNREAL_HOST", "127.0.0.1"),
        unreal_port=int(os.environ.get("UNREAL_PORT", "27777")),
        connect_timeout=int(os.environ.get("UNREAL_CONNECT_TIMEOUT", "10")),
        default_recv_timeout=int(os.environ.get("UNREAL_RECV_TIMEOUT", "30")),
        large_op_recv_timeout=int(os.environ.get("UNREAL_LARGE_OP_TIMEOUT", "300")),
        enabled_tools=_parse_enabled_tools(os.environ.get("UNREAL_ENABLED_TOOLS", "")),
    )


def _parse_enabled_tools(value: str) -> list[str]:
    """Parse comma-separated list; empty means all enabled."""
    if not value or not value.strip():
        return []
    return [s.strip() for s in value.split(",") if s.strip()]
