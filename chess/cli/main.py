"""Command-line interface for the chess game.

Designed to be usable by humans and by LLM agents alike: every subcommand
accepts ``--json`` for structured output, and the game state is persisted in
a local JSON file (``.chess_game.json`` in the current directory by default,
override with the global ``--state PATH`` option).

Usage: ``chess [--state PATH] <command> [args] [--json]``
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from chess.ai.search import best_move
from chess.engine.fen import board_from_fen, board_to_fen
from chess.engine.game import Game
from chess.engine.move import Move
from chess.engine.pgn import export_pgn, import_pgn
from chess.engine.san import move_to_san, san_to_move

DEFAULT_STATE_FILE = ".chess_game.json"


class CliError(Exception):
    """A user-facing error (message printed, exit code 1)."""


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chess",
        description="Play chess in the terminal — human- and agent-friendly.",
    )
    parser.add_argument(
        "--state",
        default=DEFAULT_STATE_FILE,
        help=f"path to the JSON game-state file (default: {DEFAULT_STATE_FILE})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    json_parent = argparse.ArgumentParser(add_help=False)
    json_parent.add_argument(
        "--json", action="store_true", help="print structured JSON (for agents)"
    )

    def add(name: str, help_text: str) -> argparse.ArgumentParser:
        return sub.add_parser(name, help=help_text, parents=[json_parent])

    add("new", "start a new game")
    add("board", "print the board (ASCII)")
    add("moves", "list the legal moves (UCI)")
    p_move = add("move", "play a move (UCI, e.g. e2e4 or e7e8q)")
    p_move.add_argument("move", help="move in UCI notation")
    add("status", "game status: side to move, check, result")
    add("undo", "take back the last move")
    add("fen", "print the FEN of the current position")
    p_load = add("load", "start a game from a FEN string")
    p_load.add_argument("fen", help="FEN string")
    add("pgn", "export the game as PGN")
    p_load_pgn = add("load-pgn", "load a game from a PGN file")
    p_load_pgn.add_argument("file", help="path to a .pgn file")
    p_ai = add("ai-move", "let the computer play a move (minimax + alpha-beta)")
    p_ai.add_argument("--depth", type=int, default=3, help="search depth")
    add("history", "list the moves played so far")
    return parser


def _load_game(state_file: Path) -> Game:
    if not state_file.exists():
        raise CliError(
            f"no game in progress ({state_file} not found) — run `chess new` first"
        )
    try:
        return Game.load(state_file)
    except (ValueError, KeyError, json.JSONDecodeError) as exc:
        raise CliError(f"could not load game state from {state_file}: {exc}") from exc


def _play_notation(game: Game, text: str) -> Move:
    """Play a move given in UCI (``e2e4``) or SAN (``Nf3``) notation."""
    try:
        uci_move = Move.from_uci(text)
    except ValueError:
        uci_move = None
    if uci_move is not None:
        try:
            return game.play_uci(uci_move.to_uci())
        except ValueError as exc:
            raise CliError(str(exc)) from exc
    try:
        move = san_to_move(game.board, text)
    except ValueError:
        legal = " ".join(sorted(m.to_uci() for m in game.legal_moves()))
        raise CliError(
            f"illegal move {text!r} (neither UCI nor SAN); legal moves: {legal}"
        ) from None
    return game.play_uci(move.to_uci())


def _legal_move_details(game: Game) -> list[dict]:
    """[{uci, san}] for the legal moves of the side to move."""
    return [
        {"uci": m.to_uci(), "san": move_to_san(game.board, m)}
        for m in sorted(game.legal_moves(), key=lambda m: m.to_uci())
    ]


def _history_details(game: Game) -> list[dict]:
    """[{uci, san}] for the moves played so far (SAN from each past position)."""
    fens = game.position_fens()
    return [
        {"uci": m.to_uci(), "san": move_to_san(board_from_fen(fens[i]), m)}
        for i, m in enumerate(game.moves)
    ]


def _status_text(status: dict) -> str:
    turn = "White" if status["turn"] == "w" else "Black"
    lines = [f"{turn} to move (move {status['fullmove_number']})"]
    if status["in_check"]:
        lines.append("check!")
    lines.append(f"result: {status['result']}")
    lines.append(f"fen: {status['fen']}")
    return "\n".join(lines)


def _dispatch(args: argparse.Namespace, state_file: Path) -> tuple[dict, str]:
    """Run one subcommand; returns (json_payload, human_text)."""
    cmd = args.command
    if cmd == "new":
        game = Game()
        game.save(state_file)
        status = game.status()
        return {"ok": True, "status": status}, f"New game started.\n{status['fen']}"
    if cmd == "load":
        try:
            game = Game.from_fen(args.fen)
        except ValueError as exc:
            raise CliError(f"invalid FEN: {exc}") from exc
        game.save(state_file)
        status = game.status()
        return {"ok": True, "status": status}, f"Loaded position.\n{status['fen']}"
    if cmd == "ai-move":
        game = _load_game(state_file)
        if game.status()["result"] != "ongoing":
            raise CliError("game is over — no AI move to play")
        depth = max(1, min(args.depth, 6))
        start = time.perf_counter()
        move, score, nodes = best_move(game.board, depth)
        time_ms = round((time.perf_counter() - start) * 1000, 1)
        san = move_to_san(game.board, move)
        game.play_uci(move.to_uci())
        game.save(state_file)
        status = game.status()
        return (
            {
                "ok": True,
                "move": move.to_uci(),
                "san": san,
                "score": score,
                "nodes": nodes,
                "time_ms": time_ms,
                "depth": depth,
                "status": status,
            },
            f"AI played {move.to_uci()} ({san}) — score {score}, {nodes} nodes "
            f"in {time_ms} ms.\n{_status_text(status)}",
        )
    if cmd == "pgn":
        game = _load_game(state_file)
        text = export_pgn(game)
        return {"pgn": text}, text
    if cmd == "load-pgn":
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            raise CliError(f"cannot read {args.file}: {exc}") from exc
        try:
            game = import_pgn(text)
        except ValueError as exc:
            raise CliError(f"invalid PGN in {args.file}: {exc}") from exc
        game.save(state_file)
        status = game.status()
        return (
            {"ok": True, "status": status},
            f"Loaded PGN from {args.file} ({len(game.moves)} plies).\n{status['fen']}",
        )

    game = _load_game(state_file)
    if cmd == "board":
        return (
            {"fen": board_to_fen(game.board), "turn": str(game.board.turn), "ascii": game.board.ascii()},
            game.board.ascii() + f"\n{game.status()['turn']} to move",
        )
    if cmd == "moves":
        details = _legal_move_details(game)
        moves = [d["uci"] for d in details]
        text = "\n".join(f"{d['uci']} ({d['san']})" for d in details)
        return {"moves": moves, "details": details}, text
    if cmd == "move":
        try:
            move = _play_notation(game, args.move)
        except CliError:
            raise
        except ValueError as exc:
            raise CliError(str(exc)) from exc
        game.save(state_file)
        status = game.status()
        return (
            {"ok": True, "move": move.to_uci(), "status": status},
            f"Played {move.to_uci()}.\n{_status_text(status)}",
        )
    if cmd == "status":
        status = game.status()
        return status, _status_text(status)
    if cmd == "undo":
        move = game.undo()
        if move is None:
            raise CliError("no moves to undo")
        game.save(state_file)
        status = game.status()
        return {"ok": True, "undone": move.to_uci(), "status": status}, f"Undone {move.to_uci()}."
    if cmd == "fen":
        fen = board_to_fen(game.board)
        return {"fen": fen}, fen
    if cmd == "history":
        details = _history_details(game)
        text = (
            "\n".join(f"{i + 1}. {d['uci']} ({d['san']})" for i, d in enumerate(details))
            or "no moves yet"
        )
        return {"moves": [d["uci"] for d in details], "details": details}, text
    raise CliError(f"unknown command: {cmd}")  # pragma: no cover


def main(argv: list[str] | None = None) -> int:
    """Entry point of the ``chess`` command."""
    args = _build_parser().parse_args(argv)
    try:
        payload, text = _dispatch(args, Path(args.state))
    except CliError as exc:
        if getattr(args, "json", False):
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"error: {exc}", file=sys.stderr)
        return 1
    if getattr(args, "json", False):
        print(json.dumps(payload, indent=2))
    else:
        print(text)
    return 0
