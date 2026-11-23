"""Named computer levels (V8): each level = a search depth + a random margin.

The computer picks uniformly at random among the root moves whose score is
within ``margin`` centipawns of the best one. The top level ("expert") has
margin 0, so it is deterministic and always finds a mate in 1. The RNG is
injectable for deterministic tests.
"""

from __future__ import annotations

import random

from chess.ai.search import _INF, _ordered_moves, negamax
from chess.engine.board import Board
from chess.engine.move import Move
from chess.engine.movegen import apply_move

# key -> (French label, indicative Elo, depth, margin in centipawns)
LEVELS: dict[str, dict] = {
    "debutant": {"label": "Débutant", "elo": 600, "depth": 1, "margin": 300},
    "novice": {"label": "Novice", "elo": 900, "depth": 2, "margin": 150},
    "club": {"label": "Club", "elo": 1200, "depth": 2, "margin": 80},
    "confirme": {"label": "Confirmé", "elo": 1500, "depth": 3, "margin": 40},
    "expert": {"label": "Expert", "elo": 1800, "depth": 4, "margin": 0},
}


def root_scores(board: Board, depth: int) -> list[tuple[Move, int, int]]:
    """``[(move, score for side to move, nodes)]`` for every legal root move."""
    out: list[tuple[Move, int, int]] = []
    for move in _ordered_moves(board):
        child_score, child_nodes = negamax(apply_move(board, move), depth - 1, -_INF, _INF)
        out.append((move, -child_score, 1 + child_nodes))
    return out


def level_move(
    board: Board, level: str, rng: random.Random | None = None
) -> tuple[Move, int, int, dict]:
    """Play one move at the given level.

    Returns ``(move, score, nodes, level_info)``. Raises ValueError for an
    unknown level or when there is no legal move.
    """
    if level not in LEVELS:
        raise ValueError(
            f"unknown level {level!r}; choose from {sorted(LEVELS)}"
        )
    info = LEVELS[level]
    scores = root_scores(board, info["depth"])
    if not scores:
        raise ValueError("no legal move available")
    best_score = max(s for _m, s, _n in scores)
    margin = info["margin"]
    candidates = [(m, s, n) for m, s, n in scores if best_score - s <= margin]
    if rng is not None and len(candidates) > 1:
        move, score, nodes = rng.choice(candidates)
    else:
        move, score, nodes = max(candidates, key=lambda t: t[1])
    return move, score, nodes, info
