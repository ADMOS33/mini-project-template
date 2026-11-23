# ♞ GUIDE — Chess : documentation, versions et mise en route

Projet universitaire (ENSEIRB-MATMECA, génie logiciel) — équipe **Adam, Hafsa, Rafiq**.
Un jeu d'échecs complet en Python pur (aucune bibliothèque d'échecs externe) :
moteur maison, CLI pensée pour les agents LLM, API HTTP (FastAPI), interface web
vanilla, serveur MCP, et un adversaire minimax + alpha-beta.

- Dépôt : fork de `rrobbes/mini-project-template`
- README détaillé (fonctionnalités, architecture, décisions) : `README.md`
- Retour d'expérience du cours : `report.md`
- Skill pour agent LLM : `skills/chess-cli/SKILL.md`

---

## 1. Démarrage rapide

```bash
# 1. Environnement virtuel + dépendances (fastapi, uvicorn, pytest — rien d'autre)
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# 2. Vérifier que tout est vert (perft standards inclus : 20 / 400 / 8902 / 197281
#    en position initiale, 48 / 2039 / 97862 en Kiwipete)
.venv/bin/python -m pytest

# 3. Lancer le serveur API + interface web (ne PAS lancer en tâche bloquante
#    dans une session agent : lancer dans un terminal dédié ou en arrière-plan)
.venv/bin/python -m uvicorn chess.api.server:app --reload --host 127.0.0.1 --port 8000
#   → interface web :  http://localhost:8000/
#   → docs API :       http://localhost:8000/docs
#   → API JSON :       http://localhost:8000/api/status

# 4. CLI (console script installé par pip)
.venv/bin/chess new --json
.venv/bin/chess move e2e4 --json
.venv/bin/chess moves --json
.venv/bin/chess board
.venv/bin/chess status --json
```

L'état de la partie est persisté dans `.chess_game.json` (racine du projet,
gitignoré) et **partagé entre CLI, API et MCP** : un coup joué en CLI apparaît
dans le navigateur en moins de 2 s (mode Spectateur + polling de `version`).

### Jouer avec un agent LLM (sans navigateur)

- **CLI** : `skills/chess-cli/SKILL.md` documente le contrat `--json` de chaque
  sous-commande (`new`, `move`, `moves`, `status`, `wait`, `ai-move`, `undo`,
  `pgn`, …). Boucle agent : `chess wait --color w --json` → `chess moves --json`
  → `chess move <coup> --json`.
- **MCP** : serveur JSON-RPC 2.0 maison, sans dépendance :
  `python -m chess.mcp` (un message JSON par ligne sur stdin/stdout).
  Outils : `new_game`, `get_board`, `get_status`, `legal_moves`, `play_move`,
  `ai_move`, `analyze_position`, `get_pgn`, `puzzle`, `solve`, `analyze_game`.
  Déclaration dans `~/.vibe/config.toml` : voir `README.md` § « Serveur MCP ».

---

## 2. Les versions (lots V1 → V13)

