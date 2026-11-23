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


def test_moves_still_lists_legal_moves_after_moves_played(capsys, tmp_path) -> None:
    # Regression: `moves` must stay the LEGAL move list even once the history
    # is non-empty (it used to silently fall back to the played history).
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    run_cli(capsys, "--state", state, "move", "e2e4", "--json")
    rc, out, _ = run_cli(capsys, "--state", state, "moves", "--json")
    assert rc == 0
    payload = json.loads(out)
    moves = payload["moves"]
    assert "e2e4" not in moves  # already played -> not legal anymore
    assert "e7e5" in moves  # black to move now
    assert len(moves) == 20
    assert all(d["uci"] in moves for d in payload["details"])
    # history is unaffected and still reports the played moves
    _, hout, _ = run_cli(capsys, "--state", state, "history", "--json")
    assert json.loads(hout)["moves"] == ["e2e4"]


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


def test_ai_move_plays_a_legal_move(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    rc, out, _ = run_cli(capsys, "--state", state, "ai-move", "--depth", "2")
    assert rc == 0 and "AI played" in out
    rc, out, _ = run_cli(capsys, "--state", state, "ai-move", "--json")
    assert rc == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert set(payload) >= {"move", "san", "score", "nodes", "time_ms", "depth", "status"}
    assert payload["depth"] == 3  # default depth
    assert payload["status"]["turn"] == "w"  # AI played White, now Black to move
    rc, out, _ = run_cli(capsys, "--state", state, "history", "--json")
    history = json.loads(out)
    assert history["moves"][-1] == payload["move"]
    assert history["details"][-1]["san"] == payload["san"]


def test_ai_move_on_finished_game_is_an_error(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new")
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        run_cli(capsys, "--state", state, "move", uci)
    rc, _, err = run_cli(capsys, "--state", state, "ai-move")
    assert rc == 1 and "game is over" in err


def test_status_json_exposes_version_and_it_increments(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    _, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    v_new = json.loads(out)["version"]
    assert isinstance(v_new, int) and v_new >= 1
    run_cli(capsys, "--state", state, "move", "e2e4", "--json")
    _, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    v_move = json.loads(out)["version"]
    assert v_move == v_new + 1
    run_cli(capsys, "--state", state, "undo", "--json")
    _, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    assert json.loads(out)["version"] == v_move + 1
    # `new` also counts as a modification: version keeps increasing
    run_cli(capsys, "--state", state, "new", "--json")
    _, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    assert json.loads(out)["version"] == v_move + 2


def test_wait_returns_immediately_when_condition_already_met(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    rc, out, _ = run_cli(capsys, "--state", state, "wait", "--color", "w", "--timeout", "2", "--json")
    assert rc == 0
    payload = json.loads(out)
    assert payload["ok"] is True
    assert payload["timeout"] is False
    assert payload["status"]["turn"] == "w"
    assert payload["status"]["result"] == "ongoing"


def test_wait_times_out_when_condition_not_met(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    run_cli(capsys, "--state", state, "move", "e2e4", "--json")  # black to move
    rc, out, _ = run_cli(capsys, "--state", state, "wait", "--color", "w", "--timeout", "0.3", "--json")
    assert rc == 0
    payload = json.loads(out)
    assert payload["timeout"] is True
    assert payload["status"]["turn"] == "b"


def test_wait_returns_when_game_is_over(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    for mv in ["f2f3", "e7e5", "g2g4", "d8h4"]:  # fool's mate
        run_cli(capsys, "--state", state, "move", mv, "--json")
    rc, out, _ = run_cli(capsys, "--state", state, "wait", "--color", "b", "--timeout", "5", "--json")
    assert rc == 0
    payload = json.loads(out)
    assert payload["timeout"] is False
    assert payload["status"]["result"] == "checkmate"
    assert payload["status"]["winner"] == "b"


def test_wait_requires_a_color(capsys, tmp_path) -> None:
    import pytest

    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    with pytest.raises(SystemExit):
        run_cli(capsys, "--state", state, "wait", "--timeout", "1", "--json")


def test_wait_unblocks_when_another_process_plays(capsys, tmp_path) -> None:
    import subprocess
    import sys
    import time
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    proc = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys; from chess.cli.main import main; "
            "sys.exit(main(['--state', sys.argv[1], 'wait', '--color', 'b', "
            "'--timeout', '5', '--json']))",
            state,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=root,
    )
    time.sleep(0.6)  # laisser le wait démarrer et entrer dans sa boucle
    run_cli(capsys, "--state", state, "move", "e2e4", "--json")
    out, _err = proc.communicate(timeout=10)
    assert proc.returncode == 0
    payload = json.loads(out)
    assert payload["timeout"] is False
    assert payload["status"]["turn"] == "b"


def test_resign_offer_draw_takeback_and_ai_level(capsys, tmp_path) -> None:
    state = str(tmp_path / ".chess_game.json")
    run_cli(capsys, "--state", state, "new", "--json")
    run_cli(capsys, "--state", state, "move", "e2e4", "--json")
    rc, out, _ = run_cli(capsys, "--state", state, "ai-move", "--level", "debutant", "--json")
    assert rc == 0
    payload = json.loads(out)
    assert payload["level"] == "debutant" and payload["depth"] == 1
    assert payload["status"]["turn"] == "w"
    # takeback removes my move AND the computer's answer
    rc, out, _ = run_cli(capsys, "--state", state, "takeback", "--json")
    assert rc == 0 and len(json.loads(out)["undone"]) == 2
    _, out, _ = run_cli(capsys, "--state", state, "status", "--json")
    assert json.loads(out)["turn"] == "w" and json.loads(out)["fen"].startswith(
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w"
    )
    rc, out, _ = run_cli(capsys, "--state", state, "offer-draw", "--json")
    assert rc == 0 and json.loads(out)["status"]["result"] == "draw_agreement"
    # resign on a finished game is an error
    rc, out, _ = run_cli(capsys, "--state", state, "resign", "--json")
    assert rc == 1
    run_cli(capsys, "--state", state, "new", "--json")
    rc, out, _ = run_cli(capsys, "--state", state, "resign", "--json")
    assert rc == 0
    payload = json.loads(out)["status"]
    assert payload["result"] == "resignation" and payload["winner"] == "b"
