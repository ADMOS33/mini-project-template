"""Pydantic request schemas for the HTTP API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MoveRequest(BaseModel):
    """Body of ``POST /api/move``."""

    move: str = Field(..., examples=["e2e4", "e7e8q"], description="Move in UCI notation")


class LoadRequest(BaseModel):
    """Body of ``POST /api/load``."""

    fen: str = Field(
        ...,
        examples=["rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"],
        description="FEN of the position to load",
    )


class PgnRequest(BaseModel):
    """Body of ``POST /api/load-pgn``."""

    pgn: str = Field(..., examples=['[Event "Casual"]\n\n1. e4 e5 2. Nf3 Nc6 *'])


class AiMoveRequest(BaseModel):
    """Body of ``POST /api/ai-move``: ``depth`` or a named ``level`` (V8)."""

    depth: int = Field(3, ge=1, le=6, description="Search depth (used when no level)")
    level: str | None = Field(
        None,
        description="Named level: debutant, novice, club, confirme, expert (overrides depth)",
    )


class FlagRequest(BaseModel):
    """Body of ``POST /api/flag``: the given color loses on time."""

    color: str = Field(..., pattern="^[wb]$", examples=["w"])


class OfferDrawRequest(BaseModel):
    """Body of ``POST /api/offer-draw``.

    ``force=True`` records the draw immediately (2-player mode). Otherwise the
    computer (the side NOT to move) accepts only if its evaluation is <= 0.
    """

    force: bool = Field(False, description="Record the draw without the AI check")


class PuzzleRequest(BaseModel):
    """Body of ``POST /api/puzzle``."""

    level: int = Field(1, ge=1, le=3, description="Mate in n")
    index: int | None = Field(None, description="Deterministic pick within the level")
    seed: int | None = Field(None, description="Random pick with this seed")


class SolveRequest(BaseModel):
    """Body of ``POST /api/solve``."""

    move: str = Field(..., examples=["d8h4", "Qh4#"], description="Move in UCI or SAN")
