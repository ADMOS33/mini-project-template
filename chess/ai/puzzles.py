"""Puzzle mode (V7): a database of engine-verified mate-in-n problems.

Each entry: ``{"fen", "solution" (UCI), "level" (1|2|3 = mate in n), "theme"}``.
``tests/test_puzzles.py`` re-verifies with the engine that the solution mates
in ``level`` AND is the only first move that does — an entry that fails is
removed from the database.

``load_puzzle`` / ``solve_move`` implement the game logic shared by the CLI,
the HTTP API and the MCP server.
"""

from __future__ import annotations

import random

from chess.ai.evaluation import MATE_SCORE
from chess.ai.mate import best_defense, is_checkmate
from chess.ai.search import _INF, negamax
from chess.engine.fen import board_from_fen
from chess.engine.game import Game
from chess.engine.move import Move
from chess.engine.movegen import apply_move
from chess.engine.san import move_to_san, san_to_move

# Engine-verified (tests/test_puzzles.py): solution is the UNIQUE mate in n.
PUZZLES: list[dict] = [
    {"fen": '6Q1/8/8/8/1N5k/5K2/8/8 w - - 0 1', "solution": 'g8g4', "level": 1, "theme": 'Mat à la dame'},
    {"fen": 'R7/7k/8/6K1/8/4R3/8/8 w - - 0 1', "solution": 'e3e7', "level": 1, "theme": 'Mat à la tour'},
    {"fen": '8/8/8/8/8/8/2K3Q1/k7 w - - 0 1', "solution": 'g2a8', "level": 1, "theme": 'Mat à la dame'},
    {"fen": '8/8/8/K1k5/3r4/8/8/7r b - - 0 1', "solution": 'h1a1', "level": 1, "theme": 'Mat à la tour'},
    {"fen": '1K6/8/2k1r3/8/8/8/8/r7 b - - 0 1', "solution": 'e6e8', "level": 1, "theme": 'Mat à la tour'},
    {"fen": '7K/4b3/7k/8/5r2/8/8/8 b - - 0 1', "solution": 'f4f8', "level": 1, "theme": 'Mat à la tour'},
    {"fen": '8/8/2q5/8/8/b4k2/8/4K3 b - - 0 1', "solution": 'c6c1', "level": 1, "theme": 'Mat à la dame'},
    {"fen": '6K1/q7/7k/8/8/7b/8/8 b - - 0 1', "solution": 'a7g7', "level": 1, "theme": 'Mat à la dame'},
    {"fen": '8/8/7K/5k2/8/5r2/1b6/8 b - - 0 1', "solution": 'f3h3', "level": 1, "theme": 'Mat à la tour'},
    {"fen": '8/8/8/1q6/8/5b2/8/2k1K3 b - - 0 1', "solution": 'b5e2', "level": 1, "theme": 'Mat à la dame'},
    {"fen": '8/Q7/8/8/8/5P1k/5K2/8 w - - 0 1', "solution": 'a7h7', "level": 1, "theme": 'Mat à la dame'},
    {"fen": '5k2/R7/6K1/8/8/8/4R3/8 w - - 0 1', "solution": 'a7a8', "level": 1, "theme": 'Mat à la tour'},
    {"fen": '8/8/8/6Q1/8/8/k1K5/7R w - - 0 1', "solution": 'g5a5', "level": 2, "theme": 'Mat à la dame'},
    {"fen": '8/7Q/8/8/8/3K4/8/3k4 w - - 0 1', "solution": 'h7h1', "level": 2, "theme": 'Mat à la dame'},
    {"fen": '7k/8/6K1/R5R1/8/8/8/8 w - - 0 1', "solution": 'a5a8', "level": 2, "theme": 'Mat à la tour'},
    {"fen": '8/5k1K/8/8/8/8/8/2q5 b - - 0 1', "solution": 'c1h1', "level": 2, "theme": 'Mat à la dame'},
    {"fen": '8/7r/8/8/8/q7/8/1K1k4 b - - 0 1', "solution": 'h7b7', "level": 2, "theme": 'Mat à la tour'},
    {"fen": '7K/8/7k/4Q3/8/8/8/3R4 w - - 0 1', "solution": 'd1d6', "level": 2, "theme": 'Mat à la tour'},
    {"fen": '2K1k3/2Q5/7R/8/8/8/8/8 w - - 0 1', "solution": 'h6h8', "level": 2, "theme": 'Mat à la tour'},
    {"fen": '8/8/8/Q7/8/8/5K2/7k w - - 0 1', "solution": 'a5h5', "level": 2, "theme": 'Mat à la dame'},
    {"fen": '8/8/8/6R1/4Q3/2K5/k7/8 w - - 0 1', "solution": 'g5a5', "level": 2, "theme": 'Mat à la tour'},
    {"fen": '8/6QR/8/8/8/k1K5/8/8 w - - 0 1', "solution": 'g7a7', "level": 2, "theme": 'Mat à la dame'},
    {"fen": '1n6/7K/5k2/6q1/8/8/8/8 b - - 0 1', "solution": 'g5g7', "level": 2, "theme": 'Mat à la dame'},
    {"fen": 'k1K5/8/3r4/8/8/7r/8/8 b - - 0 1', "solution": 'h3c3', "level": 2, "theme": 'Mat à la tour'},
    {"fen": '7r/8/8/8/8/6r1/8/3k1K2 b - - 0 1', "solution": 'h8f8', "level": 3, "theme": 'Mat à la tour'},
    {"fen": '8/8/2K5/8/k7/1R6/3R4/8 w - - 0 1', "solution": 'd2b2', "level": 3, "theme": 'Mat à la tour'},
    {"fen": '1k6/3K3B/8/7B/8/8/5Q2/8 w - - 0 1', "solution": 'f2b6', "level": 3, "theme": 'Mat à la dame'},
    {"fen": '8/5k2/b6K/8/8/1q6/8/1b6 b - - 0 1', "solution": 'f7f6', "level": 3, "theme": 'Mat aidé'},
    {"fen": '3R4/8/8/5R2/8/3K4/8/1k6 w - - 0 1', "solution": 'd8b8', "level": 3, "theme": 'Mat à la tour'},
    {"fen": '2K5/8/1q2k3/8/8/8/8/8 b - - 0 1', "solution": 'b6a7', "level": 3, "theme": 'Mat à la dame'},
    {"fen": '8/8/8/8/k7/8/2K5/6Q1 w - - 0 1', "solution": 'g1b6', "level": 3, "theme": 'Mat à la dame'},
    {"fen": '2K1k3/8/8/2Q5/8/5B2/1B6/8 w - - 0 1', "solution": 'f3h5', "level": 3, "theme": 'Mat du fou'},
]


