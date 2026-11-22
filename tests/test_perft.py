"""Perft tests on standard reference positions (chess/engine/perft.py).

Reference values: Chess Programming Wiki, "Perft Results".

Long-running cases carry ``@pytest.mark.slow`` (marker declared in
pyproject.toml, deselect with ``-m "not slow"``).
"""

import pytest

from chess.engine.fen import START_FEN, board_from_fen
from chess.engine.perft import divide, perft

KIWIPETE = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
POSITION_3 = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"  # en-passant heavy
POSITION_4 = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"

slow = pytest.mark.slow


@pytest.mark.parametrize(
    "fen,depth,expected",
    [
        pytest.param(START_FEN, 1, 20, id="initial-p1"),
        pytest.param(START_FEN, 2, 400, id="initial-p2"),
        pytest.param(START_FEN, 3, 8902, id="initial-p3"),
        pytest.param(START_FEN, 4, 197281, id="initial-p4", marks=[slow]),
        pytest.param(KIWIPETE, 1, 48, id="kiwipete-p1"),
        pytest.param(KIWIPETE, 2, 2039, id="kiwipete-p2"),
        pytest.param(KIWIPETE, 3, 97862, id="kiwipete-p3", marks=[slow]),
        pytest.param(POSITION_3, 1, 14, id="pos3-p1"),
        pytest.param(POSITION_3, 2, 191, id="pos3-p2"),
        pytest.param(POSITION_3, 3, 2812, id="pos3-p3"),
        pytest.param(POSITION_4, 1, 6, id="pos4-p1"),
        pytest.param(POSITION_4, 2, 264, id="pos4-p2"),
        pytest.param(POSITION_4, 3, 9467, id="pos4-p3"),
    ],
)
def test_perft_reference_positions(fen: str, depth: int, expected: int) -> None:
    assert perft(board_from_fen(fen), depth) == expected


def test_perft_depth_zero_is_one() -> None:
    assert perft(board_from_fen(START_FEN), 0) == 1


def test_perft_rejects_negative_depth() -> None:
    with pytest.raises(ValueError, match="depth"):
        perft(board_from_fen(START_FEN), -1)


def test_divide_initial_depth1() -> None:
    counts = divide(board_from_fen(START_FEN), 1)
    assert len(counts) == 20
    assert sum(counts.values()) == 20
    assert set(counts.values()) == {1}


def test_divide_initial_depth2_matches_perft() -> None:
    board = board_from_fen(START_FEN)
    counts = divide(board, 2)
    assert sum(counts.values()) == perft(board, 2) == 400
    assert counts["e2e4"] == 20  # after 1.e4 Black has 20 legal replies


def test_divide_rejects_depth_zero() -> None:
    with pytest.raises(ValueError, match="depth"):
        divide(board_from_fen(START_FEN), 0)


def test_divide_kiwipete_depth1_lists_castling() -> None:
    # Cross-check with divide(): 48 root moves including both castlings.
    counts = divide(board_from_fen(KIWIPETE), 1)
    assert len(counts) == 48
    assert sum(counts.values()) == 48
    assert "e1g1" in counts and "e1c1" in counts


def test_divide_kiwipete_depth2_sum_matches_perft() -> None:
    board = board_from_fen(KIWIPETE)
    counts = divide(board, 2)
    assert sum(counts.values()) == perft(board, 2) == 2039


def test_divide_counts_en_passant_capture() -> None:
    # After 1.e4 a6 2.e5 d5 the en-passant capture e5d6 must be generated.
    board = board_from_fen(
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    )
    counts = divide(board, 1)
    assert counts["e5d6"] == 1
    assert sum(counts.values()) == perft(board, 1)
