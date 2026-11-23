# ♞ Chess — un jeu d'échecs complet en Python

Projet de groupe de génie logiciel (ENSEIRB-MATMECA), développé avec l'agent
**Vibe**. Moteur d'échecs écrit **à la main** en Python pur (aucune bibliothèque
d'échecs externe), accompagné d'une **CLI utilisable par un agent LLM**, d'une
**API HTTP (FastAPI)**, d'une **interface web jouable** (HTML/CSS/JS vanilla) et
d'un **adversaire classique** (minimax + élagage alpha-beta, pas d'IA générative).

> Ce dépôt est un fork du
> [mini-project-template](https://github.com/rrobbes/mini-project-template) :
> le hook enregistre l'activité de développement dans `events/` pour
> l'évaluation du cours. **Ne jamais modifier `events/` ni `.vibe/`, et ne
> jamais gitignorer `events/`** (les logs sont commités volontairement).

## Équipe

| Membre | Périmètre |
|--------|-----------|
| **Rafiq** | Moteur d'échecs — `chess/engine/` |
| **Adam**  | CLI, API HTTP, IA — `chess/cli/`, `chess/api/`, `chess/ai/` |
| **Agent (Vibe)** | Interface web — `web/` (développée par l'agent, relue par l'équipe) |

## Fonctionnalités

> Légende : ✅ implémenté et testé · 🚧 prévu mais pas encore fait.

- **Règles du moteur** (`chess/engine/`) :
  - ✅ déplacements de toutes les pièces, coups légaux (le roi ne peut jamais
    rester en échec), échec, échec et mat, pat, promotion avec choix de la
    pièce, règle des 50 coups ;
  - ✅ petit et grand roque, deux camps (droit présent, tour en place, cases
    intermédiaires vides, roi ni en échec ni en transit/arrivée sur case
    attaquée — la tour bouge aussi, UCI `e1g1`/`e1c1`) ;
  - ✅ prise en passant (génération + application, le pion pris disparaît de
    sa propre case ; le piège du clouage est correctement rejeté) ;
  - ✅ nulle par triple répétition (clé = placement + trait + roques + case
    en passant seulement si une prise y est réellement jouable) ;
  - ✅ matériel insuffisant (K-K, KB-K, KN-K, KB-KB fous de même couleur).
- **Notations et formats** : ✅ **FEN** (import/export), ✅ **UCI** (`e2e4`,
  `e7e8q`), ✅ **SAN** (`Nf3`, `O-O`) — rendu *et* parsing dans
  `chess/engine/san.py` (`move_to_san` / `san_to_move`, désambiguïsation
  `Nbd2`/`R1e2`/`Qh4e1`, promotions `e8=Q`, `0-0` accepté, suffixes `+`/`#`) —
  et ✅ **PGN** (import/export dans `chess/engine/pgn.py` : Seven Tag Roster,
  `[SetUp "1"]`/`[FEN]` si besoin, coups SAN numérotés, résultat, lignes ≤ 80
  caractères ; import ignorant commentaires/variantes/NAG/numéros avec erreur
  numérotée).
- **CLI `chess`** pensée pour les humains *et* les agents LLM : `new`, `board`,
  `moves`, `move`, `status`, `undo`, `fen`, `load`, `history` ✅, sortie
  `pgn`, `load-pgn <fichier>`, `ai-move [--depth N]` ✅, sortie
  `--json` structurée sur chaque commande ✅, état de la partie persisté dans
  `.chess_game.json` ✅, erreurs explicites (coup illégal → rc 1 + liste des
  coups légaux, FEN invalide → « invalid FEN ») ✅. `moves` et `history`
  affichent UCI + SAN (JSON : `moves` + `details`).
- **API HTTP** (FastAPI) exposant la même partie ✅ (`/api/status`, `/api/board`,
  `/api/moves`, `/api/fen`, `/api/eval`, `/api/new`, `/api/move`, `/api/load`,
  `/api/undo`, `/api/history`, `/api/pgn`, `/api/load-pgn`, `/api/ai-move`).
- **Interface web** ✅ avec échiquier jouable en HTML/CSS/JS vanilla (voir
  ci-dessous).
- **IA classique** ✅ : évaluation statique en centipions **du point de vue du
  camp au trait** (matériel + tables pièce-case, `MATE_SCORE = ±100000` ajusté
  par la profondeur) + **negamax alpha-beta** avec tri des coups (captures
  MVV-LVA, promotions) renvoyant `(move, score, nodes)` ; dispo en CLI
  (`ai-move --depth N`) et via l'API (`/api/ai-move`, `/api/eval`).
- **Tests pytest** par module ✅ (**157 tests, 0 xfail**, + 3 tests `slow`) ; **perft** ✅ tous au vert
  (`chess/engine/perft.py`, `tests/test_perft.py`) : position initiale
  profondeurs 1 à 4 (20, 400, 8902, 197281), Kiwipete
  `r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1`
  (48, 2039, 97862), `8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1`
  (14, 191, 2812), `r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1`
  (6, 264, 9467). Les cas profonds portent le marqueur `slow`
  (deselectable via `-m "not slow"`).

## Architecture

```
chess/
  engine/  board.py pieces.py move.py movegen.py rules.py game.py fen.py pgn.py san.py
  ai/      evaluation.py search.py
  cli/     main.py
  api/     server.py schemas.py
web/       index.html style.css board.js api.js
tests/     test_board.py test_movegen.py test_rules.py test_fen.py test_pgn.py
           test_san.py test_perft.py test_game.py test_cli.py test_api.py test_ai.py
skills/    chess-cli/SKILL.md  (skill Vibe : jouer via la CLI en --json)
           chess-cli/example_game.pgn  (partie exemple jouée via la CLI seule)
```

## Utilisation prévue

### CLI (humain ou agent)

```bash
python3 -m chess new                 # nouvelle partie (persistée dans .chess_game.json) ✅
python3 -m chess board               # échiquier ASCII ✅
python3 -m chess moves               # coups légaux en UCI + SAN ✅
python3 -m chess move e2e4           # joue un coup (UCI ou SAN : Nf3, O-O...) ✅
python3 -m chess status              # au trait, échec, mat, nulle... ✅
python3 -m chess undo / fen / load <fen> / history   # ✅
python3 -m chess ai-move --depth 3   # coup de l'IA (minimax alpha-beta) ✅
                                       # JSON : move, san, score, nodes, time_ms
python3 -m chess pgn                 # exporte la partie en PGN ✅
python3 -m chess load-pgn partie.pgn # charge un fichier PGN ✅
python3 -m chess <commande> --json   # sortie structurée pour un agent ✅
```

Après `pip install -e .`, la commande `chess` est aussi disponible directement.

### API HTTP

```bash
uvicorn chess.api.server:app --reload   # endpoints REST + statut de la partie
```

### Web

Lancer le serveur (section « Lancer en local » ci-dessous) puis ouvrir
`http://localhost:8000/` : l'interface `web/` est servie par FastAPI à la
racine et branche tous ses appels sur `/api/*` (voir la section détaillée
« Interface web »). Capture du plateau initial (générée depuis les vrais SVG
de `web/pieces/`) : [`docs/screenshots/board-initial.svg`](docs/screenshots/board-initial.svg).

### Tests

```bash
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest          # tous les tests (les 'slow' tournent aussi)
.venv/bin/python -m pytest -m "not slow"   # rapide : sans perft profonds ni test live
```

Les tests API sont faits sans nouvelle dépendance : appels directs des
fonctions de route (`server.STATE_FILE` monkeypatché vers un `tmp_path`) pour
les cas 400/500, plus un test d'intégration `@pytest.mark.slow` qui démarre
**uvicorn en sous-processus** sur un port libre (arrêté à la fin du test) et
lui parle en `urllib.request`.

## Interface web (`web/`)

Servie par FastAPI à la racine (`http://localhost:8000/`), en HTML/CSS/JS
vanilla **100 % en français**, branchée sur l'API JSON (`/api/*`) — le JS ne
fait qu'afficher ce que renvoie l'API, aucune règle d'échecs en JS :

- **Design system** : thème sombre (fond `#161512`, accent `#7fa650`), police
  Inter (repli `system-ui`), chiffres tabulaires, boutons primaire/secondaire/
  icône avec SVG inline, focus clavier visible, transitions 150 ms.
- **Échiquier jouable** : carré et responsive, cases `#ebecd0`/`#739552`,
  coordonnées en bord de plateau, **pièces SVG dessinées à la main**
  (`web/pieces/`), animation ~180 ms, clic-clic **et** glisser-déposer.
- **Aide au jeu** : sélection → coups légaux de l'API (point sur case vide,
  anneau sur capture), dernier coup surligné `rgba(255,255,0,0.35)`, roi en
  échec en dégradé rouge, **sélecteur de promotion** superposé façon lichess.
