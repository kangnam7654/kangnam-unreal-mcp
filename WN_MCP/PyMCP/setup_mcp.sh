#!/usr/bin/env bash
# Unreal MCP Server Setup Script (uv)

# Install uv if missing
if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="${HOME}/.local/bin:${PATH}"
fi

# Create venv
uv venv .venv
source .venv/bin/activate

# Install dependencies (pyproject.toml)
uv sync

# Create .env from example or with defaults
if [ ! -f .env ]; then
  [ -f .env.example ] && cp .env.example .env || {
    echo "# Unreal MCP Server"
    echo "UNREAL_HOST=127.0.0.1"
    echo "UNREAL_PORT=55557"
  } > .env
  echo "Created .env — edit as needed."
fi

PYDIR="$(cd "$(dirname "$0")" && pwd)"
MCP_EXAMPLE="mcp.json.example"
cat > "$MCP_EXAMPLE" << EOF
{
  "mcpServers": {
    "unrealMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "$PYDIR",
        "run",
        "python",
        "main.py"
      ]
    }
  }
}
EOF
echo "Saved example config to $MCP_EXAMPLE. Copy the entry to ~/.cursor/mcp.json as needed."

echo "Done. Run: source .venv/bin/activate && uv run python main.py"