"""Tests for the game archive (chess/archive.py, V11) — CLI + API."""

from __future__ import annotations

import json

import pytest

import chess.api.server as server
from chess.archive import archive_current, archive_game, load_archive, save_game
from chess.cli.main import main
from chess.engine.game import Game


def run_cli(capsys, *argv: str):
    rc = main(list(argv))
    out = capsys.readouterr()
    return rc, out.out, out.err


def _fools_mate() -> Game:
    game = Game()
    for mv in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        game.play_uci(mv)
    return game


def test_archive_on_game_over_exactly_once(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CHESS_ARCHIVE_FILE", str(tmp_path / "archive.json"))
    import chess.archive as archive

    state = tmp_path / "game.json"
    game = Game()
    game.play_uci("e2e4")
    save_game(game, state)
    assert load_archive() == []  # game ongoing: not archived
    game = _fools_mate()
    game.meta["mode"] = "computer"
    game.meta["level"] = "club"
    save_game(game, state)
    entries = load_archive()
    assert len(entries) == 1
    e = entries[0]
    assert e["result"] == "checkmate" and e["winner"] == "b"
    assert e["moves_count"] == 4 and e["mode"] == "computer" and e["level"] == "club"
    assert "Qh4#" in e["pgn"] or "d8h4" in e["pgn"]
    assert e["opening"] is None or e["opening"]["code"]  # 1.f3 is not in the book
    # saving again must not duplicate
    save_game(Game.load(state), state, archive.ARCHIVE_FILE)
    assert len(load_archive()) == 1
    # archive_current on a finished persisted game -> still exactly one
    assert archive_current(state) is None
    assert len(load_archive()) == 1


def test_archive_current_before_new_game(tmp_path) -> None:
    import chess.archive as archive

    af = tmp_path / "archive.json"
    state = tmp_path / "game.json"
    game = _fools_mate()
    game.save(state)  # finished but not yet archived
    entry = archive_current(state, af)
    assert entry is not None and entry["result"] == "checkmate"
    assert len(load_archive(af)) == 1


def test_cli_games_and_api_games_endpoints(capsys, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("CHESS_ARCHIVE_FILE", str(tmp_path / "archive.json"))
    state = str(tmp_path / ".chess_game.json")
    monkeypatch.setattr(server, "STATE_FILE", __import__("pathlib").Path(state))
    run_cli(capsys, "--state", state, "new", "--json")
    for mv in ["f2f3", "e7e5", "g2g4", "d8h4"]:
        run_cli(capsys, "--state", state, "move", mv, "--json")
    rc, out, _ = run_cli(capsys, "--state", state, "games", "--json")
    assert rc == 0
    games = json.loads(out)["games"]
    assert len(games) == 1 and games[0]["result"] == "checkmate"
    # API endpoints
    r = server.get_games()
    assert len(r["games"]) == 1 and r["games"][0]["id"] == games[0]["id"]
    full = server.get_game(games[0]["id"])
    assert "pgn" in full and "1." in full["pgn"]
    with pytest.raises(Exception):
        server.get_game(999)
    # starting a new game archives the ongoing one too
    run_cli(capsys, "--state", state, "new", "--json")
    run_cli(capsys, "--state", state, "move", "e2e4", "--json")
    server.post_new()  # archives the ongoing game? no: ongoing -> not archived
    assert len(server.get_games()["games"]) == 1
