"""Tests for move model and move generation (chess/engine/movegen.py)."""

import pytest

from chess.engine.board import parse_square
from chess.engine.fen import START_FEN, board_from_fen, board_to_fen
from chess.engine.move import Move
from chess.engine.movegen import apply_move, is_square_attacked, legal_moves
from chess.engine.pieces import Color, Piece, PieceType


def test_move_uci_roundtrip() -> None:
    assert Move.from_uci("e2e4").to_uci() == "e2e4"
    assert Move.from_uci("E2E4").to_uci() == "e2e4"
    promo = Move.from_uci("e7e8q")
    assert promo.promotion is PieceType.QUEEN
    assert promo.to_uci() == "e7e8q"
    for bad in ("e2", "e2e9", "e2e4x", "e7e8k"):
        with pytest.raises(ValueError):
            Move.from_uci(bad)


def test_initial_position_has_20_legal_moves() -> None:
    board = board_from_fen(START_FEN)
    moves = legal_moves(board)
    assert len(moves) == 20  # perft depth 1
    uci = {m.to_uci() for m in moves}
    assert {"e2e4", "g1f3", "a2a3", "d2d4"} <= uci


def test_apply_move_e2e4() -> None:
    board = board_from_fen(START_FEN)
    new = apply_move(board, Move.from_uci("e2e4"))
    assert new.piece_at(parse_square("e4")) == Piece(PieceType.PAWN, Color.WHITE)
    assert new.piece_at(parse_square("e2")) is None
    assert new.piece_at(parse_square("e2")) is None
    assert new.turn is Color.BLACK
    assert new.ep_square == parse_square("e3")
    assert board.piece_at(parse_square("e2")) is not None  # input unchanged


def test_is_square_attacked_by_rook() -> None:
    board = board_from_fen("4r1k1/8/8/8/8/8/8/4K3 w - - 0 1")
    assert is_square_attacked(board, parse_square("e1"), Color.BLACK)
    assert not is_square_attacked(board, parse_square("a1"), Color.BLACK)


def test_pinned_knight_has_no_legal_moves() -> None:
    board = board_from_fen("4r1k1/8/8/8/8/8/4N3/4K3 w - - 0 1")
    knight_moves = [m for m in legal_moves(board) if m.from_sq == parse_square("e2")]
    assert knight_moves == []


def test_king_cannot_stay_on_attacked_file() -> None:
    board = board_from_fen("4r1k1/8/8/8/8/8/8/4K3 w - - 0 1")
    moves = {m.to_uci() for m in legal_moves(board)}
    assert "e1e2" not in moves  # e-file is attacked by the rook
    assert "e1d1" in moves
    assert "e1f2" in moves


def test_capture_removes_piece() -> None:
    board = board_from_fen("4r1k1/8/8/8/8/8/4P3/4K3 w - - 0 1")
    new = apply_move(board, Move(parse_square("e2"), parse_square("e3")))
    assert new.piece_at(parse_square("e3")).type is PieceType.PAWN
    assert new.halfmove_clock == 0


# --- Castling -----------------------------------------------------------

OPEN_CASTLING = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"


def test_no_castling_from_initial_position() -> None:
    moves = {m.to_uci() for m in legal_moves(board_from_fen(START_FEN))}
    assert "e1g1" not in moves and "e1c1" not in moves


def test_both_castlings_legal_for_white_and_black() -> None:
    white = {m.to_uci() for m in legal_moves(board_from_fen(OPEN_CASTLING))}
    assert "e1g1" in white and "e1c1" in white
    black = {
        m.to_uci()
        for m in legal_moves(board_from_fen(OPEN_CASTLING.replace(" w ", " b ")))
    }
    assert "e8g8" in black and "e8c8" in black


def test_kingside_castling_moves_the_rook() -> None:
    board = board_from_fen(OPEN_CASTLING)
    new = apply_move(board, Move.from_uci("e1g1"))
    assert new.piece_at(parse_square("g1")) == Piece(PieceType.KING, Color.WHITE)
    assert new.piece_at(parse_square("f1")) == Piece(PieceType.ROOK, Color.WHITE)
    assert new.piece_at(parse_square("e1")) is None
    assert new.piece_at(parse_square("h1")) is None
    assert board_to_fen(new) == "r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1"


def test_queenside_castling_moves_the_rook() -> None:
    board = board_from_fen(OPEN_CASTLING)
    new = apply_move(board, Move.from_uci("e1c1"))
    assert new.piece_at(parse_square("c1")) == Piece(PieceType.KING, Color.WHITE)
    assert new.piece_at(parse_square("d1")) == Piece(PieceType.ROOK, Color.WHITE)
    assert new.piece_at(parse_square("a1")) is None
    assert board_to_fen(new) == "r3k2r/8/8/8/8/8/8/2KR3R b kq - 1 1"


def test_black_castling_fens() -> None:
    board = board_from_fen(OPEN_CASTLING.replace(" w ", " b "))
    kingside = apply_move(board, Move.from_uci("e8g8"))
    assert board_to_fen(kingside) == "r4rk1/8/8/8/8/8/8/R3K2R w KQ - 1 2"
    queenside = apply_move(board, Move.from_uci("e8c8"))
    assert board_to_fen(queenside) == "2kr3r/8/8/8/8/8/8/R3K2R w KQ - 1 2"


