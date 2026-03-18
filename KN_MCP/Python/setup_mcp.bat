@echo off
REM Unreal MCP Server Setup Script (uv)
cd /d "%~dp0"

REM Install uv if missing
where uv >nul 2>nul || (
  powershell -NoProfile -ExecutionPolicy Bypass -c "irm https://astral.sh/uv/install.ps1 | iex"
  set "PATH=%USERPROFILE%\.local\bin;%PATH%"
)

REM Create venv
uv venv .venv
call .venv\Scripts\activate.bat

REM Install dependencies (pyproject.toml)
uv sync

REM Create .env from example or with defaults
if not exist .env (
  if exist .env.example (
    copy .env.example .env
  ) else (
    echo # Unreal MCP Server> .env
    echo UNREAL_HOST=127.0.0.1>> .env
    echo UNREAL_PORT=27777>> .env
  )
  echo Created .env - edit as needed.
)

set "PYDIR=%CD%"
set "PYDIR_JSON=%PYDIR:\=\\%"
(
echo {
echo   "mcpServers": {
echo     "unrealMCP": {
echo       "command": "uv",
echo       "args": [
echo         "--directory",
echo         "%PYDIR_JSON%",
echo         "run",
echo         "python",
echo         "main.py"
echo       ]
echo     }
echo   }
echo }
) > mcp.json.example
echo Saved example config to mcp.json.example. Copy the entry to %%USERPROFILE%%\.cursor\mcp.json as needed.

echo Done. Run: .venv\Scripts\activate then uv run python main.py
pause