"""Tests for the AI (chess/ai/evaluation.py and chess/ai/search.py)."""

import time

import pytest

from chess.ai.evaluation import evaluate
from chess.ai.search import MATE_SCORE, _INF, best_move, negamax
from chess.engine.fen import START_FEN, board_from_fen
from chess.engine.movegen import legal_moves


def test_evaluation_initial_position_is_balanced() -> None:
    assert evaluate(board_from_fen(START_FEN)) == 0


def test_evaluation_material_advantage() -> None:
    # White is up a queen, White to move: positive for the side to move.
    board = board_from_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert evaluate(board) > 800
    # Same position with Black to move: negative for the side to move.
    board_b = board_from_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1")
    assert evaluate(board_b) < -800


def test_evaluation_piece_square_tables() -> None:
    # A knight on e4 is much better than a knight on a1 (same kings).
    e4 = board_from_fen("4k3/8/8/8/4N3/8/8/4K3 w - - 0 1")
    a1 = board_from_fen("4k3/8/8/8/8/8/8/N3K3 w - - 0 1")
    assert evaluate(e4) > evaluate(a1) + 50


def test_mate_score_is_100000() -> None:
    from chess.ai.evaluation import MATE_SCORE

    assert MATE_SCORE == 100_000


def test_best_move_returns_a_legal_move() -> None:
    board = board_from_fen(START_FEN)
    move, score, nodes = best_move(board, depth=1)
    assert move in legal_moves(board)
    assert abs(score) < 200
    assert nodes > 0


def test_best_move_finds_mate_in_one() -> None:
    # Back-rank mate: Ra1-a8 is checkmate.
    board = board_from_fen("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    move, score, nodes = best_move(board, depth=2)
    assert move.to_uci() == "a1a8"
    assert score > MATE_SCORE - 100  # mate adjusted by remaining depth
    assert nodes > 0


def test_negamax_mate_score_for_mated_side() -> None:
    # Black to move, already checkmated (fool's mate final position).
    board = board_from_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
    score, nodes = negamax(board, 1, -MATE_SCORE * 2, MATE_SCORE * 2)
    assert score <= -MATE_SCORE
    assert nodes >= 1


def test_best_move_rejects_bad_depth() -> None:
    with pytest.raises(ValueError):
        best_move(board_from_fen(START_FEN), depth=0)


def test_best_move_takes_a_free_queen() -> None:
    # Black queen on d5 is hanging: e4xd5 wins it.
    board = board_from_fen(
        "rnb1kbnr/pppp1ppp/8/3qp3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq - 0 2"
    )
    move, score, _ = best_move(board, depth=3)
    assert move.to_uci() == "e4d5"
    assert score > 700


def test_best_move_does_not_leave_its_queen_en_prise() -> None:
    # The white queen on f4 is attacked by the e5 pawn; at depth 2 the search
    # must save it instead of hanging it (score would be ~ -900 otherwise).
    board = board_from_fen(
        "rnbqkbnr/ppppp1pp/8/4p3/5Q2/8/PPPPPPPP/RNB1KBNR w KQkq - 0 2"
    )
    move, score, _ = best_move(board, depth=2)
    assert score > -800, f"queen left en prise: {move.to_uci()} score {score}"


def test_best_move_depth3_from_initial_under_5s() -> None:
    board = board_from_fen(START_FEN)
    start = time.perf_counter()
    move, score, nodes = best_move(board, depth=3)
    elapsed = time.perf_counter() - start
    assert move in legal_moves(board)
    assert nodes > 100
    assert elapsed < 5.0, f"depth 3 took {elapsed:.2f}s"


def test_levels_named_and_expert_finds_mate_in_1() -> None:
    import random

    from chess.ai.levels import LEVELS, level_move
    from chess.engine.fen import board_from_fen

    assert set(LEVELS) == {"debutant", "novice", "club", "confirme", "expert"}
    assert LEVELS["expert"]["margin"] == 0 and LEVELS["expert"]["depth"] == 4
    # fool's mate position: expert (deterministic) must find Qh4#
    board = board_from_fen("rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2")
    move, score, nodes, info = level_move(board, "expert")
    assert move.to_uci() == "d8h4"
    assert score >= 100000  # mate score
    assert info["label"] == "Expert" and info["elo"] == 1800
    # injectable RNG: debutant picks within the margin, deterministic with seed
    m1, _, _, _ = level_move(board, "debutant", rng=random.Random(1))
    m2, _, _, _ = level_move(board, "debutant", rng=random.Random(1))
    assert m1.to_uci() == m2.to_uci()
    with pytest.raises(ValueError):
        level_move(board, "nope")


def test_negamax_detects_mate_in_1_at_depth_2() -> None:
    """Regression: negamax must negate child scores (mate in 1 scores +MATE)."""
    from chess.engine.fen import board_from_fen

    board = board_from_fen("7k/8/6K1/8/8/8/8/R7 w - - 0 1")  # Ra8#
    score, _ = negamax(board, 2, -_INF, _INF)
    assert score >= MATE_SCORE
    # and a hanging queen must be seen as winning at depth 2
    board2 = board_from_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    s, _ = negamax(board2, 2, -_INF, _INF)
    assert s >= 900 - 200  # queen is safe to take... just check it is positive-ish
