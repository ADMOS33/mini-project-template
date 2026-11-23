"""MCP tools exposed by the chess server.

Every tool returns a MCP tool result::

    {"content": [{"type": "text", "text": "<JSON payload>"}], "isError": bool}

The payload is always a JSON document so agents can parse it. An illegal
move (or an invalid argument that changes the game) returns ``isError: true``
with the list of legal moves in the payload.

All tools share the same persisted state file as the CLI and the HTTP API
(``CHESS_STATE_FILE`` env var, default ``.chess_game.json``), so a game played
through MCP is followed live by the web UI.
"""

from __future__ import annotations

import json
import time

from chess.ai.search import best_move
from chess.engine.game import Game, next_version
from chess.engine.move import Move
from chess.engine.pgn import export_pgn
from chess.engine.san import move_to_san, san_to_move
from chess.mcp import STATE_FILE

_DEPTH_SCHEMA = {
    "type": "integer",
    "minimum": 1,
    "maximum": 6,
    "default": 3,
    "description": "minimax search depth (1-6)",
}

TOOLS: list[dict] = [
    {
        "name": "new_game",
        "description": "Start a new game (initial position) in the shared state file.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_board",
        "description": "Current board: FEN, side to move and ASCII rendering.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_status",
        "description": "Game status: turn, in_check, result, winner, version, fen, last_move.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "legal_moves",
        "description": "Legal moves for the side to move, as UCI strings plus SAN details.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "play_move",
        "description": "Play a move given in UCI (e2e4, e7e8q) or SAN (Nf3, O-O). "
        "Illegal move -> isError with the list of legal moves.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "move": {"type": "string", "description": "UCI or SAN notation"}
            },
            "required": ["move"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ai_move",
        "description": "Let the computer (minimax + alpha-beta) play the side to move.",
        "inputSchema": {
            "type": "object",
            "properties": {"depth": _DEPTH_SCHEMA},
            "additionalProperties": False,
        },
    },
    {
        "name": "analyze_position",
        "description": "Best move and evaluation score for the current position, without playing it.",
        "inputSchema": {
            "type": "object",
            "properties": {"depth": _DEPTH_SCHEMA},
            "additionalProperties": False,
        },
    },
    {
        "name": "get_pgn",
        "description": "Export the current game as PGN.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def tool_names() -> set[str]:
    return {t["name"] for t in TOOLS}


def _text(payload: dict, is_error: bool = False) -> dict:
    return {
        "content": [
            {"type": "text", "text": json.dumps(payload, indent=2, ensure_ascii=False)}
        ],
        "isError": is_error,
    }


def _load() -> Game:
    """Current persisted game, or a fresh game if no state file exists yet."""
    if not STATE_FILE.exists():
        return Game()
    return Game.load(STATE_FILE)


def _legal_details(game: Game) -> list[dict]:
    return [
        {"uci": m.to_uci(), "san": move_to_san(game.board, m)}
        for m in sorted(game.legal_moves(), key=lambda m: m.to_uci())
    ]


def _resolve_move(game: Game, text: str) -> Move:
    """Resolve a UCI or SAN string to a legal Move.

    Raises ValueError (mentioning the legal moves) if the move is illegal or
    the game is over.
    """
    status = game.status()
    if status["result"] != "ongoing":
        raise ValueError(f"game is over ({status['result']})")
    try:
        candidate = Move.from_uci(text)
    except ValueError:
        candidate = None
    if candidate is None:
        try:
            candidate = san_to_move(game.board, text)
        except ValueError:
            legal = " ".join(sorted(m.to_uci() for m in game.legal_moves()))
            raise ValueError(
                f"illegal move {text!r} (neither UCI nor SAN); legal moves: {legal}"
            ) from None
    legal = {m.to_uci(): m for m in game.legal_moves()}
    if candidate.to_uci() not in legal:
        raise ValueError(
            f"illegal move {candidate.to_uci()!r}; legal moves: {' '.join(sorted(legal))}"
        )
    return legal[candidate.to_uci()]


def _depth(arguments: dict) -> int:
    depth = arguments.get("depth", 3)
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise ValueError(f"depth must be an integer, got {depth!r}")
    if not 1 <= depth <= 6:
        raise ValueError(f"depth must be between 1 and 6, got {depth}")
    return depth


def call_tool(name: str, arguments: dict) -> dict:
    """Execute one tool and return its MCP tool result."""
    if name == "new_game":
        game = Game()
        game.version = next_version(STATE_FILE)
        game.save(STATE_FILE)
        return _text({"ok": True, "status": game.status()})

    if name == "get_board":
        game = _load()
        return _text(
            {
                "fen": game.status()["fen"],
                "turn": str(game.board.turn),
                "ascii": game.board.ascii(),
            }
        )

    if name == "get_status":
        game = _load()
        status = game.status()
        status["last_move"] = game.moves[-1].to_uci() if game.moves else None
        return _text(status)

    if name == "legal_moves":
        game = _load()
        details = _legal_details(game)
        return _text({"moves": [d["uci"] for d in details], "details": details})

    if name == "play_move":
        move_text = arguments.get("move")
        if not isinstance(move_text, str) or not move_text.strip():
            raise ValueError("play_move expects a non-empty 'move' string")
        game = _load()
        try:
            move = _resolve_move(game, move_text.strip())
            san = move_to_san(game.board, move)  # SAN from the pre-move position
            game.play_uci(move.to_uci())
        except ValueError as exc:
            return _text(
                {
                    "error": str(exc),
                    "legal_moves": sorted(m.to_uci() for m in game.legal_moves()),
                },
                is_error=True,
            )
        game.save(STATE_FILE)
        return _text(
            {"ok": True, "move": move.to_uci(), "san": san, "status": game.status()}
        )

    if name in ("ai_move", "analyze_position"):
        depth = _depth(arguments)
        game = _load()
        status = game.status()
        if status["result"] != "ongoing":
            return _text(
                {"error": f"game is over ({status['result']})", "status": status},
                is_error=True,
            )
        start = time.perf_counter()
        move, score, nodes = best_move(game.board, depth)
        time_ms = round((time.perf_counter() - start) * 1000, 1)
        payload = {
            "best_move": move.to_uci(),
            "san": move_to_san(game.board, move),
            "score": score,
            "nodes": nodes,
            "time_ms": time_ms,
            "depth": depth,
        }
        if name == "ai_move":
            game.play_uci(move.to_uci())
            game.save(STATE_FILE)
            payload = {"ok": True, "move": move.to_uci(), "status": game.status(), **payload}
        else:
            payload = {"ok": True, "status": status, **payload}
        return _text(payload)

    if name == "get_pgn":
        game = _load()
        return _text({"pgn": export_pgn(game)})

    raise ValueError(f"unknown tool: {name!r}")
