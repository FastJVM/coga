---
title: Recurring sweep resumes non-human-paused periods
status: in_progress
owner: nicktoper
workflow:
  name: code/with-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
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
step: 1 (implement)
agent: claude
---

## Description

A scheduled sweep (`coga recurring`) and a named `coga recurring launch
<name>` currently skip every `paused` period. A period gets parked when its
agent run comes back unfinished, when it `coga block`s, or when it hits the
liveness watchdog. It then stays parked until the owner opens it by hand with
`coga launch recurring/<name>` or `coga mark active`, even when nothing
human-specific stopped it.

Change both entry points so they **resume every paused period that was not
paused by a human**, using these rules:

- **Watchdog pause:** resumed on the next sweep. There is no retry cap. Keep
  the existing `needs attention (watchdog timeout)` row, the `problems:` count,
  the notification and the non-zero exit, so a failure that keeps recurring
  stays loud even while it is retried.
- **Sweep pause after an unfinished run** (an owner handoff, an agent that
  exited without finishing, or a run that ended `blocked`):
  - With no open `## Blockers` asks, resume it on the next sweep.
  - With open asks, **resume it only once the asks are resolved**. Until then
    it stays parked, and blocker-reminders keeps reminding. This follows the
    rule that "a scheduled agent run must reach `done` in one launch", and it
    avoids a session on every sweep that would only block again.
- **Anything else counts as human and stays parked.** This includes a human
  `coga mark paused` and any pause whose origin cannot be positively
  identified as a sweep or watchdog pause.

Admission gates are unchanged:

- Agent-backed periods still need a TTY. A non-forced resume goes through the
  same headless refusal that `--force` uses today.
- The control-branch and `owner` gates still apply.
- The cleanup template, Dream, still launches last.
- The existing frozen period is resumed. It is not replaced because a newer
  period is due.

Also let `coga unblock recurring/<name> --answer "..."` accept a `paused`
recurring period that has open asks. It resolves them exactly as it does for a
blocked ticket and leaves the period `paused`, so the next sweep (or named
launch) resumes it with the answer on its blackboard. Ordinary non-recurring
paused tickets are still refused.

Done when tests cover each of these:

- Classification: a watchdog pause, a sweep pause (including the legacy log
  form), a human pause, a human pause from an assist session, and a pause of
  unknown origin.
- The sweep and the named launch resume watchdog pauses and sweep pauses with
  no open asks, without `--force`.
- A sweep-paused period with open asks stays parked until `coga unblock`
  resolves them, then resumes.
- A human-paused period is still skipped.
- A headless sweep still refuses an agent-backed resume, and watchdog periods
  stay counted in `problems:`.
- `coga unblock` resolves the asks on a paused recurring period and refuses an
  ordinary paused ticket.

The same PR updates the owning docs listed below and their packaged twins.

## Context

### Telling a human pause from a sweep pause

The audit actor does not separate them today. The `recurring_runner` path that
pauses after an unfinished run (near the `"Agent recurring launch exited
unfinished"` suffix) logs the sweep's own pause as `human:<current_user>`:

```
2026-08-14 10:58 [recurring/resolve-conflicts] [human:nicktoper] paused (blocked → paused) — Agent recurring launch exited unfinished
```

Two more facts complicate classification:

- Only the watchdog has a distinct actor, `system:watchdog`.
  `recurring._watchdog_pauses` reads pause provenance from `coga/log.md` in
  one pass, and the latest `paused`/`created` event wins.
- A human `coga mark paused` inside an assist session logs `agent:<name>`
  (`commands/mark.py`), so an actor of `human:` does **not** mean the pause was
  human.

Recommended approach: give the sweep's own pause a dedicated actor, such as
`system:recurring`. Then classify a pause as resumable only when it is
positively identified, meaning that actor or `system:watchdog`. Classify a
legacy pause as a sweep pause only when the actor is `human:` **and** the line
carries the "Agent recurring launch exited unfinished" suffix. Record the
choice on the blackboard. Generalize `_watchdog_pauses` rather than adding a
second log pass.

An `unblock` on a paused period logs an `unblocked` event and leaves the
status `paused`. Pause provenance still comes from the earlier `paused` line,
because the scan only reads `paused`/`created` events.

### Where the behavior lives today

- **Due scan in `recurring.py`:** builds `tasks`, attaches `watchdog_pause`,
  and under `force` reactivates paused periods. The headless TTY refusal for
  paused periods and the watchdog `launch_refusal` also run only under `force`
  today. The non-force scan uses `retain_paused=True` only to inspect paused
  periods. The new behavior is selective reactivation without `--force`, so
  reuse that refusal path.
- **`recurring_runner.py`:** contains the pause after an unfinished run and the
  activation of `draft`/`paused` periods under `activate_if_needed`. A
  script-backed period that stops `blocked` is never paused (it stays
  `blocked`), and that case is out of scope.
- **`commands/unblock.py`:** contains the `status not in {"blocked",
  "in_progress"}` refusal. Extend it only for `paused` `recurring/` periods
  that have open asks.
- **`blocker_reminders.py`:** `BlockerReminder.next_command` points paused
  periods at `coga launch`. Point it at `coga unblock` instead.
- **`mark.mark_paused`:** its docstring mentions an "interactive
  recurring-cleanup path" that may be stale. Check it while you are there.

### Docs to update in the same PR

These are edited, so they are not attached.

- `docs/contexts/coga/recurring/scheduling/SKILL.md`, in these sections:
  - "What a sweep does per template": paused runs are skipped today.
  - "Variants": a named launch leaves "any `paused` run" alone.
  - "Admission and unfinished runs": "it does not resume them", the "Keep
    human gates and expected blockers out of scheduled workflows" guidance,
    and the watchdog resume text.
- `docs/contexts/coga/recurring/delegation/SKILL.md`: "scheduled and named
  scans leave paused periods parked".
- `docs/contexts/coga/lifecycle/SKILL.md`: the transition table (the `coga
  unblock` row) and "Blocking and resume".
- `coga/recurring/blocker-reminders/ticket.md`: the paused-period reminder
  wording and the line "Direct unblock requires a blocked or in-progress
  ticket".

All four have packaged twins under `src/coga/resources/templates/coga/` (three
under `bootstrap/contexts/`, plus `recurring/blocker-reminders/ticket.md`).
`tests/test_packaging.py` enforces byte-identity.

### Out of scope

- Resuming human-paused periods.
- Ordinary non-recurring paused or blocked tickets.
- Script periods that stay `blocked`.
- A retry cap.
- Auto-answering asks, or deciding from external signals that a blocker is
  resolved.

<!-- coga:blackboard -->
## Dev

branch: coga/recurring-unblock-launch-9cca77


The blackboard is a notepad to be written to often as the human and agent works through a task.
