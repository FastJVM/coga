---
slug: refuse-recurring-runs-from-a-non-control-branch
title: Refuse recurring runs from a non-control branch
status: draft
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
step: 1 (implement)
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
