"""Tests for the HTTP API.

Route functions are called directly with ``server.STATE_FILE`` monkeypatched
to a tmp_path (no HTTP client needed — httpx is not an allowed dependency,
see README "Décisions"). One slow integration test boots uvicorn in a
subprocess on a free port and talks to it with urllib.request only.
"""

from pathlib import Path

import pytest
from fastapi import HTTPException

import chess.api.server as server
from chess.api.schemas import AiMoveRequest, LoadRequest, MoveRequest, PgnRequest


@pytest.fixture()
def state(tmp_path, monkeypatch):
    path = tmp_path / ".chess_game.json"
    monkeypatch.setattr(server, "STATE_FILE", path)
    return path


def test_new_move_status_flow(state) -> None:
    server.post_new()
    r = server.post_move(MoveRequest(move="e2e4"))
    assert r["ok"] and r["move"] == "e2e4"
    st = server.get_status()
    assert st["turn"] == "b"
    assert st["last_move"] == "e2e4"


def test_illegal_move_raises_400_with_legal_list(state) -> None:
    server.post_new()
    with pytest.raises(HTTPException) as exc:
        server.post_move(MoveRequest(move="e2e5"))
    assert exc.value.status_code == 400
    assert "e2e4" in exc.value.detail


def test_moves_endpoint_lists_20_at_start(state) -> None:
    server.post_new()
    assert len(server.get_moves()["moves"]) == 20


def test_history_san_and_fens(state) -> None:
    server.post_new()
    for uci in ("e2e4", "e7e5", "g1f3"):
        server.post_move(MoveRequest(move=uci))
    entries = server.get_history()["entries"]
    assert [e["san"] for e in entries] == [None, "e4", "e5", "Nf3"]
    assert [e["uci"] for e in entries] == [None, "e2e4", "e7e5", "g1f3"]
    assert entries[3]["fen"].endswith("b KQkq - 1 2")


def test_pgn_export_then_import_roundtrip(state) -> None:
    server.post_new()
    for uci in ("e2e4", "e7e5", "g1f3", "b8c6"):
        server.post_move(MoveRequest(move=uci))
    pgn = server.get_pgn()["pgn"]
    assert "1. e4 e5 2. Nf3 Nc6" in pgn
    assert '[Result "*"]' in pgn
    server.post_new()
    r = server.post_load_pgn(PgnRequest(pgn=pgn))
    assert r["ok"] and r["moves"] == ["e2e4", "e7e5", "g1f3", "b8c6"]
    assert server.get_history()["entries"][-1]["san"] == "Nc6"


def test_load_pgn_rejects_unknown_move(state) -> None:
    server.post_new()
    with pytest.raises(HTTPException) as exc:
        server.post_load_pgn(PgnRequest(pgn="1. e4 e5 2. Nf3 Nc6 3. nonsense"))
    assert exc.value.status_code == 400
    assert "nonsense" in exc.value.detail
    assert "move 5" in exc.value.detail


OPERA_PGN = """[Event "Paris Opera"]
[Result "1-0"]

1. e4 e5 2. Nf3 d6 3. d4 Bg4 4. dxe5 Bxf3 5. Qxf3 dxe5 6. Bc4 Nf6
7. Qb3 Qe7 8. Nc3 c6 9. Bg5 b5 10. Nxb5 cxb5 11. Bxb5+ Nbd7
12. O-O-O Rd8 13. Rxd7 Rxd7 14. Rd1 Qe6 15. Bxd7+ Nxd7 16. Qb8+ Nxb8
17. Rd8# 1-0
"""


def test_load_pgn_morphy_opera_is_checkmate(state) -> None:
    r = server.post_load_pgn(PgnRequest(pgn=OPERA_PGN))
    assert r["ok"] and len(r["moves"]) == 33
    assert r["status"]["result"] == "checkmate"
    assert r["status"]["winner"] == "w"
    pgn = server.get_pgn()["pgn"]
    assert "17. Rd8#" in pgn and '[Result "1-0"]' in pgn


def test_get_pgn_writes_setup_and_fen_for_custom_start(state) -> None:
    server.post_load(LoadRequest(fen="r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"))
    server.post_move(MoveRequest(move="e1g1"))
    pgn = server.get_pgn()["pgn"]
    assert '[SetUp "1"]' in pgn
    assert '[FEN "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"]' in pgn
    assert "1. O-O" in pgn


def test_load_fen_endpoint(state) -> None:
    fen = "6k1/5ppp/8/8/8/8/8/R6K w - - 0 1"
    r = server.post_load(LoadRequest(fen=fen))
    assert r["ok"]
    assert server.get_fen()["fen"] == fen


