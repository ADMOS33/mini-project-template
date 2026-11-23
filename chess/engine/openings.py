"""ECO opening book (V9): ~60 common openings with a French name and UCI moves.

``lookup_opening`` finds the longest book line that is a prefix of the game's
move list. Only well-known, legal sequences are included — the test suite
replays every one of them through the engine.
"""

from __future__ import annotations

# (ECO code, French name, UCI moves)
OPENINGS: list[tuple[str, str, list[str]]] = [
    ("A04", "Ouverture Réti", ["g1f3", "d7d5", "c2c4"]),
    ("A10", "Attaque anglaise", ["c2c4"]),
    ("A13", "Anglaise, 2.Cc3", ["c2c4", "e7e5", "b1c3", "g8f6"]),
    ("A40", "Pion dame", ["d2d4"]),
    ("A80", "Défense hollandaise", ["d2d4", "f7f5"]),
    ("B01", "Défense scandinave", ["e2e4", "d7d5"]),
    ("B06", "Défense moderne", ["e2e4", "g7g6", "d2d4", "f8g7"]),
    ("B07", "Défense Pirc", ["e2e4", "d7d6", "d2d4", "g8f6", "b1c3", "g7g6"]),
    ("B10", "Défense Caro-Kann", ["e2e4", "c7c6", "d2d4", "d7d5"]),
    ("B12", "Caro-Kann, variante d'avance", ["e2e4", "c7c6", "d2d4", "d7d5", "e4e5"]),
    ("B20", "Défense sicilienne", ["e2e4", "c7c5"]),
    ("B21", "Sicilienne, 2.Cc3", ["e2e4", "c7c5", "b1c3"]),
    ("B22", "Sicilienne, variante Alapin", ["e2e4", "c7c5", "c2c3"]),
    ("B23", "Sicilienne fermée", ["e2e4", "c7c5", "g2g3"]),
    ("B30", "Sicilienne classique", ["e2e4", "c7c5", "g1f3", "b8c6", "d2d4", "c5d4", "f3d4"]),
    ("B33", "Sicilienne Sveshnikov", ["e2e4", "c7c5", "g1f3", "b8c6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "e7e5"]),
    ("B50", "Sicilienne, 3.Fd2", ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "c1d2"]),
    ("B70", "Sicilienne, variante du dragon", ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "g7g6"]),
    ("B80", "Sicilienne, variante de Scheveningue", ["e2e4", "c7c5", "g1f3", "e7e6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "d7d6"]),
    ("B90", "Sicilienne, variante Najdorf", ["e2e4", "c7c5", "g1f3", "d7d6", "d2d4", "c5d4", "f3d4", "g8f6", "b1c3", "a7a6"]),
    ("C00", "Défense française", ["e2e4", "e7e6", "d2d4", "d7d5"]),
    ("C01", "Française, variante d'échange", ["e2e4", "e7e6", "d2d4", "d7d5", "e4d5", "e6d5"]),
    ("C02", "Française, variante d'avance", ["e2e4", "e7e6", "d2d4", "d7d5", "e4e5"]),
    ("C07", "Française, variante Tarrasch", ["e2e4", "e7e6", "d2d4", "d7d5", "b1d2"]),
    ("C11", "Française, variante Steinitz", ["e2e4", "e7e6", "d2d4", "d7d5", "b1c3", "g8f6", "e4e5"]),
    ("C15", "Française, variante Winawer", ["e2e4", "e7e6", "d2d4", "d7d5", "b1c3", "f8b4"]),
    ("C21", "Gambit danois", ["e2e4", "e7e5", "d2d4", "e5d4", "c2c3"]),
    ("C25", "Partie viennoise", ["e2e4", "e7e5", "b1c3", "g8f6"]),
    ("C30", "Gambit du roi", ["e2e4", "e7e5", "f2f4"]),
    ("C33", "Gambit du roi accepté", ["e2e4", "e7e5", "f2f4", "e5f4"]),
    ("C41", "Défense Philidor", ["e2e4", "e7e5", "g1f3", "d7d6"]),
    ("C42", "Défense Petrov", ["e2e4", "e7e5", "g1f3", "g8f6"]),
    ("C44", "Écossaise (Scotch)", ["e2e4", "e7e5", "g1f3", "b8c6", "d2d4"]),
    ("C47", "Partie des quatre cavaliers", ["e2e4", "e7e5", "g1f3", "b8c6", "b1c3", "g8f6"]),
    ("C50", "Partie italienne", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]),
    ("C51", "Gambit Evans", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5", "b2b4"]),
    ("C53", "Giuoco piano", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"]),
    ("C55", "Défense des deux cavaliers", ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6"]),
    ("C60", "Partie espagnole (Ruy Lopez)", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]),
    ("C65", "Espagnole, défense berlinoise (4.d3)", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "g8f6", "d2d3"]),
    ("C67", "Espagnole, défense berlinoise", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "g8f6"]),
    ("C68", "Espagnole, variante d'échange", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5c6", "d7c6"]),
    ("C78", "Espagnole fermée", ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6", "b5a4", "g8f6", "e1g1"]),
    ("D06", "Gambit dame accepté", ["d2d4", "d7d5", "c2c4", "d5c4"]),
    ("D10", "Défense slave", ["d2d4", "d7d5", "c2c4", "c7c6"]),
    ("D30", "Gambit dame refusé", ["d2d4", "d7d5", "c2c4", "e7e6"]),
    ("D35", "Gambit dame refusé, variante d'échange", ["d2d4", "d7d5", "c2c4", "e7e6", "c4d5", "e6d5"]),
    ("D37", "Gambit dame refusé, orthodoxe", ["d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "g1f3", "f8e7", "c1f4"]),
    ("D43", "Semi-slave", ["d2d4", "d7d5", "c2c4", "e7e6", "b1c3", "g8f6", "g1f3", "c7c6", "c1g5"]),
    ("D70", "Défense Grünfeld", ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5"]),
    ("D80", "Grünfeld, ligne principale", ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5", "c4d5", "f6d5"]),
    ("D85", "Grünfeld, variante d'échange", ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "d7d5", "c4d5", "f6d5", "e2e4", "d5c3", "b2c3"]),
    ("E00", "Ouverture catalane", ["d2d4", "g8f6", "c2c4", "e7e6", "g2g3", "d7d5"]),
    ("E04", "Catalane, variante ouverte", ["d2d4", "g8f6", "c2c4", "e7e6", "g2g3", "d7d5", "c4d5", "e6d5"]),
    ("E11", "Défense bogoljubov (bogo-indienne)", ["d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "f8b4"]),
    ("E12", "Défense dame-indienne", ["d2d4", "g8f6", "c2c4", "e7e6", "g1f3", "b7b6"]),
    ("E20", "Défense nimzo-indienne", ["d2d4", "g8f6", "c2c4", "e7e6", "b1c3", "f8b4"]),
    ("E60", "Défense est-indienne", ["d2d4", "g8f6", "c2c4", "g7g6", "b1c3", "f8g7", "e2e4", "d7d6"]),
]


def lookup_opening(uci_moves: list[str]) -> dict | None:
    """Longest book line that is a prefix of ``uci_moves``.

    Returns ``{"code", "name", "matched_plies"}`` or None.
    """
    best: tuple[str, str, list[str]] | None = None
    for code, name, line in OPENINGS:
        n = len(line)
        if n <= len(uci_moves) and uci_moves[:n] == line:
            if best is None or n > len(best[2]):
                best = (code, name, line)
    if best is None:
        return None
    code, name, line = best
    return {"code": code, "name": name, "matched_plies": len(line)}
