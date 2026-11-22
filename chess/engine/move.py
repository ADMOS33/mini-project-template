"""Move representation and UCI notation."""

from __future__ import annotations

from dataclasses import dataclass

from chess.engine.board import parse_square, square_name
from chess.engine.pieces import PieceType

#: Promotion choices offered when a pawn reaches the last rank.
PROMOTION_TYPES = (PieceType.QUEEN, PieceType.ROOK, PieceType.BISHOP, PieceType.KNIGHT)


@dataclass(frozen=True)
class Move:
    """A move: origin square, destination square, optional promotion piece.

    Castling, en-passant and double-push flags are derived from the squares
    at application time, so they are not stored here.
    """

    from_sq: int
    to_sq: int
    promotion: PieceType | None = None

    def to_uci(self) -> str:
        """UCI notation, e.g. ``e2e4`` or ``e7e8q``."""
        uci = square_name(self.from_sq) + square_name(self.to_sq)
        if self.promotion is not None:
            uci += self.promotion.value
        return uci

    @classmethod
    def from_uci(cls, uci: str) -> Move:
        """Parse UCI notation. Raises ValueError on malformed input."""
        text = uci.strip().lower()
        if len(text) not in (4, 5):
            raise ValueError(f"invalid UCI move: {uci!r} (expected e.g. 'e2e4' or 'e7e8q')")
        try:
            from_sq = parse_square(text[:2])
            to_sq = parse_square(text[2:4])
        except ValueError as exc:
            raise ValueError(f"invalid UCI move: {uci!r} ({exc})") from exc
        promotion: PieceType | None = None
        if len(text) == 5:
            try:
                promotion = PieceType(text[4])
            except ValueError as exc:
                raise ValueError(f"invalid promotion piece in UCI move: {uci!r}") from exc
            if promotion in (PieceType.PAWN, PieceType.KING):
                raise ValueError(f"cannot promote to {promotion} in UCI move: {uci!r}")
        return cls(from_sq, to_sq, promotion)
