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
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles

from chess.ai.evaluation import evaluate
from chess.ai.search import best_move
from chess.api.schemas import (
    AiMoveRequest,
    AnalyzeRequest,
    FlagRequest,
    LoadRequest,
    MoveRequest,
    OfferDrawRequest,
    PgnRequest,
    PuzzleRequest,
    SolveRequest,
)
from chess.engine.board import square_name
from chess.engine.fen import board_from_fen, board_to_fen
from chess.engine.game import Game, next_version
from chess.engine.pgn import export_pgn, import_pgn
from chess.engine.san import move_to_san

STATE_FILE = Path(os.environ.get("CHESS_STATE_FILE", ".chess_game.json"))
WEB_DIR = Path(__file__).resolve().parents[2] / "web"

app = FastAPI(title="Chess API", version="0.1.0")


def _load() -> Game:
    """Current persisted game, or a fresh game if no state file exists yet.

    A corrupted state file (invalid JSON, wrong shape, inconsistent history,
    unreadable file) raises HTTPException 500 with a clear message — it must
    NOT silently start a new game.
    """
    if not STATE_FILE.exists():
        return Game()
    try:
        return Game.load(STATE_FILE)
    except Exception as exc:  # JSONDecodeError included (subclass of ValueError)
        raise HTTPException(
            status_code=500,
            detail=f"corrupted game state in {STATE_FILE}: {exc}",
        ) from exc


def _save(game: Game) -> None:
    game.save(STATE_FILE)


@app.get("/api/status")
def get_status() -> dict:
    """Game status: side to move, check, result, FEN, last move, opening (V9)."""
    from chess.engine.openings import lookup_opening

    game = _load()
    status = game.status()
    status["last_move"] = game.moves[-1].to_uci() if game.moves else None
    status["opening"] = lookup_opening([m.to_uci() for m in game.moves])
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
    game.version = next_version(STATE_FILE)
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
    game.version = next_version(STATE_FILE)
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


@app.post("/api/flag")
def post_flag(req: FlagRequest) -> dict:
    """Record a flag fall: the given color loses on time (result "flag")."""
    game = _load()
    if game.status()["result"] != "ongoing":
        raise HTTPException(status_code=400, detail="game is over")
    winner = "b" if req.color == "w" else "w"
    game.set_external_result("flag", winner)
    _save(game)
    return {"ok": True, "status": game.status()}


@app.get("/api/history")
def get_history() -> dict:
    """Move history: one entry per ply with UCI, SAN and resulting FEN."""
    game = _load()
    fens = game.position_fens()
    entries = [{"ply": 0, "uci": None, "san": None, "fen": fens[0]}]
    for i, move in enumerate(game.moves):
        entries.append(
            {
                "ply": i + 1,
                "uci": move.to_uci(),
                "san": move_to_san(board_from_fen(fens[i]), move),
                "fen": fens[i + 1],
            }
        )
    return {"entries": entries, "result": game.status()["result"]}


@app.get("/api/pgn")
def get_pgn() -> dict:
    """Current game exported as PGN (Seven Tag Roster + SAN movetext)."""
    return {"pgn": export_pgn(_load())}


