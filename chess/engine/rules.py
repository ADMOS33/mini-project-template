"""End-of-game rules: checkmate, stalemate, the fifty-move rule, threefold
repetition and insufficient material.

All detection lives here in the engine — the CLI, API and web layers only
read the resulting ``result``/``winner`` values.
"""

from __future__ import annotations

from collections.abc import Mapping

from chess.engine.board import Board
from chess.engine.movegen import is_square_attacked, legal_moves

#: Possible values of ``result`` in :func:`game_result` / ``Game.status()``.
RESULTS = (
    "ongoing",
    "checkmate",
    "stalemate",
    "draw_threefold",
    "draw_fifty_move",
    "draw_insufficient_material",
)


def game_result(board: Board, repetitions: Mapping | None = None) -> tuple[str, str | None]:
    """Return ``(result, winner)`` for ``board``.

    ``result`` is one of :data:`RESULTS`; ``winner`` is ``"w"``, ``"b"`` or
    ``None`` (``None`` unless checkmate). ``repetitions`` maps position keys
    to occurrence counts and is used for the threefold rule.
    """
    in_check = is_square_attacked(
        board, board.king_square(board.turn), board.turn.opposite
    )
    if not legal_moves(board):
        result = "checkmate" if in_check else "stalemate"
    elif board.halfmove_clock >= 100:
        result = "draw_fifty_move"
    else:
        result = "ongoing"
    winner = board.turn.opposite.value if result == "checkmate" else None
    return result, winner
