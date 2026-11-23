"""MCP tool registry — stub for the protocol-only commit.

The real tools are added in the next commit (outils).
"""

from __future__ import annotations

TOOLS: list[dict] = []


def tool_names() -> set[str]:
    return {t["name"] for t in TOOLS}


def call_tool(name: str, arguments: dict) -> dict:
    raise ValueError(f"unknown tool: {name!r}")
