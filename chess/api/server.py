"""FastAPI server: JSON API under ``/api/*`` plus the web UI served at ``/``.

Run from the project root:

    uvicorn chess.api.server:app --reload --host 127.0.0.1 --port 8000

- Web UI:      http://localhost:8000/
- Swagger UI:  http://localhost:8000/docs
- API status:  http://localhost:8000/api/status

The game state is persisted in ``.chess_game.json`` (override with the
``CHESS_STATE_FILE`` env var), shared with the CLI when both run from the
same directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from chess.api.schemas import LoadRequest, MoveRequest
from chess.engine.board import square_name
from chess.engine.fen import board_to_fen
from chess.engine.game import Game

STATE_FILE = Path(os.environ.get("CHESS_STATE_FILE", ".chess_game.json"))
WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="Chess API", version="0.1.0")


def _load() -> Game:
    """Current persisted game, or a fresh game if none exists yet."""
    if STATE_FILE.exists():
        try:
            return Game.load(STATE_FILE)
        except (ValueError, KeyError):
            pass
    return Game()


def _save(game: Game) -> None:
    game.save(STATE_FILE)


@app.get("/api/status")
def get_status() -> dict:
    """Game status: side to move, check, result, FEN and last move (UCI)."""
    game = _load()
    status = game.status()
    status["last_move"] = game.moves[-1].to_uci() if game.moves else None
    return status


@app.get("/api/board")
def get_board() -> dict:
    """Board as FEN, ASCII rendering and per-square symbols/glyphs."""
    board = _load().board
    return {
        "fen": board_to_fen(board),
        "turn": str(board.turn),
        "ascii": board.ascii(),
        "squares": {
            square_name(sq): (piece.symbol if piece else None)
            for sq, piece in enumerate(board.squares)
        },
        "glyphs": {
            square_name(sq): piece.glyph
            for sq, piece in enumerate(board.squares)
            if piece is not None
        },
    }


@app.get("/api/moves")
def get_moves() -> dict:
    """Legal moves for the side to move, in UCI notation."""
    return {"moves": sorted(m.to_uci() for m in _load().legal_moves())}


@app.get("/api/fen")
def get_fen() -> dict:
    """FEN of the current position."""
    return {"fen": board_to_fen(_load().board)}


@app.post("/api/new")
def post_new() -> dict:
    """Start a new game (resets the persisted state)."""
    game = Game()
    _save(game)
    return {"ok": True, "status": game.status()}


@app.post("/api/move")
def post_move(req: MoveRequest) -> dict:
    """Play a UCI move. 400 with the list of legal moves if illegal."""
    game = _load()
    try:
        move = game.play_uci(req.move)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _save(game)
    return {"ok": True, "move": move.to_uci(), "status": game.status()}


@app.post("/api/load")
def post_load(req: LoadRequest) -> dict:
    """Load a position from a FEN string."""
    try:
        game = Game.from_fen(req.fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"invalid FEN: {exc}") from exc
    _save(game)
    return {"ok": True, "status": game.status()}


@app.post("/api/undo")
def post_undo() -> dict:
    """Take back the last move."""
    game = _load()
    move = game.undo()
    if move is None:
        raise HTTPException(status_code=400, detail="no moves to undo")
    _save(game)
    return {"ok": True, "undone": move.to_uci(), "status": game.status()}


# Serve the web UI last so the /api/* routes above take precedence.
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
