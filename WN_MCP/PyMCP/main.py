"""
Unreal Engine MCP Server entry point.
Config is loaded, connection is created in server lifespan, tools are registered by category.
When UE connects, user tool directories (from get_user_tool_directories) are registered automatically.
"""
import logging
import sys
from pathlib import Path

# Ensure project root and src are on path for "unreal_mcp" and "helpers"
_root = Path(__file__).resolve().parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))
if str(_root / "src") not in sys.path:
    sys.path.insert(0, str(_root / "src"))

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
    handlers=[logging.FileHandler(_root / "unreal_engine_mcp.log"), logging.StreamHandler()],
)
logger = logging.getLogger("UnrealEngineMCP")

from unreal_mcp.config import load_config
from unreal_mcp.server import create_app

config = load_config()
mcp = create_app(config)

if __name__ == "__main__":
    logger.info("Starting Unreal Engine MCP server with stdio transport")
    mcp.run(transport="stdio")