def puzzles_by_level(level: int) -> list[dict]:
    return [p for p in PUZZLES if p["level"] == level]


def get_puzzle(level: int, index: int | None = None, seed: int | None = None) -> dict:
    """Pick a puzzle of the given level (deterministic with index or seed)."""
    pool = puzzles_by_level(level)
    if not pool:
        raise ValueError(f"no puzzle of level {level} in the database")
    if index is not None:
        if not 0 <= index < len(pool):
            raise ValueError(f"index {index} out of range (0..{len(pool) - 1})")
        return dict(pool[index])
    rng = random.Random(seed)
    return dict(rng.choice(pool))


def load_puzzle(game: Game, puzzle: dict) -> None:
    """Load a puzzle position into ``game`` (in place, not saved by caller)."""
    from chess.engine.fen import board_from_fen as _bff

    game.board = _bff(puzzle["fen"])
    game.moves = []
    game._positions = [puzzle["fen"]]
    game.external_result = None
    game.meta["puzzle"] = {
        "level": puzzle["level"],
        "n": puzzle["level"],
        "solution": puzzle["solution"],
        "theme": puzzle["theme"],
        "fen": puzzle["fen"],
        "ply": 0,  # solver moves played so far
        "solved": False,
    }
    game.version += 1


def _resolve(game: Game, text: str) -> Move:
    """UCI or SAN -> legal Move, ValueError (with legal list) otherwise."""
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


def solve_move(game: Game, text: str, defense_depth: int = 4) -> dict:
    """Play one solver move in the current puzzle.

    - First solver move must be the solution.
    - Later solver moves are accepted iff they keep a forced mate (in the
      remaining moves); then the computer plays the best defense.

    Returns a JSON-serializable dict; raises ValueError on a rejected move.
    """
    meta = game.meta.get("puzzle")
    if meta is None:
        raise ValueError("no puzzle loaded — load one first (puzzle tool/command)")
    status = game.status()
    if status["result"] != "ongoing":
        raise ValueError(f"puzzle is already over ({status['result']})")
    n = meta["n"]
    ply = meta["ply"]
    move = _resolve(game, text.strip())
    san = move_to_san(game.board, move)

    if ply == 0 and move.to_uci() != meta["solution"]:
        legal = " ".join(sorted(m.to_uci() for m in game.legal_moves()))
        raise ValueError(
            f"first move must be the solution; legal moves: {legal}"
        )
    child = apply_move(game.board, move)
    remaining = n - (ply + 1)
    if is_checkmate(child):
        forced = True
    elif remaining >= 1:
        # Opponent to move in `child`: forced mate in `remaining` solver moves
        # <=> opponent's negamax score is <= -MATE_SCORE at depth 2*remaining.
        score, _nodes = negamax(child, 2 * remaining, -_INF, _INF)
        forced = score <= -MATE_SCORE
    else:
        forced = False
    if not forced:
        legal = " ".join(sorted(m.to_uci() for m in game.legal_moves()))
        raise ValueError(
            f"move {move.to_uci()} ({san}) does not keep a forced mate in {remaining + 1}; "
            f"legal moves: {legal}"
        )

    game.play_uci(move.to_uci())
    meta["ply"] = ply + 1
    reply_uci: str | None = None
    if not is_checkmate(game.board):
        reply = best_defense(game.board, max_n=max(1, remaining) + 1)
        game.play_uci(reply.to_uci())
        reply_uci = reply.to_uci()
    if is_checkmate(game.board):
        meta["solved"] = True
    game.version += 1  # meta change
    return {
        "ok": True,
        "accepted": True,
        "move": move.to_uci(),
        "san": san,
        "reply": reply_uci,
        "puzzle": {
            "level": meta["level"],
            "n": meta["n"],
            "theme": meta["theme"],
            "ply": meta["ply"],
            "remaining": max(0, n - meta["ply"]),
            "solved": meta["solved"],
        },
        "status": game.status(),
    }