- **Mise en page 3 colonnes** (1 colonne sous 900 px) : en-tête logo +
  « Nouvelle partie » ; cartes joueurs (avatar, pièces capturées, avantage
  matériel +N, bordure accent sur le joueur au trait) ; tableau des coups
  **n° | Blancs | Noirs** en SAN ; barre de statut en français (« Aux Blancs
  de jouer », « Échec ! », « Échec et mat — les Noirs gagnent »…).
- **Navigation dans l'historique** ⏮️ ◀️ ▶️ ⏭️ + flèches clavier (← → Home
  End), bandeau « position passée », bouton « ▶ Jouer » pour revenir au live.
- **Contre l'ordinateur** : contrôle segmenté, couleur
  Blancs/Noirs/aléatoire, difficulté 1–4, spinner « l'ordinateur réfléchit… ».
- **Fin de partie** : fenêtre modale (résultat + raison exacte de l'API,
  « Rejouer » / « Revoir la partie ») ; **toasts** pour les erreurs.
- **FEN / PGN** : section repliable (charger, copier) ; **barre d'évaluation
  animée** alimentée par `/api/eval`.
- **Sons optionnels** (Web Audio API) avec bouton muet, **horloge optionnelle**
  (5 min, 10 min, 3 min + 2 s, perte au temps) ; préférences persistées en
  `localStorage`. Boutons « Annuler le coup » et « Retourner l'échiquier ».
