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
step: 2 (peer-review)
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

## Decisions (confirmed with the human in the implement session)

- **Pause classification:** the sweep's own pause after an unfinished run now
  logs actor `system:recurring` (`recurring.SWEEP_ACTOR`). A pause counts as
  resumable only when it is positively identified:
  - `system:watchdog` → `PAUSE_WATCHDOG`.
  - `system:recurring`, or a legacy `human:` line ending in
    "— Agent recurring launch exited unfinished" → `PAUSE_SWEEP`.
  - Anything else (`human:` without that suffix, `agent:<name>` from an assist
    `mark paused` even with the suffix, any other `system`) is a human pause
    and stays parked.
  `recurring._watchdog_pauses` was generalized into `recurring._pause_origins`
  (still a single log pass; the latest `paused`/`created` event wins).
- **Watchdog loudness:** a bare sweep resumes a watchdog pause and still counts
  it in `problems:`, notifies and exits 2, even when the retry completes. The
  row reads `needs attention (watchdog timeout; resuming)`. `--force` keeps its
  old behavior: a successful forced recovery clears the problem.
- **Named launch:** `coga recurring launch <name>` resumes the same pauses
  (`recurring_runner._resume_named_pause`). It does not add watchdog
  problem/notify reporting, because that path had none before. An
  agent-backed resume with no TTY (or on Windows) refuses with exit 2 before
  reactivating anything.
