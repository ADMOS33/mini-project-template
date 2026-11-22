"""Allow running the CLI with ``python -m chess``."""

from chess.cli.main import main

if __name__ == "__main__":
    raise SystemExit(main())
