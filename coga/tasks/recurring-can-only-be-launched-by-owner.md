---
slug: recurring-can-only-be-launched-by-owner
title: recurring can only be launched by owner
status: in_progress
owner: nicktoper
human: nicktoper
agent: claude
assignee: nicktoper
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
step: 4 (review)
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

## Dev

pr: https://github.com/FastJVM/coga/pull/687
branch: recurring-owner-gate
worktree: /home/n/Code/claude/coga-recurring-owner-gate

Tests run with `python3.12 -m pytest` (the repo `.venv` has no pytest and the
default `python` is 3.9): post-review, post-rebase full suite 1735 passed, 1
skipped.

## What landed (implement step)

- `config.py` — new committed `owner` key on `Config` (`owner: str = ""`),
  parsed by `parse_owner` from the shared `coga.toml` only, added to
  `_ALLOWED_SHARED_SECTIONS`. Deliberately **not** a local key: an `owner` in
  `coga.local.toml` fails the generic unknown-key check, which is right — a
  machine-local owner says nothing to the clones the gate holds off.
- `recurring_runner.py` — `recurring_owner_refusal(cfg)` returns the refusal
  string or None; `_refuse_non_owner` prints it. Gated at the top of
  `run_recurring_scan` (so bare sweep, `--force`, and `coga run
  recurring-scan` are all covered) and `run_recurring_named`.
- `--all` — `_repo_owner_refusal(coga_os)` classifies each discovered repo
  *before* `_duplicate_remote_checkouts`, so a non-owned checkout can never be
  picked as the keeper for a remote whose other checkout is runnable. Skipped
  repos are listed by name with the reason and the sweep continues (exit 0).
- `coga/coga.toml` — `owner = "nicktoper"`. Commented example in the packaged
  template and `example/coga/coga.toml`.
- Docs: new "One operator owns recurring: the `owner` gate" section in
  `coga/contexts/coga/recurring/SKILL.md`, plus `docs/reference.md` and
  `docs/operations.md`.

## Decisions

- Refusal names the configured owner and the operator identity, including the
  "no `user` set" case — a fresh clone is a non-owner, not a silent owner.
- `--force` stays gated (it forces schedule/status filters, not the gate) and
  there is no override flag, per the ticket: a takeover is a committed
  `owner` edit.
- `--all` skips rather than fails: one non-owned repo in a scanned directory
  must not make the whole sweep exit non-zero.
- Config load failures in `_repo_owner_refusal` fall through to "no refusal",
  matching `_configured_remote_identity` — the child process is the
  authoritative loader.

## Verified by hand

From the worktree with a temporary `user = "someone-else"`, all four launch
entry points refuse with exit 2 (`recurring`, `recurring --force`,
`run recurring-scan`, `recurring launch dream`); `recurring list` still works.
`coga validate --json` on `example/` is clean.

## Peer review

- `codex review --base main` found a P1: the initial gate authorized before the
  existing control catch-up, so a stale clone could run under an old owner and
  `--all` could pre-skip a transferred owner forever. A verification review
  then caught the remaining feature-branch form of the same bug.
- Fixed by resolving `owner` from the exact fetched control commit for every
  launch and the `--all` prefilter. The fetch uses the existing UUID-scoped git
  primitive, never checkout-wide `FETCH_HEAD`; dirty working-tree takeovers and
  stale feature branches therefore cannot supply authorization. An opted-in
  local owner fails closed when the control owner cannot be confirmed, while a
  locally owner-less repo retains the prior best-effort offline behavior.
- Added real-git regressions for owner additions/transfers, named launches,
  feature branches, dirty owner edits, offline confirmation failure, and the
  command-scoped fetched commit. The recurring/config suites pass 243 tests.
- Committed as `peer-review: authorize recurring from control tip`, fetched
  `origin/main`, and rebased cleanly onto `3166e36b`. The feature worktree is
  clean with two commits ahead of `origin/main`.
- Post-rebase `python3.12 -m pytest`: 1735 passed, 1 skipped. The targeted task
  and seeded `example/` validate clean; whole-repo validation still reports
  unrelated pre-existing errors in old `v2/` drafts.

## PR

Add an optional committed recurring owner and gate every launching surface —
the bare/forced sweep, registered `recurring-scan` recipe, named launch, and
each repo under `--all` — while leaving list/promote and owner-unset repos
unchanged. Authorization reads `owner` from an exact command-scoped fetch of
the control tip, so stale feature branches, dirty edits, and concurrent
`FETCH_HEAD` writes cannot bypass an owner addition or transfer. This also sets
this repo's owner to `nicktoper` and updates the recurring contract, reference
docs, shipped/example config templates, and regression coverage.

Test plan: `python3.12 -m pytest` (1735 passed, 1 skipped); seeded `example/`
validation is clean with the rebased source.