- **When reactivation happens:** a resume flips the period to active
  (actor `system:recurring`, "activated (paused → active) to resume a
  <sweep|watchdog>-paused run") only when the launch loop reaches it, then
  re-captures the lease, like `_prepare_forced_launch`. The scan itself never
  mutates. A `mark_active` failure is a per-period refusal, not a sweep abort.
- **Unblock:** `coga unblock` on a paused `recurring/` period with open asks
  resolves them, logs "unblocked (asks resolved, still paused)" and leaves the
  status paused. Ordinary paused tickets and paused periods with no open asks
  are still refused.
- `mark.mark_paused` docstring: the stale "interactive recurring-cleanup path"
  now names the sweep's unfinished-run pause.

## Implementation notes

- `recurring.DueTask` gained `sweep_pause`, `open_asks`, `sweep_paused` and
  `resumes_pause`.
  - `resuming` now also covers `resumes_pause`, which gives the "→ resume" row
    and resume-first ordering.
  - `DueScan.due` admits `resumes_pause` unless the task has a `launch_refusal`.
  - `launchable` is unchanged.
- The headless refusal in `scan_due` now applies to `force or
  task.resumes_pause`. A watchdog pause keeps its `launch_refusal` for
  reporting; a sweep pause becomes an ordinary `agent_refusals` row.
- Both scan renderers (`recurring_runner._print_table` and
  `recurring_autofix.scan_lines_for_record`) share the
  `_watchdog_row_detail`/`_open_asks_row_detail` helpers. A sweep pause with
  open asks shows `skip (paused; open asks — coga unblock <ref>)`.
- `blocker_reminders.BlockerReminder.next_command` is always `coga unblock`.
  The paused-period reminder text says the next sweep resumes it.
- Existing tests whose expectations changed:
  - `test_bare_recurring_continues_past_unfinished_interactive_task`: the
    second sweep now resumes.
  - The watchdog scan test now expects `due == [task]` when a TTY is present.
  - The old non-forced interactive variant of the watchdog escalation test is
    now covered by the headless bare-sweep case plus the new retry test.
  - Fake `SimpleNamespace` due tasks gained `resumes_pause=False`.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Handoff (implement → next step)

Implemented, rebased on origin/main (0b52bee2b; only coga state commits came
in), full suite green, pushed as `coga/recurring-unblock-launch-9cca77`. No PR
yet. Self-review was limited to reading the diff once more and adding the
`mark_active` failure → per-period refusal wrapping. No independent review has
run; that belongs to the later review step. No adjacent bugs found. Nothing is
out of scope or left open beyond the ticket's own out-of-scope list.

## PR

```yaml
title: Resume non-human-paused recurring periods without --force
author: claude
author_evidence: Implement session ran as Claude Code (claude-opus-5-5); no agent override.
head: 0bcf9a38c8acfb74fcc886f1e7ca3379e9272571
base: 0b52bee2b63315d3afc8375a2df74a8b1197729b
depth: deep
rationale: >-
  Changes scheduled-run lifecycle behavior: the bare sweep and named launch now
  reactivate paused periods based on audit-log provenance. The sweep's own pause
  gets a new audit actor, and `coga unblock` accepts a new status. Read the
  classification rule and the watchdog problem semantics. Only self-review so far.
implementation: >-
  `recurring._pause_origins` (generalized from `_watchdog_pauses`, still a
  single log pass) classifies a period's latest pause as watchdog
  (`system:watchdog`) or sweep (`system:recurring`, or the legacy `human:` line
  with the "Agent recurring launch exited unfinished" suffix). Any other pause
  is human. `DueTask.resumes_pause` admits watchdog pauses, and sweep pauses
  with no open `## Blockers` asks, into `DueScan.due`. The launch loop
  reactivates them (`_resume_paused_period`, actor `system:recurring`) only
  when it reaches them, then re-leases. The headless TTY refusal now applies to
  these resumes as well as `--force`. A named launch reuses the classification
  through `recurring.resumable_pause` and refuses before reactivating when it
  has no TTY. `coga unblock` resolves the asks on a paused `recurring/` period
  and leaves it paused. Blocker reminders point to `coga unblock`.
deviations: >-
  None from the ticket. Decisions confirmed with the human: on a bare sweep, a
  watchdog retry stays a problem (row, notification, exit 2) even when it
  completes, while `--force` keeps clearing the problem on a successful
  recovery. A named launch resumes watchdog pauses without adding problem or
  notification reporting.
limitations: >-
  The legacy sweep-pause match keys on the exact log suffix. A human
  `mark paused --message` whose reason ends with that exact suffix under a
  `human:` actor would be classified as a sweep pause.
files:
  src/coga/recurring.py: Pause-origin classification, DueTask resume properties, due-set admission, headless refusal for resumes, resumable_pause for named launch.
  src/coga/recurring_runner.py: system:recurring pause actor, non-forced resume in the launch loop and named launch, watchdog report wording, scan-row text.
  src/coga/recurring_autofix.py: Run-record scan rows mirror the console rows for watchdog retries and sweep pauses waiting on asks.
  src/coga/commands/unblock.py: Accept a paused recurring period with open asks; resolve only, stay paused.
  src/coga/blocker_reminders.py: Paused-period reminders point to coga unblock and say the next sweep resumes.
  src/coga/mark.py: Fix the stale mark_paused docstring caller list.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Owner doc for sweep/named resume rules, pause provenance, watchdog loudness, admission.
  docs/contexts/coga/recurring/delegation/SKILL.md: Scans now resume non-human pauses of delegated periods.
  docs/contexts/coga/lifecycle/SKILL.md: unblock transition row and Blocking and resume text for paused recurring periods.
  coga/recurring/blocker-reminders/ticket.md: Reminder wording and the unblock eligibility statement.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Packaged twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md: Packaged twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Packaged twin, byte-identical.
  src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.md: Packaged twin, byte-identical.
  tests/test_recurring.py: Classification matrix; sweep and named resume of watchdog and sweep pauses; open asks wait for unblock; human and assist pauses stay parked; headless refusal; watchdog retry stays loud; updated expectations for changed behavior.
  tests/test_commands.py: Unblock on a paused recurring period (with and without asks) and refusal of an ordinary paused ticket.
  tests/test_blocker_reminders.py: Paused-period reminder points to coga unblock.
review:
  reviewer: claude
  kind: self
  status: passed
  head: 0bcf9a38c8acfb74fcc886f1e7ca3379e9272571
  base: 0b52bee2b63315d3afc8375a2df74a8b1197729b
  detail: Author re-read the runner diff and fixed the unguarded mark_active in resume. No independent review yet; the later workflow step owns it.
checks:
  - command: .venv/bin/python -m pytest -q -p no:cacheprovider
    status: passed
    head: 0bcf9a38c8acfb74fcc886f1e7ca3379e9272571
    base: 0b52bee2b63315d3afc8375a2df74a8b1197729b
    detail: 4072 passed, 10 skipped in 414.86s, run on the clean committed tree after the rebase.
  - command: coga validate --json
    status: not-run
    detail: No validation, config, workflow or task-model behavior changed.
```
