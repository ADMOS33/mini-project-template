"""Static position evaluation: material + piece-square tables.

Scores are in centipawns from the **side to move's** point of view
(positive = the side to move is better). Piece-square tables are indexed
like Board.squares (0 = a1 ... 63 = h8) and given here rank 1 first;
Black's squares are mirrored vertically (``sq ^ 56``). Mate scores
(±MATE_SCORE, adjusted by remaining depth) are produced by the search.
"""

from __future__ import annotations

from chess.engine.board import Board
from chess.engine.pieces import Color, PieceType

#: Mate score in centipawns; the search adds/subtracts the remaining depth
#: so that faster mates score higher.
MATE_SCORE = 100_000

VALUES = {
    PieceType.PAWN: 100,
    PieceType.KNIGHT: 320,
    PieceType.BISHOP: 330,
    PieceType.ROOK: 500,
    PieceType.QUEEN: 900,
    PieceType.KING: 0,
}


def _t(rows: list[list[int]]) -> list[int]:
    """Flatten 8 rows given rank 1 first into a 64-entry table (a1 = 0)."""
    return [v for row in rows for v in row]


PAWN_PSQT = _t([
    [0, 0, 0, 0, 0, 0, 0, 0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5, 5, 10, 25, 25, 10, 5, 5],
    [0, 0, 0, 20, 20, 0, 0, 0],
    [5, -5, -10, 0, 0, -10, -5, 5],
    [5, 10, 10, -20, -20, 10, 10, 5],
    [0, 0, 0, 0, 0, 0, 0, 0],
])

KNIGHT_PSQT = _t([
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50],
])

BISHOP_PSQT = _t([
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20],
])

ROOK_PSQT = _t([
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0],
])

QUEEN_PSQT = _t([
    [-20, -10, -10, -5, -5, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 5, 5, 5, 0, -10],
    [-5, 0, 5, 5, 5, 5, 0, -5],
    [0, 0, 5, 5, 5, 5, 0, -5],
    [-10, 5, 5, 5, 5, 5, 0, -10],
    [-10, 0, 5, 0, 0, 0, 0, -10],
    [-20, -10, -10, -5, -5, -10, -10, -20],
])

KING_PSQT = _t([
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [20, 20, 0, 0, 0, 0, 20, 20],
    [20, 30, 10, 0, 0, 10, 30, 20],
])

PSQT = {
    PieceType.PAWN: PAWN_PSQT,
    PieceType.KNIGHT: KNIGHT_PSQT,
    PieceType.BISHOP: BISHOP_PSQT,
    PieceType.ROOK: ROOK_PSQT,
    PieceType.QUEEN: QUEEN_PSQT,
    PieceType.KING: KING_PSQT,
}


def evaluate(board: Board) -> int:
    """Static evaluation in centipawns, from the side to move's perspective."""
    score = 0
    for sq, piece in enumerate(board.squares):
        if piece is None:
            continue
        if piece.color is board.turn:
            # Own piece: table as-is (tables are written for White).
            score += VALUES[piece.type] + PSQT[piece.type][
                sq if piece.color is Color.WHITE else sq ^ 56
            ]
        else:
            # Opponent piece: mirror the square vertically (rank flip).
            score -= VALUES[piece.type] + PSQT[piece.type][
                sq if piece.color is Color.WHITE else sq ^ 56
            ]
    return score
