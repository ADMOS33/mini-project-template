"""End-of-game rules: checkmate, stalemate, the fifty-move rule, threefold
repetition and insufficient material.

All detection lives here in the engine — the CLI, API and web layers only
read the resulting ``result``/``winner`` values.
"""

from __future__ import annotations

from collections.abc import Mapping

from chess.engine.board import Board, square, square_file, square_rank
from chess.engine.fen import board_to_fen
from chess.engine.movegen import is_square_attacked, legal_moves
from chess.engine.pieces import Color, Piece, PieceType

#: Possible values of ``result`` in :func:`game_result` / ``Game.status()``.
#: "flag" is never returned by game_result: it is set externally (clock fall).
RESULTS = (
    "ongoing",
    "checkmate",
    "stalemate",
    "draw_threefold",
    "draw_fifty_move",
    "draw_insufficient_material",
    "flag",
)


def _ep_capture_playable(board: Board) -> bool:
    """True if a pawn of the side to move can actually capture en passant."""
    if board.ep_square is None:
        return False
    f, r = square_file(board.ep_square), square_rank(board.ep_square)
    forward = 1 if board.turn is Color.WHITE else -1
    pawn_rank = r - forward
    if not 0 <= pawn_rank < 8:
        return False
    pawn = Piece(PieceType.PAWN, board.turn)
    for df in (-1, 1):
        pf = f + df
        if 0 <= pf < 8 and board.squares[square(pf, pawn_rank)] == pawn:
            return True
    return False


def position_key(board: Board) -> tuple[str, str, str, int | None]:
    """Repetition key of a position: piece placement, side to move, castling
    rights, and the en-passant square only when a capture on it is actually
    playable. Move counters are deliberately ignored."""
    placement = board_to_fen(board).split()[0]
    ep = board.ep_square if _ep_capture_playable(board) else None
    castling = "".join(ch for ch in "KQkq" if ch in board.castling) or "-"
    return (placement, str(board.turn), castling, ep)


def insufficient_material(board: Board) -> bool:
    """True when neither side can possibly checkmate (automatic draw):
    K vs K, K + single minor (B or N) vs K, or K+B vs K+B with both bishops
    on the same color complex."""
    minors = [
        (sq, piece)
        for sq, piece in enumerate(board.squares)
        if piece is not None and piece.type is not PieceType.KING
    ]
    if any(piece.type not in (PieceType.BISHOP, PieceType.KNIGHT) for _, piece in minors):
        return False  # a pawn, rook or queen is on the board
    if len(minors) <= 1:
        return True  # K-K, KB-K or KN-K
    if (
        len(minors) == 2
        and all(piece.type is PieceType.BISHOP for _, piece in minors)
        and {piece.color for _, piece in minors} == {Color.WHITE, Color.BLACK}
        and len({(square_file(sq) + square_rank(sq)) % 2 for sq, _ in minors}) == 1
    ):
        return True  # KB vs KB, bishops on the same color complex
    return False


def game_result(board: Board, repetitions: Mapping | None = None) -> tuple[str, str | None]:
    """Return ``(result, winner)`` for ``board``.

    ``result`` is one of :data:`RESULTS`; ``winner`` is ``"w"``, ``"b"`` or
    ``None`` (``None`` unless checkmate). ``repetitions`` maps position keys
    (see :func:`position_key`) to occurrence counts, for the threefold rule.
    """
    in_check = is_square_attacked(
        board, board.king_square(board.turn), board.turn.opposite
    )
    if not legal_moves(board):
        result = "checkmate" if in_check else "stalemate"
    elif repetitions is not None and repetitions.get(position_key(board), 0) >= 3:
        result = "draw_threefold"
    elif board.halfmove_clock >= 100:
        result = "draw_fifty_move"
    elif insufficient_material(board):
        result = "draw_insufficient_material"
    else:
        result = "ongoing"
    winner = board.turn.opposite.value if result == "checkmate" else None
    return result, winner