def test_castling_requires_the_rook_on_its_square() -> None:
    no_rook_h1 = "r3k2r/8/8/8/8/8/8/4K3 w Kq - 0 1"
    moves = {m.to_uci() for m in legal_moves(board_from_fen(no_rook_h1))}
    assert "e1g1" not in moves
    no_rook_a1 = "r3k2r/8/8/8/8/8/8/4K3 w Qq - 0 1"
    moves = {m.to_uci() for m in legal_moves(board_from_fen(no_rook_a1))}
    assert "e1c1" not in moves


def test_castling_requires_empty_intermediate_squares() -> None:
    blocked = "r3k2r/8/8/8/8/8/8/RN2K1NR w KQkq - 0 1"
    moves = {m.to_uci() for m in legal_moves(board_from_fen(blocked))}
    assert "e1g1" not in moves and "e1c1" not in moves


def test_no_castling_out_of_check() -> None:
    in_check = "r3k2r/8/8/8/8/8/4r3/R3K2R w KQkq - 0 1"  # black rook attacks e1
    moves = {m.to_uci() for m in legal_moves(board_from_fen(in_check))}
    assert "e1g1" not in moves and "e1c1" not in moves


def test_no_castling_through_an_attacked_square() -> None:
    transit = "r3k2r/8/8/8/8/8/5r2/R3K2R w KQkq - 0 1"  # f1 attacked by the f2 rook
    moves = {m.to_uci() for m in legal_moves(board_from_fen(transit))}
    assert "e1g1" not in moves
    assert "e1c1" in moves  # queenside is fine


def test_no_castling_onto_an_attacked_square() -> None:
    dest = "r3k2r/8/8/8/8/8/6r1/R3K2R w KQkq - 0 1"  # g1 attacked by the g2 rook
    moves = {m.to_uci() for m in legal_moves(board_from_fen(dest))}
    assert "e1g1" not in moves
    assert "e1c1" in moves


def test_queenside_castling_allows_b1_attacked() -> None:
    # b1 is attacked by the b2 rook, but only e1/d1/c1 matter for queenside.
    b1_attacked = "r3k2r/8/8/8/8/8/1r6/R3K2R w KQkq - 0 1"
    moves = {m.to_uci() for m in legal_moves(board_from_fen(b1_attacked))}
    assert "e1c1" in moves


# --- En passant ----------------------------------------------------------


def test_en_passant_is_generated_after_a_double_push() -> None:
    # 1.e4 a6 2.e5 d5 -> White may capture en passant on d6 (from e5).
    board = board_from_fen(
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    )
    moves = {m.to_uci() for m in legal_moves(board)}
    assert "e5d6" in moves


def test_en_passant_removes_the_pawn_from_its_own_square() -> None:
    board = board_from_fen(
        "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    )
    new = apply_move(board, Move.from_uci("e5d6"))
    assert new.piece_at(parse_square("d6")) == Piece(PieceType.PAWN, Color.WHITE)
    assert new.piece_at(parse_square("d5")) is None  # captured pawn gone from d5
    assert new.piece_at(parse_square("e5")) is None
    # input board unchanged
    assert board.piece_at(parse_square("d5")) == Piece(PieceType.PAWN, Color.BLACK)
    assert board_to_fen(new) == (
        "rnbqkbnr/ppp1pppp/3P4/8/8/8/PPPP1PPP/RNBQKBNR b KQkq - 0 3"
    )


def test_en_passant_pin_is_illegal() -> None:
    # Classic trap: bxc6 e.p. would expose the white king a5 to the h5 rook
    # along the 5th rank (b5 and c5 both become empty), so it is illegal.
    board = board_from_fen("8/8/8/KPp4r/8/8/8/4k3 w - c6 0 1")
    moves = {m.to_uci() for m in legal_moves(board)}
    assert "b5c6" not in moves


def test_en_passant_legal_without_the_pin() -> None:
    board = board_from_fen("8/8/8/KPp5/8/8/8/4k3 w - c6 0 1")
    moves = {m.to_uci() for m in legal_moves(board)}
    assert "b5c6" in moves
    new = apply_move(board, Move.from_uci("b5c6"))
    assert new.piece_at(parse_square("c6")) == Piece(PieceType.PAWN, Color.WHITE)
    assert new.piece_at(parse_square("c5")) is None  # the black pawn is removed
    assert board_to_fen(new) == "8/8/2P5/K7/8/8/8/4k3 b - - 0 1"


def test_en_passant_only_immediately() -> None:
    from chess.engine.game import Game

    game = Game()
    for uci in ("e2e4", "a7a6", "e4e5", "d7d5"):
        game.play_uci(uci)
    assert "e5d6" in {m.to_uci() for m in game.legal_moves()}
    game.play_uci("g1f3")  # ep square expires
    assert "e5d6" not in {m.to_uci() for m in game.legal_moves()}
