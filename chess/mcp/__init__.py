"""Hand-rolled MCP server for the chess project (no extra dependency).

JSON-RPC 2.0 over stdio: one JSON message per line on stdin/stdout, logs on
stderr only. Entry point: ``python -m chess.mcp``.

The server shares the same persisted state file as the CLI and the HTTP API
(default ``.chess_game.json``, override with the ``CHESS_STATE_FILE`` env
var), so a game played through MCP is followed live by the web UI (V5).
"""

import os
from pathlib import Path

STATE_FILE = Path(os.environ.get("CHESS_STATE_FILE", ".chess_game.json"))
