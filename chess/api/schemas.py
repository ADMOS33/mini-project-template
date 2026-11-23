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
    """Body of ``POST /api/ai-move``."""

    depth: int = Field(3, ge=1, le=6, description="Search depth (1-4 in the UI)")


class FlagRequest(BaseModel):
    """Body of ``POST /api/flag``: the given color loses on time."""

    color: str = Field(..., pattern="^[wb]$", examples=["w"])
