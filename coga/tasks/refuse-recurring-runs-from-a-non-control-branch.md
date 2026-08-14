---
slug: refuse-recurring-runs-from-a-non-control-branch
title: Refuse recurring runs from a non-control branch
status: in_progress
owner: nick
human: nick
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
    skills:
    - code/address-pr-comments
    assignee: owner
secrets: null
step: 3 (open-pr)
---

## Description

`coga recurring` writes shared scheduler state — it creates the period task,
records the serviced period, posts to Slack, and launches real work. Doing
that from a branch nobody will merge is wrong, and only one of the three entry
points currently prevents it.

| entry point | non-control checkout today |
| --- | --- |
| `coga recurring --all <path>` | refuses (dispatches `--require-fresh-control`) |
| bare `coga recurring` | one stderr note, scan proceeds |
| `coga recurring launch <name>` / `coga dream` | result discarded (`fresh, _reason = ...`; `_reason` never read) |

This is how the Magicator digest incident happened: `coga recurring` ran from
`coga-repo-context`, not `main`.

Make the control branch a precondition for every recurring entry point.

### Gate only the branch, not freshness

`_sync_control_checkout_ahead` conflates two failures: the control branch not
being checked out, and the fetch/rebase to `origin` failing. Only the first
should become fatal for the interactive entry points. Making the whole check
fatal would also refuse an **offline** run on the control branch, which is a
different behavior change and not wanted — a laptop with no network should
still be able to service a period from `main`.

`--all` keeps its stricter freshness requirement on top; it is unattended, so
starting from a stale tip is its own hazard.

### Scope

- Add a branch-only precondition and call it from `run_recurring_scan` and
  `run_recurring_named`, before any period state is read or written.
- Fail loud and actionable: name the current branch, the configured control
  branch, and the fix.
- Self-skip where the existing gate does — `[git].enabled = false` and
  workspaces outside a git checkout.
- Leave `--all`'s freshness gate as it is.
- Decide and document whether an override exists. Default: no. The refusal
  tells you to check out the control branch, matching `--all`.

### Consequence to accept

`coga dream` and `coga recurring launch <name>` from a feature branch start
refusing. That is the point: Dream opens PRs and deletes tickets, and the
digest posts to Slack.

It also makes the recurring path's feature-branch control landing unreachable
(`branch == control` always holds in `_sync_recurring_create`). Leave that
code and its tests in place — it stays correct, and repos mid-upgrade may
still have feature-branch state to land — but note it is no longer reachable
from a normal run, so a later cleanup can consider removing it.

### Acceptance criteria

- Bare `coga recurring`, `coga recurring launch <name>`, and `coga recurring
  --force` all refuse from a non-control branch, with a message naming both
  branches.
- An offline run on the control branch still proceeds (warn only).
- `[git].enabled = false` and non-git workspaces are unaffected.
- Refusal happens before task creation, ledger writes, Slack, and launch.

## Context

- `src/coga/recurring_runner.py` — `_sync_control_checkout_ahead` (the
  existing combined check), `run_recurring_scan` (line ~637, the
  `require_fresh_control` branch), `run_recurring_named` (line ~882, where the
  result is discarded), and `run_recurring_all_repos`.
- `src/coga/commands/recurring.py` — the Typer surface for all three.
- `coga/contexts/coga/recurring` — documents the entry conditions.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

pr: https://github.com/FastJVM/coga/pull/693
branch: fix/recurring-control-branch-gate
worktree: /tmp/coga-recurring-control-branch-gate

## Implementation notes

- Keep `--all` on its existing strict fetch/rebase gate.
- Add a separate local branch-only precondition shared by scheduled scans and
  named launches. It must skip git-disabled and non-git workspaces, reject a
  named/detached non-control checkout before recurring state is consulted, and
  provide no override (including `--force`).

## Result

- Rebased commit `527a3d9a` (`Require control branch for recurring runs`) adds the
  branch-only precondition to bare/forced scans and named launches before
  catch-up, owner resolution, period discovery, creation, Slack, or launch.
- The refusal names the current and configured control branches, recommends
  `git switch <control>`, and states that `--force` is not an override.
- `--all` retains its stricter freshness gate and temporary-failure exit path;
  control-branch fetch failures remain warn-only for single-repo runs.
- Git-disabled and non-git workspaces remain ungated. The low-level
  feature-branch state-landing logic and its tests remain for mid-upgrade repos,
  while the recurring context now documents that normal runs cannot reach it.
- Peer review found two branch-probe edge cases. Rebased commit `a85255d3`
  (`peer-review: apply review findings`) now fails closed when Git inspection
  itself fails and uses the unambiguous `git branch --show-current` identity so
  a same-named tag cannot disguise the checked-out control branch.

## Verification

- Post-review `python -m pytest tests/test_recurring.py -q` — 176 passed.
- Post-rebase `python -m pytest` — 1747 passed, 1 skipped.
- `PYTHONPATH=$PWD/src python -m coga.cli validate --json --task
  refuse-recurring-runs-from-a-non-control-branch`
  — task valid; expected warning only because the isolated worktree has no
  gitignored `coga.local.toml`.
- Final `git fetch origin main && git rebase FETCH_HEAD` — clean rebase; branch
  is clean and two commits ahead of `origin/main`.

## PR

Require every mutating recurring entry point—the bare and forced sweep, the
registered `recurring-scan` recipe, named launches, and aliases such as
`coga dream`—to start on the configured control branch before consulting or
changing period state. The gate has no override, but remains branch-only for
single-repo runs so an offline control checkout can proceed; `--all` keeps its
stricter freshness requirement, while git-disabled and confirmed non-git
workspaces remain unaffected. Git inspection failures now fail closed, and
branch identity remains correct even when a tag shadows the control-branch
name. The recurring contract and real-git regression coverage are updated with
the behavior.

Test plan: `python -m pytest` (1747 passed, 1 skipped).