- **Mise en page façon lichess** : cartes joueurs au-dessus/d-dessous du
  plateau, panneau droit à onglets (Partie / Outils), modale « Nouvelle
  partie » (2 joueurs, contre l'ordinateur, **spectateur**), mobile < 700 px
  avec barre d'actions en bas.
- **Synchro live** : le navigateur interroge `/api/status` chaque seconde et
  se rafraîchit dès que le compteur `version` change — un coup joué via la
  CLI (`chess move …`) apparaît dans le navigateur en moins de 2 s. En mode
  **Spectateur**, le navigateur n'accepte aucun coup et ne lance jamais l'IA.
  Côté agent : `chess wait --color w|b [--timeout S] --json` bloque jusqu'au
  tour de cette couleur (ou la fin de partie) — voir `skills/chess-cli/SKILL.md`.

## Lancer en local

```bash
# 1. Environnement virtuel + dépendances (fastapi, uvicorn, pytest)
python3 -m venv .venv
.venv/bin/pip install -e '.[dev]'

# 2. Tous les tests (pytest)
.venv/bin/python -m pytest

# 3. Serveur API + interface web, en arrière-plan ou terminal dédié
.venv/bin/python -m uvicorn chess.api.server:app --reload --host 127.0.0.1 --port 8000
#   → interface web :  http://localhost:8000/
#   → docs API Swagger : http://localhost:8000/docs
#   → API JSON :        http://localhost:8000/api/status

# 4. CLI (console script installé par pip ; sinon `python3 -m chess ...`)
.venv/bin/chess new                 # démarre une partie (persistée dans .chess_game.json)
.venv/bin/chess board               # échiquier ASCII
.venv/bin/chess move e2e4           # joue un coup (UCI)
.venv/bin/chess status              # au trait, échec, résultat, FEN
.venv/bin/chess moves --json        # coups légaux en JSON (pour un agent LLM)
.venv/bin/chess undo                # annule le dernier coup
.venv/bin/chess fen / load <fen> / history
```

La CLI et l'API partagent le même fichier d'état `.chess_game.json` quand elles
tournent depuis la racine du projet (surcharger avec `--state PATH` côté CLI ou
`CHESS_STATE_FILE` côté serveur).

### Skill pour agent LLM (`skills/chess-cli/`)

`SKILL.md` apprend à un agent à jouer une partie complète via la CLI seule :
boucle `status --json` → `moves --json` → `move <uci> --json` → `ai-move
--depth 2 --json` pour l'adversaire, gestion des erreurs (rc 1 + liste des
coups légaux), condition d'arrêt `result != "ongoing"`. `example_game.pgn`
est une vraie partie jouée de cette façon (agent vs `ai-move --depth 2`,
nulle par triple répétition). Voir `chess --help` pour la liste des
sous-commandes.

