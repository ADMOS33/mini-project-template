"""Game orchestration: playing moves, undo, status and JSON persistence."""

from __future__ import annotations

import json
from pathlib import Path

from chess.engine.board import Board
from chess.engine.fen import board_from_fen, board_to_fen
from chess.engine.move import Move
from chess.engine.movegen import apply_move, is_square_attacked, legal_moves


class Game:
    """A chess game: current position plus move history.

    The state can be serialized to/deserialized from a JSON file so the CLI
    and the HTTP API can share one persisted game.
    """

    def __init__(self, board: Board | None = None) -> None:
        self.board = board if board is not None else Board.initial()
        self.moves: list[Move] = []
        # FEN of the position before each ply, so undo is a simple pop.
        self._positions: list[str] = [board_to_fen(self.board)]
        # External end of game (not a chess rule, e.g. clock fall):
        # {"result": "flag", "winner": "b"} — blocks further moves.
        self.external_result: dict | None = None

    def set_external_result(self, result: str, winner: str | None = None) -> None:
        """Record an externally-decided end of game (e.g. flag fall)."""
        self.external_result = {"result": result, "winner": winner}

    @classmethod
    def from_fen(cls, fen: str) -> Game:
        """New game starting from a FEN position."""
        return cls(board_from_fen(fen))

    def legal_moves(self) -> list[Move]:
        """Legal moves for the side to move."""
        return legal_moves(self.board)

    def play_uci(self, uci: str) -> Move:
        """Play a UCI move. Raises ValueError listing legal moves if illegal."""
        if self.external_result is not None:
            raise ValueError(f"game is over ({self.external_result['result']})")
        move = Move.from_uci(uci)  # ValueError on malformed input
        legal = {m.to_uci(): m for m in self.legal_moves()}
        if move.to_uci() not in legal:
            legal_uci = " ".join(sorted(legal))
            raise ValueError(
                f"illegal move {move.to_uci()!r}; legal moves: {legal_uci}"
            )
        self.board = apply_move(self.board, legal[move.to_uci()])
        self.moves.append(move)
        # positions[i] = FEN after i plies, so undo is a simple pop.
        self._positions.append(board_to_fen(self.board))
        return move

    def undo(self) -> Move | None:
        """Take back the last move; returns it, or None if history is empty."""
        if not self.moves:
            return None
        move = self.moves.pop()
        self._positions.pop()
        self.board = board_from_fen(self._positions[-1])
        return move

    def position_fens(self) -> list[str]:
        """FEN after each ply: index 0 is the starting position."""
        return list(self._positions)

    def in_check(self) -> bool:
        """True if the side to move is in check."""
        return is_square_attacked(
            self.board,
            self.board.king_square(self.board.turn),
            self.board.turn.opposite,
        )

    def status(self) -> dict:
        """Game status as a JSON-serializable dict.

        End-of-game detection is delegated to :mod:`chess.engine.rules`;
        ``result`` is one of ``rules.RESULTS`` and ``winner`` is ``"w"``,
        ``"b"`` or ``None``.
        """
        from collections import Counter

        from chess.engine.rules import game_result, position_key

        # _positions[i] is the FEN after ply i, so the last entry is the
        # current position: counting all of them gives the repetition counts.
        repetitions = Counter(position_key(board_from_fen(fen)) for fen in self._positions)
        result, winner = game_result(self.board, repetitions)
        if self.external_result is not None:
            result = self.external_result["result"]
            winner = self.external_result.get("winner")
        return {
            "result": result,
            "winner": winner,
            "turn": str(self.board.turn),
            "in_check": self.in_check(),
            "legal_move_count": len(self.legal_moves()),
            "halfmove_clock": self.board.halfmove_clock,
            "fullmove_number": self.board.fullmove_number,
            "fen": board_to_fen(self.board),
        }

    def to_dict(self) -> dict:
        """JSON-serializable state."""
        return {
            "fen": board_to_fen(self.board),
            "moves": [m.to_uci() for m in self.moves],
            "positions": list(self._positions),
            "external_result": self.external_result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Game:
        """Rebuild a game from :meth:`to_dict` output.

        The position history is rebuilt by replaying the stored moves from the
        starting FEN, so ``undo`` always restores exactly one ply — even if the
        persisted ``positions`` list is missing or stale (legacy state files).
        Raises ValueError on a corrupted state.
        """
        moves = [Move.from_uci(u) for u in data.get("moves", [])]
        positions = data.get("positions") or []
        if positions:
            game = cls.from_fen(positions[0])
        elif moves:
            raise ValueError("corrupted game state: moves without a starting position")
        else:
            game = cls.from_fen(data["fen"])
        for move in moves:
            game.play_uci(move.to_uci())
        if board_to_fen(game.board) != data["fen"]:
            raise ValueError("corrupted game state: FEN does not match the move list")
        # Set after the replay so play_uci does not reject the stored moves.
        game.external_result = data.get("external_result")
        return game

    def save(self, path: str | Path) -> None:
        """Persist the game to a JSON file."""
        Path(path).write_text(json.dumps(self.to_dict(), indent=2) + "\n", encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> Game:
        """Load a game previously saved with :meth:`save`."""
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