| Lot | Contenu | Statut |
|-----|---------|--------|
| V1 | Bugs visuels + robustesse front (toasts, rendus isolés, écran « API injoignable », `Cache-Control: no-cache`, `tests/test_web.py`) | ✅ |
| V2 | `web/` découpé en modules ES natifs (`web/js/*.js`, aucun build) | ✅ |
| V3 | Design system sombre, contrôles segmentés accessibles, 100 % français | ✅ |
| V4 | Mise en page façon lichess : cartes joueurs, panneau à onglets, modale « Nouvelle partie », mobile < 700 px, horloge avec perte au temps | ✅ |
| V5 | **Synchro live + agent** : compteur `version` dans l'état, polling 1 s, mode Spectateur, `chess wait --color w\|b` | ✅ |
| V6 | **Serveur MCP** maison (JSON-RPC 2.0 stdio, `python -m chess.mcp`) | ✅ |
| V7 | **Problèmes** : mats forcés en 1/2/3 coups, base vérifiée par le moteur (solution unique), CLI `puzzle`/`solve`, API, MCP, carte web + score/série | ✅ |
| V8 | **Actions de partie** (abandon, nulle par accord, reprendre) + **niveaux nommés** (Débutant ~600 → Expert ~1800, profondeur + marge d'aléa, RNG injectable) | ✅ |
| V9 | **Revue de partie** (étiquettes meilleur/…/gaffe/brillant, précision, courbe d'évaluation SVG) + **ouvertures ECO** (~56 lignes, recherche par préfixe) + bouton Indice | ✅ |
| V10 | **Interactions plateau** : flèches/cercles (clic droit), prémouvements, aperçu au survol de l'historique, raccourcis clavier, animations (y compris `prefers-reduced-motion`) | ✅ |
| V11 | **Personnalisation** (thèmes de plateau, mode clair/sombre, son, pièces) + **archive des parties** (`.chess_archive.json`, onglet Parties, stats) + **éditeur de position** | ✅ |
| V12 | **Chess960** : 960 positions SPN (n° 518 = standard), droits X-FEN en lettres de colonne, roque généralisé (« le roi prend sa tour » en UCI), non-régression perft | ✅ |
| V13 | Finitions : page « Aide agent », passe de cohérence, `report.md` | ✅ |

### Fonctionnalités du moteur (toutes testées, perft au vert)

Déplacements de toutes les pièces, coups légaux (roi jamais en échec), échec,
échec et mat, pat, petit/grand roque (toutes conditions), prise en passant,
promotion avec choix de la pièce, nulle par triple répétition, règle des 50
coups, matériel insuffisant, import/export **FEN** (avec validation) et **PGN**,
notations **UCI** (`e2e4`, `e7e8q`, roque Chess960 « le roi prend sa tour`) et
**SAN** (`Nf3`, `O-O`), perft de référence.

---

## 3. Utiliser la CLI (humain ou agent)

Toutes les commandes acceptent `--json` (sortie structurée pour un agent) et
l'option globale `--state PATH` (avant la sous-commande) pour changer le
fichier d'état.

```bash
chess new                       # nouvelle partie (standard)
chess new --chess960 518        # position Chess960 n° 518 (= standard), sans N = aléatoire
chess board                     # échiquier ASCII
chess move e2e4                 # UCI…
chess move Nf3                  # …ou SAN
chess moves                     # coups légaux (UCI + SAN)
chess status                    # au trait, échec, résultat, version, ouverture
chess undo                      # annuler le dernier coup
chess fen                       # FEN courante
chess load "<fen>"              # charger une position
chess pgn                       # exporter la partie en PGN
chess load-pgn partie.pgn       # charger un PGN
chess ai-move --depth 3         # l'ordinateur joue (minimax + alpha-beta)
chess ai-move --level expert    # niveau nommé (débutant…expert)
chess resign                    # abandon
chess offer-draw                # proposer la nulle
chess takeback                  # reprendre le dernier échange (vs ordinateur)
chess wait --color w --timeout 30 --json   # attendre le tour des Blancs (2 agents)
chess puzzle --level 2          # charger un problème (mat en 2)
chess solve g8g4                # jouer la solution / un coup du problème
chess games                     # archive des parties terminées
chess analyze --depth 2         # revue de partie (étiquettes + pertes)
chess history                   # historique UCI + SAN
```

Erreur de coup illégal → rc 1 + liste des coups légaux (lisible par un agent).

## 4. Utiliser l'API HTTP

`POST /api/new` (body optionnel `{mode, level, chess960}`), `/api/move`,
`/api/moves`, `/api/status` (avec `version` + `opening`), `/api/board`,
`/api/fen`, `/api/history`, `/api/pgn`, `/api/load`, `/api/load-pgn`,
`/api/undo`, `/api/ai-move` (`{depth}` ou `{level}`), `/api/eval`,
`/api/resign`, `/api/offer-draw`, `/api/takeback`, `/api/flag`,
`/api/puzzle`, `/api/solve`, `/api/analyze`, `/api/analyze-position`,
`/api/games`, `/api/games/{id}`.
Docs interactives : `http://localhost:8000/docs`.

## 5. Utiliser l'interface web

Ouvrir `http://localhost:8000/` :

- **Nouvelle partie** : 2 joueurs / contre l'ordinateur (couleur + niveau) /
  Spectateur (suit la partie CLI/MCP en direct) / Problèmes / Chess960 (n° 0–959).
- Jouer au clic-clic ou glisser-déposer ; coups légaux pointés, dernier coup
  surligné, roi en échec en rouge, promotion en fenêtre, flèches au clic droit.
- Panneau droit : onglets **Partie** (coups en SAN, navigation ⏮◀▶⏭, actions
  Abandonner/Proposer nulle/Reprendre) et **Outils** (FEN/PGN, évaluation,
  indice, revue de partie), plus **Parties** (archive) ; ⚙ réglages (thèmes,
  son, pièces) ; **?** aide agent.
- Modes : horloge optionnelle (perte au temps = défaite), retour du plateau,
  flipped auto en 2 joueurs.

## 6. Tests

```bash
.venv/bin/python -m pytest            # tout (les mats en 3 sont marqués slow)
.venv/bin/python -m pytest tests/test_perft.py   # perft de référence uniquement
```

---

*Généré dans le cadre du projet ; voir `report.md` pour la méthode et les chiffres.*