## Plan de développement (phases)

1. **Fondations** — `AGENTS.md`, `README.md`, squelette (`pyproject.toml`,
   arborescence, test trivial qui passe). ✅
2. **Moteur** (Rafiq) — plateau, pièces, génération de coups pseudo-légaux puis
   légaux, règles complètes (échec/mat/pat, promotion, roque, prise en
   passant, triple répétition, 50 coups, matériel insuffisant), FEN, UCI ✅ ;
   ✅ **perft** au vert (toutes les positions de référence) ; ✅ **SAN** dans
   `chess/engine/san.py` ; ✅ **PGN** dans `chess/engine/pgn.py`.
3. **CLI** (Adam) — persistance `.chess_game.json`, sous-commandes complètes
   (`new`…`load-pgn`, `ai-move`), `--json`, tests CLI ✅.
4. **IA** (Adam) — évaluation statique + minimax alpha-beta, tests. ✅
5. **API HTTP** (Adam) — FastAPI + schémas + tests (SAN, PGN import/export,
   `ai-move`). ✅
6. **Web** (agent) — échiquier jouable vanilla JS branché sur l'API. ✅
7. **Finitions** (tous) — ✅ règles complètes + perft au vert, ✅ skill agent
   `skills/chess-cli/` (avec `example_game.pgn` jouée via la CLI seule) ;
   🚧 `report.md` (retour d'expérience demandé par le cours).

## Décisions

- README en français ; **code, docstrings et commits en anglais**.
- État de la partie persisté dans `.chess_game.json` à la racine (gitignoré :
  c'est de l'état runtime, pas du code).
- Packaging via `pyproject.toml` (console script `chess` + `python -m chess`).
- venv local `.venv` gitignoré ; dépendances strictement limitées à
  `fastapi`, `uvicorn`, `pytest`.
- Aucune bibliothèque d'échecs externe : tout le moteur est écrit à la main.
- Le fichier d'état `.chess_game.json` vit dans le **cwd** (racine du projet en
  pratique) et est partagé entre CLI et API ; `--state PATH` (option globale,
  avant la sous-commande) et `CHESS_STATE_FILE` (env var serveur) permettent de
  le déplacer.
- L'API est testée via le serveur live + `curl` (et non `TestClient`) car
  `httpx` ne fait pas partie des dépendances autorisées.
- Le serveur sert `web/` à la racine (`/`) ; les routes `/api/*` et `/docs`
  sont enregistrées avant le mount statique pour prendre la priorité.
- Slice moteur actuel : coups normaux de toutes les pièces, promotion, roque
  (petit/grand, toutes conditions), prise en passant, filtre « roi pas en
  échec », échec/mat/pat, triple répétition, règle des 50 coups, matériel
  insuffisant, FEN (+ validation), persistance JSON, perft au vert sur les 4
  positions de référence. SAN (`chess/engine/san.py`) et PGN
  (`chess/engine/pgn.py`) vivent dans le moteur ; la couche API ne contient
  plus aucune logique d'échecs.
- **Nulles automatiques** : triple répétition, règle des 50 coups et matériel
  insuffisant sont détectées automatiquement (pas de réclamation à la FIDE) —
  `result` vaut `draw_threefold` / `draw_fifty_move` /
  `draw_insufficient_material` et `winner` vaut `null` dans `Game.status()`.
- **Perte au temps = défaite** : le camp au clock à 0 perd (résultat
  `flag` + `winner`), enregistré par l'API via `POST /api/flag` et persisté
  dans l'état ; plus aucun coup n'est accepté ensuite.
- Règle d'ambiguïté : choisir l'option la plus simple et l'ajouter ici.
