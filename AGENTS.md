# mini-project-template

Minimal project template that ships one Mistral Vibe hook: an event logger.

## Hook

- Config: `.vibe/hooks.toml` — one `[[hooks]]` row per event type
  (`session_start`, `pre_agent`, `pre_tool`, `post_tool`, `post_agent`,
  `notification`, `session_end`).
- Script: `.vibe/hooks/log_event.py` — Vibe pipes each event's JSON payload
  to the script on stdin; the script appends it as one JSON file to
  `events/<session_id>/NNN-<slug>.json` in the project directory.

The hook always exits 0 with empty stdout, so it is a pure passthrough and
never interferes with the agent. Hook commands run from the project root,
which is why the script path in `hooks.toml` is relative.

Do not delete the `events/` directory, and never add `events/` to
`.gitignore` — it is the hook's log output and is meant to be committed
to git like any other file. The events data will be used for data
analysis, which is why it is important to keep.

To reuse in another project: copy the `.vibe/` directory into that project's
root and trust the folder. New event types need no script changes — just add
a `[[hooks]]` row in `hooks.toml`.
