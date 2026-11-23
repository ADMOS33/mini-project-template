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
    assert status["winner"] == "b"


def test_single_undo_after_two_plies_restores_exact_position(tmp_path) -> None:
    """Regression: ONE undo must take back exactly one ply, even when the game
    is reloaded from disk between commands (like the CLI does)."""
    path = tmp_path / "game.json"
    game = Game()
    game.save(path)
    for uci in ("e2e4", "e7e5"):
        game = Game.load(path)
        game.play_uci(uci)
        game.save(path)
    game = Game.load(path)
    undone = game.undo()
    assert undone is not None and undone.to_uci() == "e7e5"
    assert [m.to_uci() for m in game.moves] == ["e2e4"]
    assert game.status()["fen"] == (
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    )
    assert game.position_fens() == [
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1",
    ]


def test_from_dict_with_stale_positions_still_undoes_one_ply() -> None:
    """A persisted state whose positions list misses the current FEN (legacy
    format) must not make undo jump back two plies."""
    f0 = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    f1 = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    f2 = "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2"
    data = {"fen": f2, "moves": ["e2e4", "e7e5"], "positions": [f0, f1]}
    game = Game.from_dict(data)
    game.undo()
    assert [m.to_uci() for m in game.moves] == ["e2e4"]
    assert game.status()["fen"] == f1


def test_from_dict_without_positions_but_with_moves_is_rejected() -> None:
    """A state with moves but no position history is corrupted: refuse it
    clearly instead of letting undo crash later."""
    data = {
        "fen": "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2",
        "moves": ["e2e4", "e7e5"],
    }
    with pytest.raises(ValueError, match="corrupted game state"):
        Game.from_dict(data)


def test_external_result_blocks_moves_and_persists(tmp_path) -> None:
    game = Game()
    game.play_uci("e2e4")
    game.set_external_result("flag", "b")
    status = game.status()
    assert status["result"] == "flag"
    assert status["winner"] == "b"
    with pytest.raises(ValueError, match="game is over"):
        game.play_uci("e7e5")
    path = tmp_path / "g.json"
    game.save(path)
    loaded = Game.load(path)
    assert loaded.status()["result"] == "flag"
    assert loaded.status()["winner"] == "b"


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


def test_version_counter_increments_on_play_undo_and_persists(tmp_path) -> None:
    game = Game()
    assert game.status()["version"] == 0
    game.play_uci("e2e4")
    assert game.status()["version"] == 1
    game.play_uci("e7e5")
    assert game.status()["version"] == 2
    game.undo()
    assert game.status()["version"] == 3
    path = tmp_path / "g.json"
    game.save(path)
    loaded = Game.load(path)
    assert loaded.status()["version"] == 3
    loaded.play_uci("e7e5")
    assert loaded.status()["version"] == 4


def test_version_survives_legacy_state_file_without_version(tmp_path) -> None:
    import json

    game = Game()
    game.play_uci("e2e4")
    path = tmp_path / "g.json"
    game.save(path)
    data = json.loads(path.read_text(encoding="utf-8"))
    del data["version"]
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = Game.load(path)
    assert loaded.status()["version"] == 1  # replayed move count as fallback


def test_next_version_increases_across_new_games(tmp_path) -> None:
    from chess.engine.game import next_version

    path = tmp_path / "g.json"
    assert next_version(path) == 1
    game = Game()
    game.version = next_version(path)
    game.save(path)
    assert next_version(path) == 2
    game.play_uci("e2e4")
    game.save(path)
    assert next_version(path) == 3


def test_resign_and_offer_draw_are_persisted_external_results(tmp_path) -> None:
    game = Game()
    game.play_uci("e2e4")
    game.resign()  # black to move resigns -> white wins
    status = game.status()
    assert status["result"] == "resignation"
    assert status["winner"] == "w"
    with pytest.raises(ValueError, match="game is over"):
        game.play_uci("e7e5")
    path = tmp_path / "g.json"
    game.save(path)
    loaded = Game.load(path)
    assert loaded.status()["result"] == "resignation"
    assert loaded.status()["winner"] == "w"

    game2 = Game()
    game2.offer_draw()
    assert game2.status()["result"] == "draw_agreement"
    assert game2.status()["winner"] is None
