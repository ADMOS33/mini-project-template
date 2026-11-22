"""Tests for FEN import/export (chess/engine/fen.py)."""

import pytest

from chess.engine.board import parse_square
from chess.engine.fen import START_FEN, board_from_fen, board_to_fen
from chess.engine.pieces import Color, PieceType

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"


def test_start_fen_roundtrip() -> None:
    assert board_to_fen(board_from_fen(START_FEN)) == START_FEN


def test_kiwipete_fen_roundtrip() -> None:
    assert board_to_fen(board_from_fen(KIWIPETE)) == KIWIPETE


def test_fen_fields() -> None:
    board = board_from_fen("4k3/8/8/8/8/8/8/R3K2R b Kq e3 17 42")
    assert board.turn is Color.BLACK
    assert board.castling == {"K", "q"}
    assert board.ep_square == parse_square("e3")
    assert board.halfmove_clock == 17
    assert board.fullmove_number == 42


def test_invalid_fen_raises() -> None:
    bad_fens = [
        "",
        "8/8/8/8/8/8/8/8 w",  # missing fields
        "8/8/8/8/8/8/8/8 x KQkq - 0 1",  # bad side
        "9/8/8/8/8/8/8/8 w - - 0 1",  # rank overflow
        "7/8/8/8/8/8/8/8 w - - 0 1",  # short rank
        "8/8/8/8/8/8/8/8 w KQx - 0 1",  # bad castling
        "8/8/8/8/8/8/8/8 w - - x 1",  # bad counter
    ]
    for bad in bad_fens:
        with pytest.raises(ValueError):
            board_from_fen(bad)


def test_fen_must_have_exactly_one_king_per_side() -> None:
    bad_fens = [
        "8/8/8/8/8/8/8/8 w - - 0 1",  # no king at all
        "4k3/8/8/8/8/8/8/4K3 w - - 0 1",  # ok (control, not in list)
    ]
    with pytest.raises(ValueError, match="exactly one king"):
        board_from_fen("8/8/8/8/8/8/8/8 w - - 0 1")
    with pytest.raises(ValueError, match="exactly one king"):
        board_from_fen("4k3/8/8/8/8/8/8/8 w - - 0 1")  # no white king
    with pytest.raises(ValueError, match="exactly one king"):
        board_from_fen("8/8/8/8/8/8/8/4K3 w - - 0 1")  # no black king
    with pytest.raises(ValueError, match="exactly one king"):
        board_from_fen("4k3/8/8/8/8/8/8/3K1K2 w - - 0 1")  # two white kings
    # control: one king per side is accepted
    assert board_from_fen(bad_fens[1]).king_square(Color.BLACK) is not None


def test_fen_rejects_pawns_on_first_and_last_ranks() -> None:
    with pytest.raises(ValueError, match="pawn"):
        board_from_fen("4k3/8/8/8/8/8/8/P3K3 w - - 0 1")  # white pawn on rank 1
    with pytest.raises(ValueError, match="pawn"):
        board_from_fen("p3k3/8/8/8/8/8/8/4K3 w - - 0 1")  # black pawn on rank 8
    # pawns on ranks 2..7 are fine
    board = board_from_fen("4k3/p7/8/8/8/8/P7/4K3 w - - 0 1")
    assert board.piece_at(parse_square("a7")).type is PieceType.PAWN


def test_fen_rejects_check_against_the_side_not_to_move() -> None:
    # White to move but the black king is already in check: illegal position.
    with pytest.raises(ValueError, match="check"):
        board_from_fen("4k3/8/8/8/8/8/8/4R1K1 w - - 0 1")
    # Same position with Black to move is legal (black is in check and must respond).
    board = board_from_fen("4k3/8/8/8/8/8/8/4R1K1 b - - 0 1")
    assert board.turn is Color.BLACK
