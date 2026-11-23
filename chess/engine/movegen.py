"""Move generation: attack detection, pseudo-legal moves, legal moves and
move application.

Basic moves (pawn pushes/double-push/captures/en-passant/promotions, knight,
bishop, rook, queen, king) and castling are fully implemented and filtered
for king safety.
"""

from __future__ import annotations

from chess.engine.board import FILES, Board, square, square_file, square_rank
from chess.engine.move import Move
from chess.engine.pieces import Color, Piece, PieceType

KNIGHT_OFFSETS = ((1, 2), (2, 1), (2, -1), (1, -2), (-1, -2), (-2, -1), (-2, 1), (-1, 2))
KING_OFFSETS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
ROOK_DIRS = ((1, 0), (-1, 0), (0, 1), (0, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
QUEEN_DIRS = ROOK_DIRS + BISHOP_DIRS

def rook_file_for_right(letter: str) -> int:
    """Rook file targeted by a castling-right letter (X-FEN aware).

    Standard letters ``K``/``Q`` (and ``k``/``q``) map to the h/a files;
    Chess960 X-FEN letters are the rook's own file (``A``-``H`` / ``a``-``h``).
    """
    if letter in ("K", "H", "k", "h"):
        return 7
    if letter in ("Q", "A", "q", "a"):
        return 0
    return FILES.index(letter.lower())


def is_castling_move(board: Board, move: Move) -> bool:
    """True if ``move`` is a castling move of the king in ``board``.

    Standard castling is king two files away on its home rank (e1g1/e1c1);
    in Chess960 the king moves onto its own rook's square ("the king takes
    its rook", e.g. f1h1).
    """
    piece = board.piece_at(move.from_sq)
    if piece is None or piece.type is not PieceType.KING:
        return False
    if square_rank(move.from_sq) not in (0, 7):
        return False
    kf = square_file(move.from_sq)
    target = board.piece_at(move.to_sq)
    if (
        target is not None
        and target.type is PieceType.ROOK
        and target.color is piece.color
    ):
        return True
    return abs(square_file(move.to_sq) - kf) == 2


def _on_board(f: int, r: int) -> bool:
    return 0 <= f < 8 and 0 <= r < 8


def is_square_attacked(board: Board, sq: int, by: Color) -> bool:
    """True if square ``sq`` is attacked by at least one piece of color ``by``."""
    f, r = square_file(sq), square_rank(sq)
    pawn_rank = r - 1 if by is Color.WHITE else r + 1
    if 0 <= pawn_rank < 8:
        pawn = Piece(PieceType.PAWN, by)
        for df in (-1, 1):
            pf = f + df
            if 0 <= pf < 8 and board.squares[square(pf, pawn_rank)] == pawn:
                return True
    for df, dr in KNIGHT_OFFSETS:
        nf, nr = f + df, r + dr
        if _on_board(nf, nr) and board.squares[square(nf, nr)] == Piece(PieceType.KNIGHT, by):
            return True
    for df, dr in KING_OFFSETS:
        nf, nr = f + df, r + dr
        if _on_board(nf, nr) and board.squares[square(nf, nr)] == Piece(PieceType.KING, by):
            return True
    for dirs, types in (
        (ROOK_DIRS, (PieceType.ROOK, PieceType.QUEEN)),
        (BISHOP_DIRS, (PieceType.BISHOP, PieceType.QUEEN)),
    ):
        for df, dr in dirs:
            nf, nr = f + df, r + dr
            while _on_board(nf, nr):
                piece = board.squares[square(nf, nr)]
                if piece is not None:
                    if piece.color is by and piece.type in types:
                        return True
                    break
                nf += df
                nr += dr
    return False


def _add_pawn_move(moves: list[Move], from_sq: int, to_sq: int, is_promotion: bool) -> None:
    if is_promotion:
        from chess.engine.move import PROMOTION_TYPES

        for promo in PROMOTION_TYPES:
            moves.append(Move(from_sq, to_sq, promo))
    else:
        moves.append(Move(from_sq, to_sq))


def _pawn_moves(board: Board, sq: int, color: Color, moves: list[Move]) -> None:
    f, r = square_file(sq), square_rank(sq)
    forward = 1 if color is Color.WHITE else -1
    start_rank = 1 if color is Color.WHITE else 6
    promo_rank = 7 if color is Color.WHITE else 0
    one = square(f, r + forward)
    if board.squares[one] is None:
        _add_pawn_move(moves, sq, one, r + forward == promo_rank)
        if r == start_rank:
            two = square(f, r + 2 * forward)
            if board.squares[two] is None:
                moves.append(Move(sq, two))
    for df in (-1, 1):
        tf = f + df
        if 0 <= tf < 8:
            target = square(tf, r + forward)
            target_piece = board.squares[target]
            if target_piece is not None and target_piece.color is not color:
                _add_pawn_move(moves, sq, target, r + forward == promo_rank)
            elif target_piece is None and board.ep_square == target:
                moves.append(Move(sq, target))  # en-passant capture


def _jump_moves(board: Board, sq: int, color: Color, offsets: tuple, moves: list[Move]) -> None:
    f, r = square_file(sq), square_rank(sq)
    for df, dr in offsets:
        nf, nr = f + df, r + dr
        if _on_board(nf, nr):
            target = square(nf, nr)
            piece = board.squares[target]
            if piece is None or piece.color is not color:
                moves.append(Move(sq, target))


def _slide_moves(board: Board, sq: int, color: Color, dirs: tuple, moves: list[Move]) -> None:
    f, r = square_file(sq), square_rank(sq)
    for df, dr in dirs:
        nf, nr = f + df, r + dr
        while _on_board(nf, nr):
            target = square(nf, nr)
            piece = board.squares[target]
            if piece is None:
                moves.append(Move(sq, target))
            else:
                if piece.color is not color:
                    moves.append(Move(sq, target))
                break
            nf += df
            nr += dr


def _castling_moves(board: Board, sq: int, color: Color, moves: list[Move]) -> None:
    """Castling moves for a king on its home rank, with every condition checked:
    right present, rook on the file named by the right, all squares between king
    and rook (plus both destination squares) empty, king not in check and never
    crossing or landing on an attacked square.

    The king always lands on the g/c file and the rook on the f/d file. In the
    standard position (king e1/e8, rook a/h) the move is rendered e1g1/e1c1;
    in Chess960 it is "the king takes its rook" (king square -> rook square).
    """
    rank = 0 if color is Color.WHITE else 7
    if square_rank(sq) != rank:
        return
    enemy = color.opposite
    kf = square_file(sq)
    if is_square_attacked(board, sq, enemy):
        return  # may not castle out of check
    for right in sorted(board.castling):
        if right.isupper() != (color is Color.WHITE):
            continue
        rf = rook_file_for_right(right)
        if rf == kf:
            continue
        rook_sq = square(rf, rank)
        rook = board.squares[rook_sq]
        if (
            rook is None
            or rook.type is not PieceType.ROOK
            or rook.color is not color
        ):
            continue
        kingside = rf > kf
        king_dest_f = 6 if kingside else 2
        rook_dest_f = 5 if kingside else 3
        king_dest = square(king_dest_f, rank)
        rook_dest = square(rook_dest_f, rank)
        # Every square strictly between the king and the rook must be empty,
        # and so must both destination squares (unless they are the king/rook
        # squares themselves).
        empty = all(
            board.squares[square(f, rank)] is None
            for f in range(min(kf, rf) + 1, max(kf, rf))
        )
        if empty:
            for dest in (king_dest, rook_dest):
                df = square_file(dest)
                if df in (kf, rf):
                    continue
                if board.squares[dest] is not None:
                    empty = False
                    break
        if not empty:
            continue
        # The king may not cross or land on an attacked square.
        step = 1 if king_dest_f > kf else -1
        f = kf
        safe = True
        while True:
            if is_square_attacked(board, square(f, rank), enemy):
                safe = False
                break
            if f == king_dest_f:
                break
            f += step
        if not safe:
            continue
        if kf == 4 and rf == 7:
            moves.append(Move(sq, square(6, rank)))  # e1g1 / e8g8
        elif kf == 4 and rf == 0:
            moves.append(Move(sq, square(2, rank)))  # e1c1 / e8c8
        else:
            moves.append(Move(sq, rook_sq))  # Chess960: king takes its rook


def pseudo_legal_moves(board: Board, color: Color) -> list[Move]:
    """All pseudo-legal moves for ``color`` (king safety not checked)."""
    moves: list[Move] = []
    for sq, piece in enumerate(board.squares):
        if piece is None or piece.color is not color:
            continue
        if piece.type is PieceType.PAWN:
            _pawn_moves(board, sq, color, moves)
        elif piece.type is PieceType.KNIGHT:
            _jump_moves(board, sq, color, KNIGHT_OFFSETS, moves)
        elif piece.type is PieceType.KING:
            _jump_moves(board, sq, color, KING_OFFSETS, moves)
            _castling_moves(board, sq, color, moves)
        elif piece.type is PieceType.BISHOP:
            _slide_moves(board, sq, color, BISHOP_DIRS, moves)
        elif piece.type is PieceType.ROOK:
            _slide_moves(board, sq, color, ROOK_DIRS, moves)
        elif piece.type is PieceType.QUEEN:
            _slide_moves(board, sq, color, QUEEN_DIRS, moves)
    return moves


def apply_move(board: Board, move: Move) -> Board:
    """Apply ``move`` and return the resulting board (input left unchanged).

    Handles captures, promotions, the en-passant square after a double push,
    castling-rights bookkeeping and the move counters. Legality (king safety,
    castling/en-passant rules) is the caller's responsibility.
    """
    new = board.copy()
    piece = new.squares[move.from_sq]
    if piece is None:
        from chess.engine.board import square_name

        raise ValueError(f"no piece on {square_name(move.from_sq)}")
    captured = new.squares[move.to_sq]
    if piece.type is PieceType.KING and is_castling_move(board, move):
        # Castling: the king lands on g/c (standard) or stays/takes its rook
        # (Chess960); the rook lands on f/d. Not a capture for the 50-move rule.
        rank = square_rank(move.from_sq)
        kf = square_file(move.from_sq)
        target = board.squares[move.to_sq]
        if target is not None and target.type is PieceType.ROOK:
            rook_sq = move.to_sq  # Chess960: king takes its rook
        else:
            rook_sq = square(7 if square_file(move.to_sq) > kf else 0, rank)
        rf = square_file(rook_sq)
        kingside = rf > kf
        king_to = square(6 if kingside else 2, rank)
        rook_to = square(5 if kingside else 3, rank)
        rook = new.squares[rook_sq]
        new.squares[king_to] = piece
        new.squares[move.from_sq] = None
        new.squares[rook_to] = rook
        new.squares[rook_sq] = None
        captured = None
    else:
        new.squares[move.to_sq] = (
            Piece(move.promotion, piece.color) if move.promotion is not None else piece
        )
        new.squares[move.from_sq] = None
    if (
        piece.type is PieceType.PAWN
        and captured is None
        and move.to_sq == board.ep_square
        and square_file(move.to_sq) != square_file(move.from_sq)
    ):
        # En passant: the captured pawn disappears from its own square.
        ep_captured = square(square_file(move.to_sq), square_rank(move.from_sq))
        new.squares[ep_captured] = None
    if piece.type is PieceType.KING:
        # A king move discards every castling right of its color.
        if piece.color is Color.WHITE:
            new.castling = {r for r in new.castling if not r.isupper()}
        else:
            new.castling = {r for r in new.castling if not r.islower()}
    # A rook leaving (or being captured on) its home square discards the right
    # tied to that square: the X-FEN file letter, plus K/Q/k/q on the corners.
    for sq in (move.from_sq, move.to_sq):
        f, r = square_file(sq), square_rank(sq)
        if r not in (0, 7):
            continue
        new.castling.discard(FILES[f].upper() if r == 0 else FILES[f])
        if f == 7:
            new.castling.discard("K" if r == 0 else "k")
        elif f == 0:
            new.castling.discard("Q" if r == 0 else "q")
    new.ep_square = None
    if piece.type is PieceType.PAWN and abs(move.to_sq - move.from_sq) == 16:
        new.ep_square = (move.to_sq + move.from_sq) // 2
    if piece.type is PieceType.PAWN or captured is not None:
        new.halfmove_clock = 0
    else:
        new.halfmove_clock += 1
    if board.turn is Color.BLACK:
        new.fullmove_number += 1
    new.turn = board.turn.opposite
    return new


def legal_moves(board: Board) -> list[Move]:
    """All legal moves for the side to move (own king may not be left in check)."""
    color = board.turn
    result: list[Move] = []
    for move in pseudo_legal_moves(board, color):
        new = apply_move(board, move)
        if not is_square_attacked(new, new.king_square(color), new.turn):
            result.append(move)
    return result
