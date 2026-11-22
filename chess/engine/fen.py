"""FEN (Forsyth-Edwards Notation) import and export."""

from __future__ import annotations

from chess.engine.board import Board, parse_square, square, square_name, square_rank
from chess.engine.movegen import is_square_attacked
from chess.engine.pieces import Color, Piece, PieceType

START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_CASTLING_CHARS = "KQkq"


def _validate_position(board: Board, fen: str) -> None:
    """Reject impossible positions with a clear ValueError.

    Each side must have exactly one king, no pawn may sit on the first or
    last rank, and the side that is NOT to move may not be in check.
    """
    king_counts = {Color.WHITE: 0, Color.BLACK: 0}
    for sq, piece in enumerate(board.squares):
        if piece is None:
            continue
        if piece.type is PieceType.KING:
            king_counts[piece.color] += 1
        elif piece.type is PieceType.PAWN and square_rank(sq) in (0, 7):
            raise ValueError(
                f"pawn on back rank {square_name(sq)}: {fen!r}"
            )
    for color, count in king_counts.items():
        if count != 1:
            raise ValueError(
                f"{color.value} must have exactly one king, got {count}: {fen!r}"
            )
    # The side that just moved (not to move) may not be left in check.
    idle = board.turn.opposite
    if is_square_attacked(board, board.king_square(idle), board.turn):
        raise ValueError(
            f"{idle.value} king is in check but it is {board.turn.value}'s move: {fen!r}"
        )


def board_from_fen(fen: str) -> Board:
    """Parse a FEN string into a Board. Raises ValueError on malformed input."""
    parts = fen.split()
    if len(parts) != 6:
        raise ValueError(f"FEN must have 6 fields, got {len(parts)}: {fen!r}")
    placement, side, castling, ep, halfmove, fullmove = parts

    board = Board()
    board.squares = [None] * 64
    ranks = placement.split("/")
    if len(ranks) != 8:
        raise ValueError(f"FEN placement must have 8 ranks: {placement!r}")
    for row, rank_str in enumerate(ranks):
        rank = 7 - row
        file = 0
        for ch in rank_str:
            if ch.isdigit():
                file += int(ch)
            else:
                if file > 7:
                    raise ValueError(f"FEN rank overflows 8 squares: {rank_str!r}")
                board.squares[square(file, rank)] = Piece.from_symbol(ch)
                file += 1
        if file != 8:
            raise ValueError(f"FEN rank must span exactly 8 squares: {rank_str!r}")

    if side == "w":
        board.turn = Color.WHITE
    elif side == "b":
        board.turn = Color.BLACK
    else:
        raise ValueError(f"FEN side to move must be 'w' or 'b': {side!r}")

    if castling == "-":
        board.castling = set()
    else:
        if any(ch not in _CASTLING_CHARS for ch in castling):
            raise ValueError(f"invalid FEN castling field: {castling!r}")
        board.castling = set(castling)

    board.ep_square = None if ep == "-" else parse_square(ep)

    try:
        board.halfmove_clock = int(halfmove)
        board.fullmove_number = int(fullmove)
    except ValueError as exc:
        raise ValueError(f"FEN counters must be integers: {halfmove!r} {fullmove!r}") from exc
    if board.halfmove_clock < 0 or board.fullmove_number < 1:
        raise ValueError(f"FEN counters out of range: {halfmove!r} {fullmove!r}")
    _validate_position(board, fen)
    return board


def board_to_fen(board: Board) -> str:
    """Serialize a Board to its FEN string."""
    rows = []
    for rank in range(7, -1, -1):
        row = ""
        empty = 0
        for f in range(8):
            piece = board.squares[square(f, rank)]
            if piece is None:
                empty += 1
            else:
                if empty:
                    row += str(empty)
                    empty = 0
                row += piece.symbol
        if empty:
            row += str(empty)
        rows.append(row)
    placement = "/".join(rows)
    side = "w" if board.turn is Color.WHITE else "b"
    castling = "".join(ch for ch in _CASTLING_CHARS if ch in board.castling) or "-"
    ep = "-" if board.ep_square is None else square_name(board.ep_square)
    return (
        f"{placement} {side} {castling} {ep} "
        f"{board.halfmove_clock} {board.fullmove_number}"
    )
