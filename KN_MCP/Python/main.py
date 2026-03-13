"""
Unreal Engine MCP Server entry point.
Config is loaded, connection is created in server lifespan, tools are registered by category.
When UE connects, user tool directories (from get_user_tool_directories) are registered automatically.
"""
import logging
import sys
from pathlib import Path

# Ensure project root is on path for "kn_mcp" package
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

logger = logging.getLogger("UnrealEngineMCP")

from kn_mcp.config import load_config
from kn_mcp.server import create_app

config = load_config()
mcp = create_app(config)

if __name__ == "__main__":
    import atexit

    _file_handler = logging.FileHandler(_root / "unreal_engine_mcp.log")
    atexit.register(_file_handler.close)
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        handlers=[_file_handler, logging.StreamHandler()],
    )
    logger.info("Starting Unreal Engine MCP server with stdio transport")
    mcp.run(transport="stdio")
