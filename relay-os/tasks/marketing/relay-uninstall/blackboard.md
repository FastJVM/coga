The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: relay-uninstall
worktree: /home/n/Code/codex/relay-uninstall

## Goal

`relay uninstall` — the symmetric inverse of `relay init`. Removes this repo's
relay footprint and (opt-in) the global pip/pipx package, so people can try
Relay knowing it's a one-command removal.

## What `relay init` creates (the inverse we must reverse)

1. `<target>/relay-os/` whole tree (incl. vendored `.relay/.venv`)
2. `<target>/.claude/skills/relay` + `<target>/.codex/skills/relay` symlinks
   → `relay-os/.agent-skills`
3. `<target>/CLAUDE.md`, `<target>/AGENTS.md` (written only if missing)
4. relay-managed block in `<target>/.gitignore` (marker-fenced)
5. `~/.local/bin/relay` shim symlink → this repo's `.relay/bin/relay`
6. global `relay-os` pip/pipx package

## Design decisions (from human, interactive)

- **pip removal: flag-gated.** Default uninstall removes repo files + shim and
  prints the exact `pipx/pip uninstall relay-os` command. `--purge` actually
  runs the uninstall. (Machine-global, so opt-in.)
- **Safety: confirm prompt + `--yes`.** Print the plan, prompt y/N; `--yes`
  skips for scripting.
- **CLAUDE.md / AGENTS.md: remove, but back up modified.** Unmodified (==
  shipped `AGENT_GUIDE_TEMPLATE`) → remove silently. Modified → rename to
  `<name>.relay-bak` and report (don't destroy user edits). Rationale: they're
  relay-orientation docs, stale after uninstall.

## Implementation

- New `src/relay/commands/uninstall.py` with `uninstall(yes, purge)`.
- New helper `remove_host_gitignore(target) -> bool` in `update.py` (inverse of
  `ensure_host_gitignore`, same marker logic). Reuse `running_cli_location`,
  `RELAY_PIPX_PACKAGE`.
- Shim removed only if it's a symlink resolving into this repo's `.relay`.
- Agent skill symlinks removed; prune now-empty `skills/` and `.claude`/`.codex`
  if empty.
- Register `app.command("uninstall")` in cli.py + add to known-command set.
- Tests in `tests/test_uninstall.py` mirroring `tests/test_init.py` (CliRunner).

## Status — implemented

Done on branch `relay-uninstall`:
- `src/relay/commands/uninstall.py` — `relay uninstall [--yes] [--purge]`.
- `remove_host_gitignore()` helper added to `update.py` (inverse of
  `ensure_host_gitignore`).
- Registered `uninstall` in `cli.py` (command + `_BUILTIN_COMMANDS`), and made
  `main()` tolerate a broken config for `uninstall` like it does for `init`.
- `tests/test_uninstall.py` — 8 tests, all pass (CliRunner, mirrors test_init).
- Smoke: `relay uninstall --help` renders; config-leniency note fires.

Test note: full suite has 2 pre-existing failures in `test_autoclose_sweep.py`
(date-dependent — hardcoded 2026-06-11 vs today). Confirmed they fail on the
clean stashed tree too; unrelated to this change. Everything else passes (814).

Env note: system python is 3.9 (no tomllib); ran tests with `python3.12`.

## Follow-up (out of scope — note for a future ticket)

- Human flagged: on *install*, `init` should save a pre-existing CLAUDE.md /
  AGENTS.md before writing the relay template. Today `_write_agent_guides` only
  writes when missing (never overwrites), so there's no data loss on install —
  but a backup-on-install would let init refresh a stale relay-owned guide
  without clobbering edits. Separate ticket; not touched here.
