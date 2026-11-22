"""Piece types, colors and piece identity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Color(Enum):
    """The two sides of a chess game."""

    WHITE = "w"
    BLACK = "b"

    @property
    def opposite(self) -> Color:
        """The other color."""
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    def __str__(self) -> str:
        return self.value


class PieceType(Enum):
    """The six chess piece types, named by their FEN letter."""

    PAWN = "p"
    KNIGHT = "n"
    BISHOP = "b"
    ROOK = "r"
    QUEEN = "q"
    KING = "k"

    def __str__(self) -> str:
        return self.value


# Unicode glyphs for the web UI (white U+2654..2659, black U+265A..265F).
_GLYPHS = {
    PieceType.KING: ("♔", "♚"),
    PieceType.QUEEN: ("♕", "♛"),
    PieceType.ROOK: ("♖", "♜"),
    PieceType.BISHOP: ("♗", "♝"),
    PieceType.KNIGHT: ("♘", "♞"),
    PieceType.PAWN: ("♙", "♟"),
}


@dataclass(frozen=True)
class Piece:
    """A piece: a type plus a color."""

    type: PieceType
    color: Color

    @property
    def symbol(self) -> str:
        """FEN-style letter: uppercase for White, lowercase for Black."""
        letter = self.type.value
        return letter.upper() if self.color is Color.WHITE else letter

    @property
    def glyph(self) -> str:
        """Unicode chess glyph for this piece."""
        white, black = _GLYPHS[self.type]
        return white if self.color is Color.WHITE else black

    @classmethod
    def from_symbol(cls, symbol: str) -> Piece:
        """Build a piece from its FEN letter (e.g. ``'Q'``, ``'p'``)."""
        if len(symbol) != 1 or not symbol.isalpha():
            raise ValueError(f"invalid piece symbol: {symbol!r}")
        color = Color.WHITE if symbol.isupper() else Color.BLACK
        try:
            piece_type = PieceType(symbol.lower())
        except ValueError as exc:
            raise ValueError(f"invalid piece symbol: {symbol!r}") from exc
        return cls(piece_type, color)
