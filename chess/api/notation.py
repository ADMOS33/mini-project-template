"""PGN import/export for the API layer.

SAN rendering/parsing itself lives in the engine (``chess/engine/san.py``);
this module only adapts it to PGN movetext and re-exports ``to_san`` for the
server endpoints.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from chess.engine.board import Board
from chess.engine.fen import board_from_fen
from chess.engine.game import Game
from chess.engine.move import Move
from chess.engine.san import move_to_san, san_to_move

#: Re-exported for the API endpoints (history, PGN export).
to_san = move_to_san


def pgn_export(game: Game) -> str:
    """Export a game as a PGN string (headers + movetext in SAN)."""
    fens = game.position_fens()
    sans = [to_san(board_from_fen(fens[i]), move) for i, move in enumerate(game.moves)]
    status = game.status()
    if status["result"] == "checkmate":
        result = "1-0" if status["winner"] == "w" else "0-1"
    elif status["result"] == "ongoing":
        result = "*"
    else:
        result = "1/2-1/2"
    pairs = []
    for i in range(0, len(sans), 2):
        num = i // 2 + 1
        pair = f"{num}. {sans[i]}"
        if i + 1 < len(sans):
            pair += f" {sans[i + 1]}"
        pairs.append(pair)
    movetext = " ".join(pairs) + (" " if pairs else "") + result
    date = datetime.now(timezone.utc).strftime("%Y.%m.%d")
    headers = [
        '[Event "Chess web game"]',
        '[Site "http://localhost:8000/"]',
        f'[Date "{date}"]',
        '[Round "-"]',
        '[White "Blancs"]',
        '[Black "Noirs"]',
        f'[Result "{result}"]',
    ]
    return "\n".join(headers) + "\n\n" + movetext + "\n"


def pgn_import(text: str) -> tuple[str | None, list[str]]:
    """Parse a PGN string into (start FEN or None, list of UCI moves).

    Raises ValueError on an unknown or illegal SAN move.
    """
    match = re.search(r'\[FEN\s+"([^"]+)"\]', text)
    start_fen = match.group(1) if match else None
    body = re.sub(r"\[[^\]]*\]", " ", text)  # header lines
    body = re.sub(r"\{[^}]*\}", " ", body)  # comments
    body = re.sub(r"\([^)]*\)", " ", body)  # variations (non-nested)
    body = re.sub(r"\$\d+", " ", body)  # NAGs
    game = Game.from_fen(start_fen) if start_fen else Game()
    uci_moves: list[str] = []
    for raw in body.split():
        token = raw.strip()
        if not token or re.fullmatch(r"\d+\.", token) or token in ("1-0", "0-1", "1/2-1/2", "*"):
            continue
        try:
            move = san_to_move(game.board, token)
        except ValueError as exc:
            raise ValueError(f"coup SAN inconnu ou illégal dans le PGN: {token!r}") from exc
        game.play_uci(move.to_uci())
        uci_moves.append(move.to_uci())
    return start_fen, uci_moves
