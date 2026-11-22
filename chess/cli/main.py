"""Command-line interface for the chess game.

The CLI is designed to be usable both by humans and by LLM agents: every
command supports a ``--json`` flag for structured output, and the game state
is persisted in ``.chess_game.json`` at the project root.

Subcommands: ``new``, ``board``, ``move``, ``moves``, ``status``, ``undo``,
``fen``, ``load``, ``pgn``, ``ai-move``, ``history``.
"""

from __future__ import annotations


def main(argv: list[str] | None = None) -> int:
    """Entry point of the ``chess`` command (skeleton, not implemented yet)."""
    print("chess CLI skeleton — the engine is not implemented yet.")
    return 0
