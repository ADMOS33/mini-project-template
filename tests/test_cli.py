"""Tests for the CLI (chess/cli/main.py)."""

import json

from chess.cli.main import main


def run_cli(capsys, *argv: str):
    rc = main(list(argv))
    out = capsys.readouterr()
    return rc, out.out, out.err


def test_new_board_move_status(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    rc, out, _ = run_cli(capsys, "--state", state, "new")
    assert rc == 0 and "New game started" in out
    rc, out, _ = run_cli(capsys, "--state", state, "board")
    assert rc == 0 and "R N B Q K B N R" in out
    rc, out, _ = run_cli(capsys, "--state", state, "move", "e2e4")
    assert rc == 0 and "Played e2e4" in out
    rc, out, _ = run_cli(capsys, "--state", state, "board")
    assert rc == 0
    # rank 4 row of the ASCII board must show the pawn on e4 and nothing else
    assert out.splitlines()[4] == "4  . . . . P . . ."
    rc, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    assert rc == 0
    payload = json.loads(out)
    assert payload["turn"] == "b"
    assert payload["result"] == "ongoing"
    assert payload["fen"].endswith("b KQkq e3 0 1")


def test_moves_json_has_20_moves_initially(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    rc, out, _ = run_cli(capsys, "--state", state, "moves", "--json")
    assert rc == 0
    moves = json.loads(out)["moves"]
    assert len(moves) == 20
    assert "e2e4" in moves


def test_illegal_move_error_lists_legal_moves(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    rc, out, err = run_cli(capsys, "--state", state, "move", "e2e5")
    assert rc == 1
    assert "illegal move 'e2e5'" in err and "e2e4" in err
    rc, out, _ = run_cli(capsys, "--state", state, "move", "e2e5", "--json")
    assert rc == 1
    assert "legal moves" in json.loads(out)["error"]


def test_no_game_error_mentions_new(capsys, tmp_path) -> None:
    rc, _, err = run_cli(capsys, "--state", str(tmp_path / "nope.json"), "board")
    assert rc == 1 and "chess new" in err


def test_undo_fen_history_load(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    run_cli(capsys, "--state", state, "move", "e2e4")
    run_cli(capsys, "--state", state, "move", "e7e5")
    rc, out, _ = run_cli(capsys, "--state", state, "history")
    assert rc == 0 and "1. e2e4" in out and "2. e7e5" in out
    rc, out, _ = run_cli(capsys, "--state", state, "fen")
    assert "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2" in out
    rc, out, _ = run_cli(capsys, "--state", state, "undo")
    assert rc == 0 and "Undone e7e5" in out
    rc, out, _ = run_cli(capsys, "--state", state, "load",
                         "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
    assert rc == 0
    rc, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    assert json.loads(out)["fullmove_number"] == 1
    rc, _, err = run_cli(capsys, "--state", state, "load", "not a fen")
    assert rc == 1 and "invalid FEN" in err


def test_load_empty_board_is_a_clean_invalid_fen_error(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    rc, _, err = run_cli(capsys, "--state", state, "load", "8/8/8/8/8/8/8/8 w - - 0 1")
    assert rc == 1
    assert "invalid FEN" in err
    assert "Traceback" not in err
    rc, out, _ = run_cli(capsys, "--state", state, "load", "8/8/8/8/8/8/8/8 w - - 0 1", "--json")
    assert rc == 1 and "invalid FEN" in json.loads(out)["error"]


def test_move_accepts_san(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    rc, out, _ = run_cli(capsys, "--state", state, "move", "Nf3")
    assert rc == 0 and "Played g1f3" in out
    rc, out, _ = run_cli(capsys, "--state", state, "move", "e5")
    assert rc == 0 and "Played e7e5" in out
    # SAN castling with the 0-0 spelling
    run_cli(capsys, "--state", state, "load", "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
    rc, out, _ = run_cli(capsys, "--state", state, "move", "0-0")
    assert rc == 0 and "Played e1g1" in out
    # illegal SAN -> rc 1 with the legal moves listed
    rc, _, err = run_cli(capsys, "--state", state, "move", "Ke9")
    assert rc == 1 and "Ke9" in err and "legal moves" in err


def test_moves_output_shows_uci_and_san(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    rc, out, _ = run_cli(capsys, "--state", state, "moves")
    assert rc == 0 and "g1f3 (Nf3)" in out and "e2e4 (e4)" in out
    rc, out, _ = run_cli(capsys, "--state", state, "moves", "--json")
    payload = json.loads(out)
    assert rc == 0
    assert payload["moves"] == sorted(payload["moves"])  # UCI list kept
    assert len(payload["moves"]) == 20
    details = {d["uci"]: d["san"] for d in payload["details"]}
    assert details["g1f3"] == "Nf3" and details["e2e4"] == "e4"
    assert set(details) == set(payload["moves"])


def test_history_output_shows_uci_and_san(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    run_cli(capsys, "--state", state, "move", "e2e4")
    run_cli(capsys, "--state", state, "move", "e5")
    rc, out, _ = run_cli(capsys, "--state", state, "history")
    assert rc == 0 and "1. e2e4 (e4)" in out and "2. e7e5 (e5)" in out
    rc, out, _ = run_cli(capsys, "--state", state, "history", "--json")
    payload = json.loads(out)
    assert payload["moves"] == ["e2e4", "e7e5"]
    assert payload["details"] == [
        {"uci": "e2e4", "san": "e4"},
        {"uci": "e7e5", "san": "e5"},
    ]


def test_pgn_export_command(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    run_cli(capsys, "--state", state, "move", "e2e4")
    run_cli(capsys, "--state", state, "move", "e7e5")
    rc, out, _ = run_cli(capsys, "--state", state, "pgn")
    assert rc == 0
    assert '[Result "*"]' in out and "1. e4 e5 *" in out
    rc, out, _ = run_cli(capsys, "--state", state, "pgn", "--json")
    assert rc == 0 and "1. e4 e5 *" in json.loads(out)["pgn"]


def test_load_pgn_command(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    pgn_file = tmp_path / "game.pgn"
    pgn_file.write_text(
        '[Event "t"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 Nc6 *\n', encoding="utf-8"
    )
    rc, out, _ = run_cli(capsys, "--state", state, "load-pgn", str(pgn_file))
    assert rc == 0 and "4 plies" in out
    rc, out, _ = run_cli(capsys, "--state", state, "history", "--json")
    assert json.loads(out)["moves"] == ["e2e4", "e7e5", "g1f3", "b8c6"]
    # invalid PGN -> rc 1 with the offending move number
    bad = tmp_path / "bad.pgn"
    bad.write_text("1. e4 e5 2. nonsense\n", encoding="utf-8")
    rc, _, err = run_cli(capsys, "--state", state, "load-pgn", str(bad))
    assert rc == 1 and "invalid PGN" in err and "move 3" in err and "nonsense" in err
    # missing file -> rc 1
    rc, _, err = run_cli(capsys, "--state", state, "load-pgn", str(tmp_path / "nope.pgn"))
    assert rc == 1 and "cannot read" in err


def test_unimplemented_commands_report_clearly(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    rc, _, err = run_cli(capsys, "--state", state, "ai-move")
    assert rc == 1 and "not implemented yet" in err
