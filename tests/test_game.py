"""Tests for game orchestration (chess/engine/game.py)."""

import pytest

from chess.engine.game import Game


def test_new_game_status() -> None:
    status = Game().status()
    assert status["result"] == "ongoing"
    assert status["turn"] == "w"
    assert status["in_check"] is False
    assert status["legal_move_count"] == 20


def test_play_uci_updates_state() -> None:
    game = Game()
    game.play_uci("e2e4")
    status = game.status()
    assert status["turn"] == "b"
    assert status["fen"] == "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"


def test_illegal_move_raises_with_legal_list() -> None:
    game = Game()
    with pytest.raises(ValueError, match="illegal move 'e2e5'.*e2e4"):
        game.play_uci("e2e5")
    with pytest.raises(ValueError, match="invalid UCI move"):
        game.play_uci("e2")


def test_undo_restores_position() -> None:
    game = Game()
    fen0 = game.status()["fen"]
    game.play_uci("e2e4")
    game.play_uci("e7e5")
    assert game.undo().to_uci() == "e7e5"
    assert game.undo().to_uci() == "e2e4"
    assert game.status()["fen"] == fen0
    assert game.moves == []
    assert game.undo() is None


def test_undo_after_several_moves_restores_intermediate_position() -> None:
    game = Game()
    game.play_uci("e2e4")
    fen_after_e4 = game.status()["fen"]
    game.play_uci("e7e5")
    game.undo()
    assert game.status()["fen"] == fen_after_e4
    game.undo()
    assert game.status()["fen"].startswith("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w")


def test_position_fens_tracks_every_ply() -> None:
    game = Game()
    assert len(game.position_fens()) == 1
    game.play_uci("e2e4")
    game.play_uci("c7c5")
    fens = game.position_fens()
    assert len(fens) == 3
    assert fens[1].endswith("b KQkq e3 0 1")
    assert fens[2] == game.status()["fen"]


def test_fools_mate_is_checkmate() -> None:
    game = Game()
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        game.play_uci(uci)
    status = game.status()
    assert status["result"] == "checkmate"
    assert status["in_check"] is True
    assert status["legal_move_count"] == 0


def test_persistence_roundtrip(tmp_path) -> None:
    game = Game()
    game.play_uci("e2e4")
    game.play_uci("e7e5")
    path = tmp_path / "game.json"
    game.save(path)
    loaded = Game.load(path)
    assert loaded.status() == game.status()
    assert [m.to_uci() for m in loaded.moves] == ["e2e4", "e7e5"]
    loaded.undo()
    game.undo()
    assert loaded.status() == game.status()
    assert [m.to_uci() for m in loaded.moves] == ["e2e4"]
