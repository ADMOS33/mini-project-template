# AGENTS.md — Projet Chess (ENSEIRB-MATMECA, cours de génie logiciel)

## Fichiers interdits — NE JAMAIS modifier, supprimer ou déplacer

- `events/` : logs du hook Vibe. Ne jamais modifier/supprimer/déplacer, et
  **ne jamais l'ajouter au `.gitignore`** : ces fichiers sont faits pour être
  commités dans git comme n'importe quel autre (le prof les analyse).
- `.vibe/hooks.toml` et `.vibe/hooks/log_event.py` : configuration du hook
  d'enregistrement d'événements. Ne jamais toucher.

## Le projet

Un **jeu d'échecs complet en Python pur** (aucune bibliothèque d'échecs
externe, tout est écrit à la main) :

1. un moteur d'échecs avec règles complètes ;
2. une CLI utilisable par un humain **et par un agent LLM** (exigence du cours) ;
3. une API HTTP (FastAPI) ;
4. une interface web (HTML/CSS/JS vanilla) avec échiquier jouable ;
5. un adversaire ordinateur classique : **minimax + élagage alpha-beta**
   (pas d'IA générative).

Règles à implémenter intégralement : déplacements de toutes les pièces, coups
légaux (on ne laisse pas son roi en échec), échec, échec et mat, pat, petit et
grand roque (avec toutes les conditions), prise en passant, promotion (choix
de la pièce), nulle par triple répétition, règle des 50 coups, matériel
insuffisant. Import/export **FEN** et **PGN**. Notations **UCI** (`e2e4`,
`e7e8q`) et **SAN** (`Nf3`, `O-O`).

Vérification : tests pytest par module + **perft obligatoires** (position
initiale profondeur 1 à 4 : 20, 400, 8902, 197281 ; Kiwipete
`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1`
profondeurs 1 à 3 : 48, 2039, 97862). Le moteur n'est correct que si tous les
perft passent.

## Règles de travail

- Commits petits et fréquents, **un commit par unité logique**, messages en
  anglais au format **Conventional Commits** (`feat:`, `test:`, `fix:`,
  `refactor:`, `docs:`, `chore:`).
- **Ne jamais committer un état où les tests existants échouent.**
- Code en **anglais**, typé (type hints), docstrings courtes.
- Dépendances autorisées uniquement : `fastapi`, `uvicorn`, `pytest`.
- Après chaque fonctionnalité : lancer les tests et corriger jusqu'au vert.
- Si une décision est ambiguë : choisir **l'option la plus simple** et la noter
  dans le README (section « Décisions »).

## Ne jamais faire (règles absolues)

- **Ne jamais lancer de process bloquant** (uvicorn, serveur, watcher, ...) :
  c'est l'humain qui le lance.
- **Ne jamais modifier `events/`** ni `.vibe/hooks.toml` /
  `.vibe/hooks.log_event.py` — sauf pour committer `events/`.
- **Ne jamais ajouter de dépendance** (pas de python-chess, pas de httpx) :
  uniquement `fastapi`, `uvicorn`, `pytest`.
- **Ne jamais implémenter de règle d'échecs en JS ou dans l'API** : tout vit
  dans le moteur (`chess/engine/`).
- **Ne jamais committer un état où les tests échouent** ; pour une cible pas
  encore atteinte, utiliser `pytest.mark.xfail(strict=True, reason=...)`.
- **N'implémenter que ce qui est demandé**, rien de plus.

## Workflow — test d'abord

1. Écrire le test de régression et le voir **échouer**.
2. Corriger/implementer jusqu'au **vert**.
3. Un seul commit (test + code ensemble), message Conventional Commits.

## Definition of Done

Une étape est terminée quand :

1. le test de régression existe et passe ;
2. `pytest` est entièrement vert ;
3. le README est à jour si le comportement visible a changé.

À la fin de **chaque phase** : mettre à jour le tableau « État d'avancement"
ci-dessous, puis `git add events/ && git commit -m "chore: add vibe session logs"`.
Si la session est interrompue, la prochaine reprendra grâce à ce tableau.

## État d'avancement

| Module | Fait ✅ | À faire 🚧 |
|--------|---------|-----------|
| Moteur `chess/engine/` | plateau/pièces, déplacements de base, promotion, coups légaux (roi jamais en échec), échec/mat/pat, règle des 50 coups, FEN import/export, `Game` (play/undo/status/persistance JSON) | roque, prise en passant, triple répétition, matériel insuffisant, perft, validation FEN (rois, pions 1re/8e, échec) |
| CLI `chess/cli/` | `new`, `board`, `moves`, `move`, `status`, `undo`, `fen`, `load`, `history`, `--json` | `pgn`, `ai-move` |
| API `chess/api/` | `status`, `board`, `moves`, `fen`, `new`, `move`, `load`, `undo`, `history` (SAN), export/import PGN, `ai-move` | — |
| IA `chess/ai/` | évaluation statique (matériel + tables de pièces), minimax + alpha-beta | — |
| Web `web/` | échiquier jouable complet (clic + drag&drop, surbrillance, promotion, historique SAN, captures, horloges, vs ordinateur, flip, modale fin de partie, import/export FEN/PGN) | — |
| Tests | 46 tests pytest verts | perft (position initiale + Kiwipete) |
| Skills `skills/` | — | skill Vibe apprenant à jouer via la CLI |

## Architecture cible

```
chess/
  engine/  board.py pieces.py move.py movegen.py rules.py game.py fen.py pgn.py san.py
  ai/      evaluation.py search.py
  cli/     main.py
  api/     server.py schemas.py
web/       index.html style.css board.js api.js
tests/     test_board.py test_movegen.py test_rules.py test_fen.py test_pgn.py
           test_san.py test_perft.py test_game.py test_cli.py test_api.py test_ai.py
skills/    (plus tard) skill Vibe apprenant à un agent à jouer via la CLI
```

## Contrat CLI (pensé pour les agents)

Commande `chess`, sous-commandes : `new`, `board` (ASCII), `move <uci|san>`,
`moves` (coups légaux), `status` (au trait, échec, mat, nulle), `undo`, `fen`,
`load <fen>`, `pgn`, `ai-move [--depth N]`, `history`. L'état de la partie est
persisté dans `.chess_game.json` à la racine du projet (gitignoré). Chaque
commande accepte `--json` pour une sortie structurée lisible par un agent.
Messages d'erreur clairs : coup illégal → liste des coups légaux.

## Équipe et répartition

- **Rafiq** : moteur (`chess/engine/`)
- **Adam** : CLI / API / IA (`chess/cli/`, `chess/api/`, `chess/ai/`)
- **Hafsa** : interface web (`web/`)

Le développement est réalisé principalement par l'agent ; les membres
relacent/valident par revue.

## Environnement de dev

- venv local `.venv` (gitignoré) : `python3 -m venv .venv` puis
  `.venv/bin/pip install -e '.[dev]'`
- Tests : `.venv/bin/python -m pytest` depuis la racine du dépôt.
- CLI sans installation : `python3 -m chess ...` (ou `.venv/bin/chess ...`
  après `pip install -e .`).
