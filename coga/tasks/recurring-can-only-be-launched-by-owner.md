---
slug: recurring-can-only-be-launched-by-owner
title: recurring can only be launched by owner
status: draft
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
contexts: []
skills: []
workflow: code/with-review
secrets: null
---

## Description

Recurring sweeps can be launched twice at the same time when two operators
(different machines/clones of this repo) both run them — same-machine overlap
is already handled because the sweep is sequential. Fix this by gating
recurring launches on a repo owner: add a committed `owner = "<name>"` setting
to `coga.toml`, and make every recurring launch entry point refuse to run when
the local operator (`current_user`) is not that owner. Set `owner =
"nicktoper"` for this repo as part of the change.

## Context

- **Identity model**: the local operator is `current_user`, loaded from the
  required `user =` field in the uncommitted `coga.local.toml`
  (`src/coga/config.py` ~line 277 — it is explicitly set, never guessed; keep
  that rule). There is **no repo-level owner concept today**: `owner:` exists
  only per-ticket. The new `owner` belongs in the *committed* `coga.toml` so
  every clone agrees on it; add it to `Config` in `config.py`.
- **Entry points to gate** (all of them): the bare `coga recurring` sweep
  (including `--force` and, per-repo, `--all`) and the manual `coga recurring
  launch <name>` — see `src/coga/commands/recurring.py`. The sweep runs the
  registered `recurring-scan` recipe via `run_recipe`, so put the gate in the
  shared recurring machinery (`recurring.py` / `recurring_runner.py`), not
  just the Typer command, so `coga run recurring-scan` is covered too.
- `coga recurring list` and `coga recurring promote` are not launches — leave
  them ungated.
- **When `owner` is unset** in `coga.toml`: behave as today (no gate), so
  other repos are unaffected until they opt in. The refusal message for a
  non-owner should name the configured owner so the operator knows who runs
  recurring here.
- Update the repo-local `coga/contexts/coga/recurring/SKILL.md` in the same
  PR (behavior change → context change; this context is repo-local, not
  packaged). Check whether the packaged `coga.toml` template /
  `example/coga/` fixture should document the new field (a commented example
  is probably enough).

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
