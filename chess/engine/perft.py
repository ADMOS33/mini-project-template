"""Perft (performance test): count leaf nodes of the move-generation tree.

``perft(board, depth)`` returns the number of positions reachable in exactly
``depth`` plies; ``divide(board, depth)`` breaks that count down per root move.
Reference values on standard positions live in ``tests/test_perft.py``.
"""

from __future__ import annotations

from chess.engine.board import Board
from chess.engine.movegen import apply_move, legal_moves


def perft(board: Board, depth: int) -> int:
    """Number of leaf nodes at exactly ``depth`` plies from ``board``."""
    if depth < 0:
        raise ValueError(f"depth must be >= 0, got {depth}")
    if depth == 0:
        return 1
    moves = legal_moves(board)
    if depth == 1:
        return len(moves)
    total = 0
    for move in moves:
        total += perft(apply_move(board, move), depth - 1)
    return total


def divide(board: Board, depth: int) -> dict[str, int]:
    """Per-root-move node counts at ``depth``: ``{uci: perft(child, depth-1)}``."""
    if depth < 1:
        raise ValueError(f"depth must be >= 1, got {depth}")
    result: dict[str, int] = {}
    for move in legal_moves(board):
        result[move.to_uci()] = perft(apply_move(board, move), depth - 1)
    return result
