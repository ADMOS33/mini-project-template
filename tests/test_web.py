"""Static checks for web/ — pure stdlib, no new dependency, no HTTP client.

- every id used by getElementById() / querySelector("#…") in web/*.js must
  exist in web/index.html (dynamically built ids are whitelisted below);
- every local file referenced by index.html (<script src>, <link href>) and
  by the JS/CSS (pieces/*.svg, including the 12 dynamically built piece
  paths) must exist on disk.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
INDEX_HTML = (WEB / "index.html").read_text(encoding="utf-8")
JS_SOURCE = "\n".join(p.read_text(encoding="utf-8") for p in sorted(WEB.glob("*.js")))
CSS_SOURCE = (WEB / "style.css").read_text(encoding="utf-8")

# Ids construits dynamiquement dans board.js, ex.:
#   getElementById("pname-" + cardId.split("-")[1])  -> pname-top / pname-bottom
#   getElementById(cardId / capId / avId / elId)      -> listes ci-dessous
DYNAMIC_IDS = {
    "pname-top", "pname-bottom",
    "avatar-top", "avatar-bottom",
    "captured-top", "captured-bottom",
    "player-top", "player-bottom",
    "clock-top", "clock-bottom",
}
# Expressions dynamiques connues de getElementById(...) ; toute nouvelle
# expression dynamique doit être ajoutée ici (le test échoue sinon).
# "pname-" + … est un préfixe concaténé (ids pname-top / pname-bottom).
KNOWN_DYNAMIC_CALLS = {"avId", "capId", "cardId", "elId"}
KNOWN_DYNAMIC_PREFIXES = ('"pname-"',)


def _is_known_dynamic(call: str) -> bool:
    return call in KNOWN_DYNAMIC_CALLS or call.startswith(KNOWN_DYNAMIC_PREFIXES)

PIECE_TYPES = "PNBRQK"


def _literal_ids() -> set[str]:
    """Ids passés en littéral pur : getElementById("board")."""
    return set(re.findall(r'getElementById\(\s*"([^"]+)"\s*\)', JS_SOURCE))


def _dynamic_calls() -> list[str]:
    """Appels getElementById(...) qui ne sont PAS un littéral pur."""
    calls = re.findall(r"getElementById\(([^)]*)\)", JS_SOURCE)
    return [c.strip() for c in calls if not re.fullmatch(r'"[^"]+"', c.strip())]


def _query_selector_ids() -> set[str]:
    selectors = re.findall(r"querySelector(?:All)?\(\s*[`'\"]([^`'\"]+)[`'\"]", JS_SOURCE)
    ids = set()
    for sel in selectors:
        m = re.search(r"#([A-Za-z0-9_-]+)", sel)
        if m:
            ids.add(m.group(1))
    return ids


def _html_ids() -> set[str]:
    return set(re.findall(r'id="([^"]+)"', INDEX_HTML))


def test_all_js_ids_exist_in_index_html() -> None:
    used = _literal_ids() | DYNAMIC_IDS | _query_selector_ids()
    unknown_dynamic = [c for c in _dynamic_calls() if not _is_known_dynamic(c)]
    assert not unknown_dynamic, (
        f"nouveau getElementById dynamique à whitelister dans KNOWN_DYNAMIC_CALLS: {unknown_dynamic}"
    )
    missing = sorted(i for i in used if i not in _html_ids())
    assert not missing, f"ids utilisés en JS mais absents de web/index.html: {missing}"


def test_referenced_local_files_exist() -> None:
    refs: set[str] = set()
    for attr in re.findall(r'(?:src|href)="([^"]+)"', INDEX_HTML):
        if attr.startswith(("http://", "https://", "#", "mailto:")):
            continue
        refs.add("index.html" if attr == "/" else attr.lstrip("/"))
    refs |= set(re.findall(r'["\'`]([\w./-]+\.(?:svg|css|js|png|html|ico))["\'`]', JS_SOURCE))
    refs |= set(re.findall(r'url\(\s*["\']?([\w./-]+\.(?:svg|png))["\']?\s*\)', CSS_SOURCE))
    # chemins de pièces construits dynamiquement : pieces/{w|b}{P,N,B,R,Q,K}.svg
    for color in "wb":
        for t in PIECE_TYPES:
            refs.add(f"pieces/{color}{t}.svg")
    missing = sorted(r for r in refs if not (WEB / r).is_file())
    assert not missing, f"fichiers référencés mais absents de web/: {missing}"


def test_piece_svg_set_is_complete() -> None:
    for color in "wb":
        for t in PIECE_TYPES:
            path = WEB / "pieces" / f"{color}{t}.svg"
            assert path.is_file(), f"{path.name} manquante"
            assert path.stat().st_size > 0, f"{path.name} est vide"


@pytest.mark.slow
def test_web_files_served_with_no_cache(tmp_path) -> None:
    """Live check (urllib only, no new dependency): uvicorn in a subprocess,
    stopped at the end. Every file served from web/ must carry
    'Cache-Control: no-cache' so a reload never shows a stale UI."""
    import os
    import socket
    import subprocess
    import sys
    import time
    import urllib.request

    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    env = dict(os.environ, CHESS_STATE_FILE=str(tmp_path / ".chess_game.json"))
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "chess.api.server:app",
         "--host", "127.0.0.1", "--port", str(port)],
        cwd=ROOT, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    base = f"http://127.0.0.1:{port}"
    try:
        for _ in range(100):  # wait until the server answers
            try:
                with urllib.request.urlopen(base + "/api/status", timeout=5):
                    break
            except Exception:
                time.sleep(0.1)
        else:
            raise RuntimeError("uvicorn did not start")
        for path in ("/", "/index.html", "/style.css", "/board.js", "/api.js", "/pieces/wK.svg"):
            with urllib.request.urlopen(base + path, timeout=5) as resp:
                cc = resp.headers.get("Cache-Control", "")
                assert "no-cache" in cc, f"{path}: Cache-Control={cc!r} (no-cache attendu)"
    finally:
        proc.terminate()
        proc.wait(timeout=10)
