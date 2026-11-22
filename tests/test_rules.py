"""Tests for end-of-game rules (chess/engine/rules.py)."""

from collections import Counter

from chess.engine.fen import START_FEN, board_from_fen
from chess.engine.game import Game
from chess.engine.rules import game_result, position_key


def test_game_result_ongoing_at_start() -> None:
    result, winner = game_result(board_from_fen(START_FEN), Counter())
    assert result == "ongoing"
    assert winner is None


def test_game_result_checkmate_fools_mate() -> None:
    game = Game()
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.play_uci(uci)
    result, winner = game_result(game.board, Counter())
    assert result == "checkmate"
    assert winner == "b"  # Black delivered the mate


def test_game_result_stalemate() -> None:
    # Black to move, not in check, no legal move.
    board = board_from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
    result, winner = game_result(board, Counter())
    assert result == "stalemate"
    assert winner is None


def test_game_result_fifty_move_rule() -> None:
    board = board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 100 60")
    result, winner = game_result(board, Counter())
    assert result == "draw_fifty_move"
    assert winner is None


def test_status_exposes_winner() -> None:
    game = Game()
    assert game.status()["winner"] is None
    assert game.status()["result"] == "ongoing"
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.play_uci(uci)
    status = game.status()
    assert status["result"] == "checkmate"
    assert status["winner"] == "b"


# --- Threefold repetition -------------------------------------------------


def test_position_key_ignores_move_counters() -> None:
    a = board_from_fen(START_FEN)
    b = board_from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 42")
    assert position_key(a) == position_key(b)


def test_position_key_includes_castling_rights() -> None:
    full = board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    partial = board_from_fen("r3k2r/8/8/8/8/8/8/R3K2R w Kq - 0 1")
    assert position_key(full) != position_key(partial)


def test_position_key_ignores_ep_square_when_no_capture_is_playable() -> None:
    # After 1.e4 the ep square is e3, but no black pawn can capture on it.
    with_ep = board_from_fen(
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    )
    without_ep = board_from_fen(
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    )
    assert position_key(with_ep) == position_key(without_ep)


def test_position_key_keeps_ep_square_when_a_capture_is_playable() -> None:
    # After 1.e4 a6 2.e5 d5 the white pawn on e5 can capture on d6.
    with_ep = board_from_fen(
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    )
    without_ep = board_from_fen(
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq - 0 3"
    )
    assert position_key(with_ep) != position_key(without_ep)


def test_two_repetitions_are_not_a_draw() -> None:
    game = Game()
    for uci in ("g1f3", "g8f6", "f3g1", "f6g8"):
        game.play_uci(uci)
    assert game.status()["result"] == "ongoing"


def test_threefold_repetition_is_a_draw() -> None:
    game = Game()
    for uci in ("g1f3", "g8f6", "f3g1", "f6g8", "g1f3", "g8f6", "f3g1", "f6g8"):
        game.play_uci(uci)
    status = game.status()
    assert status["result"] == "draw_threefold"
    assert status["winner"] is None
