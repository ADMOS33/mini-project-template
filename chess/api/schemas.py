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
