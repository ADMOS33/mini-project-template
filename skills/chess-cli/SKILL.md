---
name: chess-cli
description: Load this skill when you must play a game of chess (or set one up) through the `chess` command-line interface — e.g. "play a game via the CLI", "make a move with chess", "run the computer opponent". It documents the JSON-first contract of every subcommand so an agent can drive a full game loop by itself.
---

# Playing chess through the `chess` CLI

The `chess` command is **agent-friendly**: every subcommand accepts `--json`
and returns a structured object on stdout. Game state is persisted in a JSON
file (default `.chess_game.json` at the repo root); override it with the
global `--state PATH` option, e.g. `chess --state /tmp/my_game.json new --json`.

All chess rules live in the Python engine — the CLI is only a thin wrapper, so
**never re-implement rules yourself**: always ask the CLI.

## Subcommands (all accept `--json`)

| Command | Purpose | JSON highlights |
|---|---|---|
| `chess new` | start a new game | `{"ok": true, "status": {...}}` |
| `chess board` | ASCII board | `board` string |
| `chess moves` | legal moves | `moves`: list of UCI strings; `details`: `[{"uci","san"}, …]` |
| `chess move <uci\|san>` | play a move | `{"ok": true, "move": "e2e4", "status": {...}}` |
| `chess status` | side to move, check, result | `turn` (`"w"`/`"b"`), `in_check`, `result`, `winner`, `legal_move_count`, `fen` |
| `chess undo` | take back the last move | `{"ok": true, "undone": "a7a5", "status": {...}}` |
| `chess fen` | current FEN | `fen` string |
| `chess load <fen>` | start from a FEN | `{"ok": true, "status": {...}}`; invalid FEN → rc 1, `{"error": "invalid FEN: …"}` |
| `chess pgn` | export the game as PGN | `pgn` string |
| `chess load-pgn <file>` | load a game from a PGN file | `{"ok": true, "status": {...}}` |
| `chess ai-move [--depth N]` | let the computer play (minimax + alpha-beta) | `move`, `san`, `score` (centipawns), `nodes`, `time_ms`, `depth`, `status` |
| `chess history` | moves played so far | `moves` (UCI) + `details` (`[{"uci","san"}, …]`) |
| `chess wait --color w\|b [--timeout S]` | block until it is this side's turn or the game ends (multi-agent sync) | `{"ok": true, "timeout": bool, "status": {...}}` |

Moves can be given in **UCI** (`e2e4`, `e7e8q` for promotion) **or SAN**
(`Nf3`, `exd5`, `O-O`). In JSON, `moves` stays the plain UCI list and
`details` adds the SAN.

## The game loop (use this pattern)

```bash
chess --state game.json new --json            # 1. start
chess --state game.json status --json         # 2. read state
chess --state game.json moves --json          # 3. list legal moves (UCI + SAN)
chess --state game.json move e2e4 --json      # 4. play one of them
chess --state game.json ai-move --depth 2 --json   # 5. computer answers
chess --state game.json pgn > game.pgn        # 6. export at the end
```

Loop: `status --json` → if `result != "ongoing"`, **stop** (see below) →
`moves --json` → choose a legal move → `move <uci> --json` → repeat.

## Errors

- **Illegal move**: `chess move e2e5 --json` exits with **rc 1** and prints
  `{"error": "illegal move 'e2e5'; legal moves: a2a3 a2a4 …"}` — the message
  already contains the full list of legal UCI moves. Pick one of those and
  retry; do not guess blindly.
- **Invalid FEN / PGN**: rc 1 with `{"error": "invalid FEN: …"}` /
  `"invalid PGN (move N): …"`.
- **Undo with empty history**: rc 1 with a clear `error`.
- Always check the **return code**, not just stdout, and parse the `error`
  field when present.

## End of game — stopping condition

`status --json` returns:

- `result`: one of `ongoing`, `checkmate`, `stalemate`, `draw_threefold`,
  `draw_fifty_move`, `draw_insufficient_material`, `flag` (loss on time)
- `winner`: `"w"`, `"b"` or `null`
- `in_check`: whether the side to move is in check
- `version`: monotonic counter bumped on **every** state change (move, undo,
  new, load, ai-move). Poll `status --json` and compare it to detect moves
  played by another client (web UI in spectator mode, another agent…).

**Stop the loop as soon as `result != "ongoing"`** and report the result and
winner (e.g. `checkmate` + `winner: "b"` → "checkmate, Black wins").
`legal_move_count == 0` with `in_check == false` is a stalemate, with
`in_check == true` a checkmate — but rely on `result`, not on your own
calculation.

## Tips

- Prefer `--json` everywhere: it is stable and parseable; the human-readable
  output is for humans.
- `ai-move` plays **for the side to move**, so after your `move`, call
  `ai-move` to let the computer answer, then loop back to `status`.
- `--depth` (default 2) trades strength for speed; depth 3–4 is noticeably
  slower but stronger.
- Use a dedicated `--state` file per game so parallel games do not collide.
- `chess pgn` gives you a PGN you can save or hand to `load-pgn` later.
- A full worked example is in `example_game.pgn` next to this file.

## Playing against the computer (or watching it play)

```bash
chess new --json
chess moves --json                 # your legal moves (you are White)
chess move e2e4 --json             # your move
chess ai-move --depth 3 --json     # computer answers as Black
# loop: status --json → moves --json → move <uci> --json → ai-move --json
```

Open `http://localhost:8000/` and pick **Spectateur** in the new-game modal:
the browser follows the game **live** (it polls `status` every second and
refreshes whenever `version` changes) without ever playing a move itself —
a move you play here appears in the browser in under 2 s.

## Playing against a human or another agent (two-sided sync with `wait`)

The state file is shared, so two agents can play the same game — one per
color — without ever playing the opponent's side:

```bash
# Agent playing White (in its own session):
chess wait --color w --timeout 300 --json   # blocks until White to move / game over
chess status --json                         # result != "ongoing"? stop
chess moves --json                          # choose ONE legal move
chess move <uci> --json                     # play it, then loop back to wait

# Agent playing Black: same loop with --color b.
```

- `wait` re-reads the state file every 0.1 s, so it wakes up as soon as the
  other side has moved. `--json` adds `"timeout": true` if the deadline hit
  first (treat it as "not my turn yet / still playing", never as an error).
- **Never** call `move` when `status.turn` is not your color, never use
  `ai-move` or `undo` in a two-agent game.
- End of game: when `status.result != "ongoing"`, stop looping and print
  `chess pgn` to export the game.
