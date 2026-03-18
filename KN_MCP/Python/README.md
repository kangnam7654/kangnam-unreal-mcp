# KN_MCP Python MCP Server

FastMCP-based Python server that bridges AI agents to Unreal Engine via stdio + TCP.

## Setup

```bash
# Install uv if not already installed
# https://docs.astral.sh/uv/

# Setup
cp settings.ini.example settings.ini
uv venv .venv
uv sync
```

## Run

```bash
uv run python main.py
```

Or configure your MCP client to launch it automatically (see root README).

## Configuration

Edit `settings.ini`:

```ini
[Logging]
log_level = INFO

[UE_Connection]
ue_host = 127.0.0.1
ue_port = 27777
```

Or use environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `UNREAL_HOST` | `127.0.0.1` | UE TCP server host |
| `UNREAL_PORT` | `27777` | UE TCP server port |
| `UNREAL_CONNECT_TIMEOUT` | `10` | Connection timeout (seconds) |
| `UNREAL_RECV_TIMEOUT` | `30` | Receive timeout (seconds) |
| `UNREAL_LARGE_OP_TIMEOUT` | `300` | Large operation timeout (seconds) |

## Package Structure

```
kn_mcp/
├── server.py          # FastMCP app factory + lifespan
├── config.py          # Settings from env/ini
├── connection.py      # UnrealConnection (retry, reconnect)
├── params.py          # MCP request parameter context
├── core/
│   ├── protocol.py    # JSON-RPC 2.0 layer
│   └── schemas.py     # Agent-chain result builders
├── tools/
│   ├── general.py     # UE status, connection check
│   ├── agent.py       # Notifications, questions
│   ├── logging.py     # Log level control
│   ├── simple_commands.py  # SimpleCommand auto-registration
│   ├── user_tools.py  # Dynamic tool discovery from UE
│   └── ue/            # Built-in UE tools
├── helpers/           # Utilities
└── prompts.py         # MCP prompts (agent guides)
```
