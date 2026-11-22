"""Tests for the AI (chess/ai/evaluation.py and chess/ai/search.py)."""

import pytest

from chess.ai.evaluation import evaluate
from chess.ai.search import MATE_SCORE, best_move, negamax
from chess.engine.fen import START_FEN, board_from_fen
from chess.engine.movegen import legal_moves


def test_evaluation_initial_position_is_balanced() -> None:
    assert evaluate(board_from_fen(START_FEN)) == 0


def test_evaluation_material_advantage() -> None:
    # White is up a queen.
    board = board_from_fen("rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert evaluate(board) > 800


def test_best_move_returns_a_legal_move() -> None:
    board = board_from_fen(START_FEN)
    move, score = best_move(board, depth=1)
    assert move in legal_moves(board)
    assert abs(score) < 200


def test_best_move_finds_mate_in_one() -> None:
    # Back-rank mate: Ra1-a8 is checkmate.
    board = board_from_fen("6k1/5ppp/8/8/8/8/8/R6K w - - 0 1")
    move, score = best_move(board, depth=2)
    assert move.to_uci() == "a1a8"
    assert score > MATE_SCORE - 100


def test_negamax_mate_score_for_mated_side() -> None:
    # Black to move, already checkmated (fool's mate final position).
    board = board_from_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
    assert negamax(board, 1, -MATE_SCORE * 2, MATE_SCORE * 2) <= -MATE_SCORE


def test_best_move_rejects_bad_depth() -> None:
    with pytest.raises(ValueError):
        best_move(board_from_fen(START_FEN), depth=0)
