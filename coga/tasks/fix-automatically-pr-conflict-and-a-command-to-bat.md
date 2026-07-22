---
slug: fix-automatically-pr-conflict-and-a-command-to-bat
title: fix automatically PR conflict and a command to batch fix them
status: draft
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/architecture
- coga/codebase
- dev/code
skills: []
workflow: code/with-review
secrets: null
script: null
---

## Description

Ship a launchable command that resolves conflicts across the repo's open
PRs in one pass, and land the launch-side arg channel that lets it target a
single PR.

The command is authored as a **command ticket** under `coga/bootstrap/`
(the seam the `commands-as-tickets-open-pr-pilot` pilot just landed —
local-first `coga/bootstrap/<name>/ticket.md` resolution + `[aliases]`), so
a ticket plus one alias line mints a new `coga` verb with zero core-Python
change. It is launched in place each time, not instantiated per run.

Behavior:

- `coga resolve-conflicts` — enumerate every open PR (`gh pr list --state
  open`), and for each one that is conflicted against `main`, rebase it,
  resolve the conflicts with **full agent judgment** (read both sides,
  understand intent, re-apply the branch's change on top of main's), verify
  with `python -m pytest` when the diff touches `src/` or `tests/`, and
  `git push --force-with-lease`. This is deliberately more aggressive than
  the mechanical-only posture below it — the agent may resolve semantic
  conflicts, so verification before push is the safety net.
- `coga resolve-conflicts <PR>` — scope to a single PR. This requires the
  **arg channel for agent launches** (see below), which does not exist yet.

Because full agent judgment needs an agent (not a script), the command is an
**agent** launch. Today `coga launch` fails loud when an agent launch is
given trailing args — `commands-as-tickets-open-pr-pilot` shipped the arg
channel for *script* launches only and explicitly deferred composing args
into agent prompts "until a second use case exists." **This ticket is that
second use case:** extend `launch` to compose trailing args into the agent
prompt so `coga resolve-conflicts 631` works.

This **supersedes** the `rebase-stale-worktrees` recurring task. That task
already walks live branches and rebases them mechanically; the new command
is the PR-scoped, judgment-capable successor. Delete
`coga/recurring/rebase-stale-worktrees/` and move its weekly cron intent
onto the new command (a scheduled `coga resolve-conflicts` if a schedule is
still wanted — confirm with owner at review).

The per-run summary goes to **stdout + Slack** (one line per PR, then a
`coga slack` roll-up). Nothing durable is written to disk — this fits the
stateless command-ticket model and avoids the new command writing other
tickets' files.

## Acceptance Criteria

- [ ] `coga/bootstrap/resolve-conflicts/ticket.md` exists as a stateless
  command ticket (no `status`/`workflow`; body documents the verb) and
  `coga resolve-conflicts` runs it via a default alias
  (`launch bootstrap/resolve-conflicts`).
- [ ] Running it with no args sweeps all open PRs: for each conflicted-vs-main
  PR it rebases, resolves conflicts with agent judgment, runs `pytest` when
  the diff touches `src/`/`tests/`, and `git push --force-with-lease`. A PR
  it cannot safely resolve is reported, never force-pushed.
- [ ] Verification gates the push: a rebase whose `pytest` fails is left
  unpushed and reported `verify-failed`, matching `rebase-stale-worktrees`'
  posture.
- [ ] `coga launch <agent-target> <ARG...>` composes trailing args into the
  agent prompt (the deferred half of the `commands-as-tickets` arg channel);
  `coga resolve-conflicts 631` scopes the run to PR 631. The `COGA_*` env
  reservation and the existing script-launch `COGA_ARG_*` behavior are
  untouched.
- [ ] Per-run summary prints one line per PR to stdout and posts a one-line
  roll-up via `coga slack`; nothing is written to any ticket blackboard.
- [ ] `coga/recurring/rebase-stale-worktrees/` is deleted and any reference
  to it (docs, cron config) is updated or removed.
- [ ] Live + packaged copies stay in sync where touched (the arg-channel docs
  in `coga/architecture`, `coga/codebase`, and `docs/reference.md`; the new
  command ticket under both `coga/bootstrap/` and, if it should ship as a
  battery, `src/coga/resources/templates/coga/bootstrap/`).
- [ ] `python -m pytest` green; `coga validate` clean.

## Context

**Reuse the pilot's seam — don't rebuild it.** `commands-as-tickets-open-pr-pilot`
(PR #625, in review) landed: local-first `coga/bootstrap/<name>/ticket.md`
resolution (over the package resource), the `COGA_ARG_1..N` + `COGA_ARGC`
env channel for **script** launches, and `open-pr` as the first shipped
command ticket + default alias. Read that ticket's blackboard and PR before
starting — it is the template for authoring `resolve-conflicts` and it
documents exactly where the agent-arg channel was deferred (`launch()` in
`src/coga/commands/launch.py`; agent launch with trailing args currently
fails loud *before* the TTY gate). Coordinate if #625 has not merged yet —
this ticket builds directly on its seams.

**The behavior already half-exists.** `coga/recurring/rebase-stale-worktrees/ticket.md`
enumerates live branches (worktrees + `branch:` under non-terminal tickets),
`git fetch`es, tests staleness with `git merge-base --is-ancestor`, rebases
onto `origin/main`, resolves *trivial mechanical* conflicts only, verifies
(pytest when `src/`/`tests/` touched), and `git push --force-with-lease` for
branches with an upstream. Lift its run-order and its report vocabulary
(`rebased-pushed`, `up-to-date`, `conflict`, `skipped-dirty`,
`verify-failed`) into the new command — the two differences are: (a) the new
command enumerates from **open PRs** (`gh pr list`) not from live branches,
and (b) it may resolve **semantic** conflicts with agent judgment, not just
mechanical ones. Then delete `rebase-stale-worktrees`.

**Safety posture.** Force-pushing a PR branch is outward-facing and hard to
reverse. The chosen posture is full agent judgment *with* mandatory
verification before push and explicit per-PR reporting; a PR the agent
can't confidently resolve is aborted (`git rebase --abort`, worktree left as
found) and reported for a human, never force-pushed. There is no dry-run
flag in this scope — the verification gate and abort-on-doubt rule are the
safety net. (`--dry-run` was considered and set aside; revisit if the sweep
proves too eager in practice.)

**Workflow note.** Runs `code/with-review` (implement → peer-review →
open-pr → review). This ticket deletes a recurring task and changes core
`launch`; the owner chose to see the approach at PR time rather than gate a
separate design step. The peer-review step is the last judgment gate before
the PR.

## Out of Scope

- A `--dry-run` / plan-only mode (deferred; abort-on-doubt + verify-before-push
  is the safety mechanism instead).
- Writing conflict-resolution outcomes onto originating tickets' blackboards
  (rejected — the command stays stateless; summary is stdout + Slack only).
- Keeping `rebase-stale-worktrees` alongside the new command (rejected — the
  new command supersedes it; two things force-pushing the same branch is the
  hazard being removed).
- Composing trailing args into *script* prompts (already shipped by #625) —
  this ticket adds only the **agent**-launch arg composition.
- Re-litigating the `commands-as-tickets` seam (local-first resolution, the
  alias mechanism, the `requires: pr` gate) — reuse it as-is.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
