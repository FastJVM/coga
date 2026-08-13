---
slug: recurring-can-only-be-launched-by-owner
title: recurring can only be launched by owner
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: claude
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
    requires: pr
  - name: review
    skills: []
    assignee: owner
secrets: null
step: 1 (implement)
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
  them ungated. `--force` stays gated for non-owners too — no override flag;
  a deliberate takeover means editing the committed `owner` in `coga.toml`.
- **This is a policy gate, not a lock.** It closes the observed race (two
  *different* operators sweeping concurrently from different clones); the same
  owner running two clones could still race, and same-machine overlap is
  already handled by the sequential sweep. Don't build locking here.
- Under `--all`, the gate is per-repo (each repo's own `owner` vs. the
  operator): skip non-owned repos and continue the sweep, don't fail it. The
  `--all` path already has remote-identity checks
  (`_configured_remote_identity` in `recurring_runner.py`) — compose with
  them, don't duplicate.
- Adding `owner` to the committed `coga.toml` also means touching the shared
  known-keys/schema set in `config.py` (near where `"user"` is declared for
  the local file).
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
