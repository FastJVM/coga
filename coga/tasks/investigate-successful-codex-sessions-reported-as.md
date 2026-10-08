---
title: Investigate successful Codex sessions reported as failed
status: draft
owner: nicktoper
workflow: code/design-then-implement
---

## Description

Determine why apparently successful Codex sessions are recorded with
`outcome_status: failed` in their activity records, and correct the
classification only where lifecycle and process evidence prove it wrong. A
success-looking final message or passing tests alone is not proof of success.

Reproduce with a live Codex session, bootstrap first (`coga orient` or
`coga ticket`, closed the way a human closes it), then an ordinary ticket
step. Capture the launch target, raw process exit status, supervisor exit
`kind`, done sentinel, recorded `outcome_status`, and expected workflow
progress. Preserve real failures, crashes, interrupts, and timeouts.

Done is one of two outcomes, chosen by the owner at `review-design`:

- **Misclassification confirmed:** fix the mapping for the confirmed
  mechanism, add a regression test, and update the `outcome_status` meaning
  in coga/internals/activity-capture (canonical and packaged twin).
- **Classification correct** (Codex really exits non-zero, and `failed`
  correctly means process failure): no mapping change. Deliver the evidence,
  clarify the `outcome_status` definition in activity-capture, and, if the
  owner approves, start recording `exit_code` / exit `kind` so future
  records can be audited. This may be a docs-only change.

## Context

### Evidence already on disk

The reported 2026-10-05 session is in `coga/log.md` (search session_id
`01a10dfa-c7d1-7062-b33d-94413f67a6c1`): `[bootstrap/orient]`, cli `codex`,
`outcome_status: failed`, with outcome text "Merged all five open PRs… 80
passed". Its Codex transcript is under
`~/.codex/sessions/2026/10/05/rollout-2026-10-05T14-31-41-01a10dfa-*.jsonl`.
As of 2026-10-08, `coga/log.md` holds 24 `outcome_status: failed` records,
all codex. Claude has 0 failures in about 665 completed records, and codex
has about 351 completed. Of the 24, 15 are bootstrap sessions (9
`bootstrap/orient`, 6 `bootstrap/ticket`), which suggests interactive,
human-closed sessions. Records store neither `exit_code` nor exit `kind`, so
past records cannot confirm a mechanism. Confirming one needs a live repro.

### Where `failed` comes from

- `commands/launch.py` `_session_outcome_status`: `timeout` gives
  `timed_out`; `crash` **or any non-zero `exit_code`** gives `failed`;
  anything else gives `completed`. It never produces `interrupted`, although
  the schema defines it.
- An exception raised in `spawn_agent_session` is also recorded `failed`.
- `repl_supervisor._classify_exit` returns 0 for a done-signal teardown and
  passes a `natural` exit's raw status through. `run_with_done_marker`
  drives the session.
- `usage.py` (`OutcomeStatus`) only stores the value.

Leading hypothesis, not a confirmed cause: a human quits Codex (Ctrl-C,
`/quit`, or similar), Codex exits non-zero, the exit is classified
`natural`, and the record says `failed`. Check how Claude exits on the same
quit path before concluding the effect is Codex-specific.

Megalaunch's no-progress `failed` *result* (`megalaunch.py`) is a separate
field from `outcome_status`; leave it unchanged.

### Related ticket

`where-have-code-review-disappeared` owns workflow chains that stop
advancing (sentinel and stale environment). The two tickets share
`_classify_exit` only in passing. If a done-signal teardown ever turns out to
be recorded `failed`, coordinate the fix with that ticket.

### Topics (cited, not attached)

- coga/internals/activity-capture (`docs/contexts/coga/internals/activity-capture/SKILL.md`):
  this ticket edits its `outcome_status` definition, so read it first,
  especially the schema-2 activity fields and "Capture point and gates".
- coga/launch (`docs/contexts/coga/launch/SKILL.md`): read the supervisor and
  exit-classification sections.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
