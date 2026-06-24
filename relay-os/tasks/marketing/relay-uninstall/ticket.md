---
slug: marketing/relay-uninstall
title: relay-uninstall
status: done
autonomy: interactive
owner: zach
human: zach
agent: claude
assignee: zach
contexts: []
skills: []
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
  - name: peer-review
    skills: []
    assignee: other-agent
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
  - name: review
    skills: []
    assignee: owner
---

## Description

Create a one-step command to uninstall Relay. "Relay-uninstall" removes all relay files from your machine. 

Having this in place will help folks try it when they know it's easily removed if they don't like it. 

## Context

<!-- relay:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: relay-uninstall
worktree: /home/n/Code/codex/relay-uninstall
pr: https://github.com/FastJVM/relay/pull/407

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
- `tests/test_uninstall.py` — 9 tests, all pass (CliRunner, mirrors test_init).
- Follow-up fix in this session: `--purge` now uses the same vendored/global
  CLI-location decision during execution that the printed plan already used, so
  running the repo's vendored `relay` does not accidentally invoke pipx.
- Durable docs/context updated in this session: README command reference and
  packaged `relay/cli` context now document `relay uninstall`.
- Smoke: `relay uninstall --help` renders; config-leniency note fires.
- Final feature commit: `8e10f6c` on branch `relay-uninstall`.
- Final verification in this session:
  `python3.12 -m pytest tests/test_uninstall.py -q` (9 passed),
  `PYTHONPATH=src python3.12 -m relay.cli uninstall --help`, and
  `git diff --check main...HEAD`.

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

## Peer Review

Native review: `codex review --base main` from
`/home/n/Code/codex/relay-uninstall`. The sandboxed attempt failed with the
known read-only app-server initialization error, then succeeded when rerun
outside the sandbox.

Must-fix findings applied:
- `--purge` now branches on `running_cli_location`: pipx installs use
  `pipx uninstall relay-os`, non-pipx installs use the running interpreter's
  `python -m pip uninstall -y relay-os`, and vendored installs skip global
  removal.
- `relay-os/` removal no longer uses `ignore_errors=True`; uninstall exits loud
  if the directory cannot be removed or still exists after removal.
- Direct `relay uninstall` now bypasses alias validation/registration, with a
  notice for a legacy `[aliases] uninstall = ...`, so the new built-in cannot
  be blocked by a pre-existing uninstall alias.

Peer-review fix commit: `13ce897` (`peer-review: apply uninstall fixes`).

Verification after peer-review fixes:
- `python3.12 -m pytest tests/test_uninstall.py -q` → 12 passed.
- `python3.12 -m pytest -p no:cacheprovider` → 818 passed, 1 skipped, 2 failed
  in `tests/test_autoclose_sweep.py` from existing autoclose live/packaged
  blackboard drift (`last_serviced_period: 2026-06-17` vs expected/package
  state); unrelated to uninstall.
- `PYTHONPATH=src python3.12 -m relay.cli uninstall --help` renders.
- `git diff --check main...HEAD` clean.
