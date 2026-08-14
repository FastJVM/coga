---
slug: read-the-recurring-serviced-period-from-the-log-dr
title: Read the recurring serviced-period from the log, drop the blackboard marker
status: in_progress
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- coga/recurring
- coga/codebase
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

`coga recurring` decides "has this period already been serviced?" from
`last_serviced_period`, a single line in the recurring template's blackboard
region. Make the repo-global `coga/log.md` the ledger instead and delete the
marker outright.

### Why the marker fails

The blackboard is a shared free-text region, so a co-writer that rewrites part
of it can destroy the mark. The digest recipe does exactly that: `_STATE_RE`
matches `### Digest State` through EOF, and `_write_digest_state` replaces the
whole match — including a `last_serviced_period` line appended after it.

Observed in Magicator on 2026-07-27 (one-off) and again on 2026-08-13 as an
unbounded loop: three consecutive `coga recurring` invocations each printed
`digest ... → launch` / `Replaced completed recurring/digest` and posted a
separate Slack digest (7, then 2, then 8 items). Template git history shows the
writers alternating every cycle — a `recurring create` commit adding
`last_serviced_period: 2026-08-13`, the following digest `Sync coga state`
commit removing it. Each erasure sends `create_template` down the prior-period
branch (`done` and `not _period_already_serviced`), which deletes the completed
period task, recreates it, and reruns the recipe.

The loop is silent: the scan table prints `ready` / `→ launch`, which is
indistinguishable from a legitimate first firing.

### Why the log is the right ledger

- **It already holds the answer.** Every path that advances the marker also
  appends a line carrying the same period key —
  `_advance_serviced_period` → `_record_run`, and the two force paths →
  `_append_forced_reused_log`. No path advances the marker silently, so the log
  can never under-report a serviced period. In the 2026-08-13 incident the log
  recorded `deleted completed prior-period task before 2026-08-13` four lines
  after `created recurring/digest for 2026-08-13`; the proof was already on
  disk and simply never read.
- **Append-only is the anti-clobber property.** A co-writer rewriting a region
  cannot destroy an appended line.
- **It outlives the task.** Dream's Retro pass direct-deletes completed period
  tickets, so for most templates the task is gone and the ledger is the only
  surviving record. The log is repo-global, so it covers the reaped case and
  the surviving-task case identically.
- **Precedent exists.** `_append_forced_reused_log` already dedups by scanning
  `task_log_lines` for `reused <slug> for <period>`.
- **The marker is forbidden state.** `coga/principles` #3 forbids
  "derived/denormalized state that hides what a file already says". A cache of
  what the log records is precisely that, which is why this drops the marker
  rather than repairing it.

### No migration

The log record predates the marker — `_record_run`'s ancestor lands 2026-05-22,
`last_serviced_period` 2026-06-13 — so there is no historical period that
advanced the marker without a log line. Existing repos work from their existing
log.

### Scope

- Read the serviced period from `coga/log.md`, keyed by the `recurring/<name>`
  tag, in **one reverse pass** that short-circuits once every template resolves.
  The log is designed to grow unbounded, so do not scan it once per template.
- Give the log line one shared constant used for both write and parse, and pin
  the format with a test. Dedup now depends on the wording, so a reworded
  message must break a test rather than silently disable dedup.
- Delete `read_`/`write_`/`merge_last_serviced_period_text`,
  `set_last_serviced_period_text`, `_last_serviced_period_from_text`,
  `_local_blackboard_with_control_period`, and the cross-branch marker
  reconciliation in `recurring_runner.py`. The scanner should stop writing the
  template during a scan.
- Repoint `coga recurring list` and the `coga status` recurring footer, which
  read the marker for `ran this period — task reaped`.
- Strip the vestigial `last_serviced_period` line from shipped templates.
- Update the `coga/architecture` context — it currently states the log is "not
  the dedup source" — in both the live copy and the packaged copy.

### Out of scope

- Period keys compare as strings, so `2026-W33` and `2026-08-13` sort
  lexically. That is
  `recurring-last-serviced-period-compares-as-a-strin...`; the log-based read
  inherits the same comparison and neither fixes nor worsens it. Note on that
  ticket that the two now share a code path.
- The sync path committing a conflicted working tree (the 2026-08-13 run left
  `<<<<<<<` / `>>>>>>>` markers committed in `coga/recurring/digest/ticket.md`
  via a single-parent `Sync coga state` commit). Separate defect.

### Acceptance criteria

- Erasing or hand-removing any template blackboard content cannot cause a
  serviced period to re-fire.
- Repeated `coga recurring` invocations inside one period launch each template
  at most once.
- No `last_serviced_period` read or write remains in the source tree.
- Rollback paths that remove generated audit lines are checked: confirm a
  rolled-back create re-fires (correct) rather than wedging.

## Context

- `src/coga/recurring.py` — `_period_already_serviced`, `_advance_serviced_period`,
  `_record_run`, `create_template`'s replace-done branch, and the marker
  read/write helpers.
- `src/coga/recurring_runner.py` — the cross-branch marker reconciliation
  (~1101, 1311, 1340, 1421-1441, 1459, 1566, 1856) and
  `_append_forced_reused_log`, the existing log-as-dedup precedent.
- `src/coga/logfile.py` — `task_log_lines`; needs a reverse/single-pass read.
- `src/coga/views.py` and `src/coga/commands/recurring.py` — the template
  footer and `recurring list` period column.
- `src/coga/commands/digest.py` — `_STATE_RE` / `_write_digest_state`, the
  co-writer that exposed the bug; no longer needs to defend the marker.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev

branch: fix/recurring-log-reverse-pass
worktree: /tmp/coga-recurring-log-reverse-pass

## Implement notes

- PR #688 (`f5543446`) landed the main marker-to-log conversion before this
  workflow step started. The remaining ticket gaps are the required reverse,
  bounded ledger read and rollback coverage; source/help prose also still
  describes the removed blackboard marker.
- Preserve the exact `created|reused <task-ref> for <period>` contract while
  making scan/list callers supply the finite recurring refs they need, so one
  reverse pass can stop as soon as all of them resolve.