@app.post("/api/load-pgn")
def post_load_pgn(req: PgnRequest) -> dict:
    """Load a game from a PGN string. 400 naming the move number if invalid."""
    try:
        game = import_pgn(req.pgn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    game.version = next_version(STATE_FILE)
    _save(game)
    return {
        "ok": True,
        "moves": [m.to_uci() for m in game.moves],
        "status": game.status(),
    }


@app.get("/api/eval")
def get_eval() -> dict:
    """Static evaluation in centipawns, from the side to move's perspective."""
    game = _load()
    return {
        "score": evaluate(game.board),
        "turn": str(game.board.turn),
        "fen": board_to_fen(game.board),
    }


@app.post("/api/ai-move")
def post_ai_move(req: AiMoveRequest) -> dict:
    """Let the computer (minimax + alpha-beta) play the side to move.

    Accepts either a numeric ``depth`` or a named ``level`` (V8: depth + random
    margin among near-best moves).
    """
    from chess.ai.levels import LEVELS, level_move

    game = _load()
    if game.status()["result"] != "ongoing":
        raise HTTPException(status_code=400, detail="game is over")
    start = time.perf_counter()
    level = None
    if req.level is not None:
        if req.level not in LEVELS:
            raise HTTPException(
                status_code=400,
                detail=f"unknown level {req.level!r}; choose from {sorted(LEVELS)}",
            )
        move, score, nodes, info = level_move(game.board, req.level)
        depth = info["depth"]
        level = req.level
    else:
        depth = max(1, min(req.depth, 6))
        move, score, nodes = best_move(game.board, depth)
    time_ms = round((time.perf_counter() - start) * 1000, 1)
    san = move_to_san(game.board, move)
    game.play_uci(move.to_uci())
    _save(game)
    return {
        "ok": True,
        "move": move.to_uci(),
        "san": san,
        "score": score,
        "nodes": nodes,
        "time_ms": time_ms,
        "depth": depth,
        "level": level,
        "status": game.status(),
    }


@app.post("/api/resign")
def post_resign() -> dict:
    """The side to move resigns; the other side wins ("resignation")."""
    game = _load()
    if game.status()["result"] != "ongoing":
        raise HTTPException(status_code=400, detail="game is over")
    game.resign()
    _save(game)
    return {"ok": True, "status": game.status()}


@app.post("/api/offer-draw")
def post_offer_draw(req: OfferDrawRequest | None = None) -> dict:
    """Offer a draw. ``force=True`` records it immediately (2-player mode);
    otherwise the computer (side not to move) accepts only if its own
    evaluation is <= 0 (see README "Décisions")."""
    game = _load()
    if game.status()["result"] != "ongoing":
        raise HTTPException(status_code=400, detail="game is over")
    force = req is not None and req.force
    if not force:
        from chess.ai.evaluation import evaluate

        score_white = evaluate(game.board)  # white perspective, centipawns
        computer = game.board.turn.opposite.value
        comp_score = score_white if computer == "w" else -score_white
        if comp_score > 0:
            return {"ok": True, "accepted": False, "status": game.status()}
    game.offer_draw()
    _save(game)
    return {"ok": True, "accepted": True, "status": game.status()}


@app.post("/api/takeback")
def post_takeback() -> dict:
    """Take back the last two plies (my move + the computer's answer)."""
    game = _load()
    undone = []
    for _ in range(2):
        move = game.undo()
        if move is None:
            break
        undone.append(move.to_uci())
    if not undone:
        raise HTTPException(status_code=400, detail="no moves to undo")
    _save(game)
    return {"ok": True, "undone": undone, "status": game.status()}


@app.post("/api/puzzle")
def post_puzzle(req: PuzzleRequest) -> dict:
    """Load a mate-in-n puzzle (V7) into the shared state. The response
    includes the solution so the web UI can offer a "Solution" button."""
    from chess.ai.puzzles import get_puzzle, load_puzzle

    try:
        puzzle = get_puzzle(req.level, req.index, req.seed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    game = _load()
    game.version = next_version(STATE_FILE)
    load_puzzle(game, puzzle)
    _save(game)
    meta = game.meta["puzzle"]
    return {
        "ok": True,
        "puzzle": {
            "level": meta["level"],
            "n": meta["n"],
            "theme": meta["theme"],
            "turn": game.status()["turn"],
            "fen": meta["fen"],
            "solution": meta["solution"],
        },
        "status": game.status(),
    }


@app.post("/api/solve")
def post_solve(req: SolveRequest) -> dict:
    """Play one solver move in the current puzzle (V7); the computer answers
    with the best defense. 400 if the move is rejected."""
    from chess.ai.puzzles import solve_move

    game = _load()
    if game.meta.get("puzzle") is None:
        raise HTTPException(status_code=400, detail="no puzzle loaded — POST /api/puzzle first")
    try:
        result = solve_move(game, req.move)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _save(game)
    return result


@app.post("/api/analyze")
def post_analyze(req: AnalyzeRequest) -> dict:
    """Game review (V9): per-ply evaluation, centipawn loss and label."""
    from chess.ai.analysis import analyze_game

    game = _load()
    return analyze_game(game, req.depth)


class NoCacheStaticFiles(StaticFiles):
    """Static files served with ``Cache-Control: no-cache`` so a browser
    reload never shows a stale version of the web UI."""

    async def get_response(self, path: str, scope) -> Response:
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


# Serve the web UI last so the /api/* routes above take precedence.
app.mount("/", NoCacheStaticFiles(directory=WEB_DIR, html=True), name="web")
