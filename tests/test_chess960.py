"""Chess960 (V12) tests: 960 start positions, X-FEN rights, generalized castling."""

import pytest

from chess.engine.board import Board, square
from chess.engine.chess960 import start_board, start_fen
from chess.engine.fen import START_FEN, board_from_fen, board_to_fen
from chess.engine.movegen import apply_move, is_castling_move, legal_moves
from chess.engine.pieces import Color, PieceType
from chess.engine.san import move_to_san, san_to_move


def test_960_distinct_positions():
    fens = {start_fen(i) for i in range(960)}
    assert len(fens) == 960


def test_spn_518_is_standard():
    assert start_fen(518) == START_FEN


def test_spn_0_is_bbqnnrkr():
    assert start_fen(0).split()[0] == "bbqnnrkr/pppppppp/8/8/8/8/PPPPPPPP/BBQNNRKR"


def test_invalid_index():
    with pytest.raises(ValueError):
        start_board(-1)
    with pytest.raises(ValueError):
        start_board(960)


def test_start_positions_have_bishops_on_opposite_colors_and_king_between_rooks():
    for i in range(0, 960, 37):  # sample
        board = start_board(i)
        back_rank = [board.squares[square(f, 0)] for f in range(8)]
        types = [p.type for p in back_rank if p is not None]
        bishops = [f for f in range(8) if back_rank[f].type is PieceType.BISHOP]
        king = next(f for f in range(8) if back_rank[f].type is PieceType.KING)
        rooks = [f for f in range(8) if back_rank[f].type is PieceType.ROOK]
        assert (bishops[0] + bishops[1]) % 2 == 1
        assert rooks[0] < king < rooks[1]
        from collections import Counter

        assert Counter(types) == Counter(
            [PieceType.ROOK] * 2 + [PieceType.KNIGHT] * 2 + [PieceType.BISHOP] * 2
            + [PieceType.QUEEN, PieceType.KING]
        )


def test_xfen_round_trip():
    for i in (0, 1, 518, 519, 959):
        board = start_board(i)
        assert board_to_fen(board_from_fen(start_fen(i))) == start_fen(i)


def test_xfen_file_letter_castling_standard_equivalent():
    # Same position as standard start but with X-FEN file letters A/H/a/h.
    board = board_from_fen(
        "r3k2r/8/8/8/8/8/8/R3K2R w AHah - 0 1"
    )
    uci = {m.to_uci() for m in legal_moves(board)}
    assert "e1g1" in uci and "e1c1" in uci  # castling still e1g1/e1c1


def test_chess960_castle_king_takes_rook():
    # White king f1, rook h1: kingside castle is f1h1, king stays on g1, rook to f1.
    board = board_from_fen("4k3/8/8/8/8/8/8/5K1R w H - 0 1")
    castles = [m for m in legal_moves(board) if is_castling_move(board, m)]
    assert [m.to_uci() for m in castles] == ["f1h1"]
    assert move_to_san(board, castles[0]) == "O-O"
    after = apply_move(board, castles[0])
    assert after.squares[square(6, 0)].type is PieceType.KING      # king g1
    assert after.squares[square(5, 0)].type is PieceType.ROOK      # rook f1
    assert after.squares[square(7, 0)] is None                     # h1 empty
    assert after.castling == set()                                 # rights gone
    # SAN parses back
    assert san_to_move(board, "O-O").to_uci() == "f1h1"


def test_chess960_queenside_castle():
    # White king b1, rook a1: queenside castle is b1a1, king to c1, rook to d1.
    board = board_from_fen("4k3/8/8/8/8/8/8/RK6 w A - 0 1")
    castles = [m for m in legal_moves(board) if is_castling_move(board, m)]
    assert [m.to_uci() for m in castles] == ["b1a1"]
    assert move_to_san(board, castles[0]) == "O-O-O"
    after = apply_move(board, castles[0])
    assert after.squares[square(2, 0)].type is PieceType.KING      # king c1
    assert after.squares[square(3, 0)].type is PieceType.ROOK      # rook d1


def test_chess960_castle_blocked_by_piece_between():
    # Knight on g1 blocks the f1-h1 kingside castle.
    board = board_from_fen("4k3/8/8/8/8/8/8/5KNR w H - 0 1")
    assert not [m for m in legal_moves(board) if is_castling_move(board, m)]


def test_chess960_castle_through_check_forbidden():
    # Black rook on g8 attacks g1: kingside castle f1h1 is illegal.
    board = board_from_fen("4k1r1/8/8/8/8/8/8/5K1R w H - 0 1")
    assert not [m for m in legal_moves(board) if is_castling_move(board, m)]


def test_chess960_castle_out_of_check_forbidden():
    # Black rook on f8 attacks f1 (the king): no castling at all.
    board = board_from_fen("4k3/5r2/8/8/8/8/8/5K1R w H - 0 1")
    assert not [m for m in legal_moves(board) if is_castling_move(board, m)]


def test_chess960_rook_move_and_capture_remove_right():
    # Rook leaving a1 removes the white A right.
    board = board_from_fen("r3k3/8/8/8/8/8/8/R3K3 w A - 0 1")
    moves = {m.to_uci(): m for m in legal_moves(board)}
    after = apply_move(board, moves["a1a2"])
    assert "A" not in after.castling
    # Capturing the black rook on a8 removes the black a right too.
    board2 = board_from_fen("r3k3/8/8/8/8/8/8/R3K3 w Aa - 0 1")
    moves2 = {m.to_uci(): m for m in legal_moves(board2)}
    assert "a1a8" in moves2
    after2 = apply_move(board2, moves2["a1a8"])
    assert after2.castling == set()


def test_standard_castling_unchanged():
    board = Board.initial()
    board.squares = [None] * 64  # cleared; rebuild minimal
    board = board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    uci = {m.to_uci() for m in legal_moves(board)}
    assert "e1g1" in uci and "e1c1" in uci
    after = apply_move(board, next(m for m in legal_moves(board) if m.to_uci() == "e1g1"))
    assert after.squares[square(6, 0)].type is PieceType.KING
    assert after.squares[square(5, 0)].type is PieceType.ROOK
    assert after.castling == {"k", "q"}
