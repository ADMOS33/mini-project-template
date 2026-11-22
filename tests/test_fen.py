"""Tests for FEN import/export (chess/engine/fen.py)."""

import pytest

from chess.engine.board import parse_square
from chess.engine.fen import START_FEN, board_from_fen, board_to_fen
from chess.engine.pieces import Color

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"


def test_start_fen_roundtrip() -> None:
    assert board_to_fen(board_from_fen(START_FEN)) == START_FEN


def test_kiwipete_fen_roundtrip() -> None:
    assert board_to_fen(board_from_fen(KIWIPETE)) == KIWIPETE


def test_fen_fields() -> None:
    board = board_from_fen("8/8/8/8/8/8/8/R3K2R b Kq e3 17 42")
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
