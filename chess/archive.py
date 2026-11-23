"""Game archive (V11): finished games are appended to ``.chess_archive.json``
(gitignored, local runtime data). Shared by the CLI and the HTTP API.

An entry: ``{id, date, mode, level, result, winner, moves_count, opening, pgn}``.
A game is archived exactly once (``meta["archived"]`` flag), when its result
becomes non-ongoing — and before being replaced by a new game.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from chess.engine.game import Game
from chess.engine.openings import lookup_opening
from chess.engine.pgn import export_pgn

ARCHIVE_FILE = Path(os.environ.get("CHESS_ARCHIVE_FILE", ".chess_archive.json"))


def default_archive_file() -> Path:
    """Archive path resolved at call time (CHESS_ARCHIVE_FILE env, default .chess_archive.json)."""
    return Path(os.environ.get("CHESS_ARCHIVE_FILE", ".chess_archive.json"))


def load_archive(path: str | Path | None = None) -> list[dict]:
    p = Path(path) if path is not None else default_archive_file()
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def append_archive(entry: dict, path: str | Path | None = None) -> None:
    path = path if path is not None else default_archive_file()
    entries = load_archive(path)
    entries.append(entry)
    Path(path).write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def archive_game(game: Game, path: str | Path | None = None) -> dict | None:
    if path is None:
        path = default_archive_file()
    """Archive ``game`` if it is over and not yet archived. Returns the entry or None."""
    status = game.status()
    if status["result"] == "ongoing" or game.meta.get("archived"):
        return None
    entries = load_archive(path)
    opening = lookup_opening([m.to_uci() for m in game.moves])
    entry = {
        "id": (entries[-1]["id"] + 1) if entries else 1,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mode": game.meta.get("mode", "2 joueurs"),
        "level": game.meta.get("level"),
        "result": status["result"],
        "winner": status["winner"],
        "moves_count": len(game.moves),
        "opening": opening,
        "pgn": export_pgn(game),
    }
    append_archive(entry, path)
    game.meta["archived"] = True
    game.version += 1
    return entry


def save_game(game: Game, state_file: str | Path, archive_path: str | Path | None = None) -> None:
    """Archive if over, then persist the state file."""
    archive_game(game, archive_path)
    game.save(state_file)


def archive_current(state_file: str | Path, archive_path: str | Path | None = None) -> dict | None:
    """Archive the persisted game (e.g. before starting a new one)."""
    p = Path(state_file)
    if not p.exists():
        return None
    try:
        game = Game.load(p)
    except Exception:
        return None
    entry = archive_game(game, archive_path)
    if entry is not None:
        game.save(p)
    return entry
