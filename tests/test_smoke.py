"""Smoke test: the package skeleton imports cleanly."""

import chess


def test_package_exposes_version() -> None:
    assert chess.__version__ == "0.1.0"