def test_load_invalid_fen_raises_400(state) -> None:
    server.post_new()
    with pytest.raises(HTTPException) as exc:
        server.post_load(LoadRequest(fen="8/8/8/8/8/8/8/8 w - - 0 1"))  # no kings
    assert exc.value.status_code == 400
    assert "invalid FEN" in exc.value.detail


def test_undo_on_empty_history_raises_400(state) -> None:
    server.post_new()
    with pytest.raises(HTTPException) as exc:
        server.post_undo()
    assert exc.value.status_code == 400
    assert "no moves to undo" in exc.value.detail


def test_ai_move_plays_and_flips_turn(state) -> None:
    server.post_new()
    r = server.post_ai_move(AiMoveRequest(depth=2))
    assert r["ok"] and r["depth"] == 2
    assert set(r) >= {"move", "san", "score", "nodes", "time_ms"}
    assert r["nodes"] > 0 and r["time_ms"] >= 0
    st = server.get_status()
    assert st["turn"] == "b"
    assert st["last_move"] == r["move"]
    # the SAN of the AI move is in the history
    assert server.get_history()["entries"][-1]["san"] == r["san"]


def test_ai_move_on_finished_game_is_400(state) -> None:
    server.post_new()
    for uci in ("f2f3", "e7e5", "g2g4", "d8h4"):
        server.post_move(MoveRequest(move=uci))
    with pytest.raises(HTTPException) as exc:
        server.post_ai_move(AiMoveRequest(depth=1))
    assert exc.value.status_code == 400
    assert "game is over" in exc.value.detail


def test_eval_endpoint_static_score(state) -> None:
    server.post_new()
    r = server.get_eval()
    assert r["score"] == 0  # initial position is balanced
    assert r["turn"] == "w"
    server.post_load(LoadRequest(fen="rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"))
    assert server.get_eval()["score"] > 800  # White (to move) is up a queen


def test_undo_endpoint(state) -> None:
    server.post_new()
    server.post_move(MoveRequest(move="e2e4"))
    r = server.post_undo()
    assert r["undone"] == "e2e4"
    with pytest.raises(HTTPException):
        server.post_undo()


def test_missing_state_file_starts_a_fresh_game(state) -> None:
    assert not state.exists()
    assert server.get_status()["turn"] == "w"


def test_corrupted_state_file_gives_a_clear_error(state) -> None:
    server.post_new()
    state.write_text("{not json", encoding="utf-8")  # JSONDecodeError
    with pytest.raises(HTTPException) as exc:
        server.get_status()
    assert exc.value.status_code == 500
    assert "corrupted game state" in exc.value.detail


def test_state_file_with_wrong_shape_gives_a_clear_error(state) -> None:
    state.write_text('{"fen": 42}', encoding="utf-8")
    with pytest.raises(HTTPException) as exc:
        server.get_moves()
    assert exc.value.status_code == 500
    assert "corrupted game state" in exc.value.detail


@pytest.mark.slow
def test_live_server_over_http_with_urllib(tmp_path) -> None:
    """Integration test: uvicorn in a subprocess on a free port, stopped at
    the end of the test; requests via urllib.request (no new dependency)."""
    import json as jsonlib
    import os
    import socket
    import subprocess
    import sys
    import time
    import urllib.error
    import urllib.request

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    env = dict(os.environ, CHESS_STATE_FILE=str(tmp_path / ".chess_game.json"))
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "chess.api.server:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=root, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"

    def req(method: str, path: str, payload: dict | None = None):
        data = jsonlib.dumps(payload).encode() if payload is not None else None
        request = urllib.request.Request(
            base + path, data=data, method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=5) as resp:
            return resp.status, jsonlib.loads(resp.read())

    try:
        for _ in range(100):  # wait for the server to be ready
            try:
                req("GET", "/api/status")
                break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("uvicorn did not start")
        assert req("GET", "/api/status")[1]["turn"] == "w"
        assert req("POST", "/api/new", {})[0] == 200
        status, body = req("POST", "/api/move", {"move": "e2e4"})
        assert status == 200 and body["move"] == "e2e4"
        assert "4P3" in req("GET", "/api/fen")[1]["fen"]
        assert len(req("GET", "/api/moves")[1]["moves"]) == 20
        with pytest.raises(urllib.error.HTTPError) as exc:  # illegal move
            req("POST", "/api/move", {"move": "e2e5"})
        assert exc.value.code == 400
        with pytest.raises(urllib.error.HTTPError) as exc:  # invalid FEN
            req("POST", "/api/load", {"fen": "8/8/8/8/8/8/8/8 w - - 0 1"})
        assert exc.value.code == 400
        with urllib.request.urlopen(base + "/", timeout=5) as resp:  # web UI
            html = resp.read()
        assert resp.status == 200 and b"<html" in html.lower()
    finally:
        proc.terminate()
        proc.wait(timeout=10)
