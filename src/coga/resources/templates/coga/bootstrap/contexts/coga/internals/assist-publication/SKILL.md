---
name: coga/internals/assist-publication
description: Where a human-step assist's lifecycle, script, and audit writes are published (control only, never the PR branch), how failures behave, and what the assist identity does and does not authorize.
---

# Assist publication

A recorded human-step assist
([human assist](../human-assist/SKILL.md)) runs in the checkout that holds
the PR's feature branch. That checkout's copy of the ticket is the live one,
yet nothing the assist generates is committed to that branch. Every write
goes through the same `git.publish` path as any other checkout and lands on
the control branch only (`coga/sync`; the strict-versus-best-effort split is
in `coga/internals/state-publication`).

## What is published, and where

| Write | Destination |
| --- | --- |
| Inline activation (draft, paused, blocked) | control |
| `active → in_progress` start | control |
| `launched as a script` line, `script exited with code N`, and the script's ticket result (published immediately after the child exits) | control |
| In-session `coga bump`, `mark`, `block`, `unblock` | control |
| A successful `requires: pr` bump | control |
| Teardown usage record and launch log line | control (`sync_log`) |

The feature branch receives only commits the agent or human make on purpose,
plus whatever `coga open-pr` pushes
([PR publication](../pr-publication/SKILL.md)).

## Consequences

- The single checkout keeps Coga's live task, log, and recurring state dirty
  by design. `coga open-pr` publishes the pending log append first, then
  leaves those paths out of its cleanliness gate; any other dirt still
  refuses. Assist alignment tolerates the same three paths and nothing else.
- Assist writes use ordinary best-effort publication: a refused or failed
  sync is reported on stderr and in the log, the local transition stands,
  and the end-of-command state sweep retries it. There is no assist lease,
  compensation, or uncertain-push retention; those belong to megalaunch
  claims ([launch claims](../launch-claims/SKILL.md)) and recurring
  admission (`coga/internals/recurring-admission`).
- Publication authority comes from the PR-head proof made before
  composition, not from the environment. `COGA_ASSIST_*` only attributes
  audit lines to the assisting agent. Inside an assist, `coga bump` refuses
  every rewind (`--to` / `--backward`); a human rewinds outside the assist.
- The deterministic attribution marker (`COGA_SCRIPT_TASK`,
  [script tickets](../../script-tickets/SKILL.md)) is independent of the
  assist identity. A script inside an assist credits `system`, and the marker
  can never stand in for the PR-head proof.
- A missing assist agent or PR on a script launch raises
  `ScriptPublicationError` before any user code runs, as does a notification
  configuration that fails `preflight_post`. If notification config breaks
  while the script runs, the child's exit code stays authoritative.

## Source notes

The comment above `ASSIST_BRANCH_ENV` in `src/coga/repl_supervisor.py` still
describes publishing generated task and log commits back to the PR branch.
It is stale: `src/coga/pr_assist.py` and every lifecycle caller publish to
control only.
