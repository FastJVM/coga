---
title: Recurring sweep resumes non-human-paused periods
status: done
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

pr: https://github.com/FastJVM/coga/pull/1118
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

## Peer review

Direct Codex review **completed** on final head `d7b10ad6d0318905b791dcf3024bd90345ce23ed`
against base `33cb4c613012491b2fed36d9ee1e6f6c45778c52`. No unresolved must-fix findings.
Claude authored the original implementation (implement handoff and original
commit identify Claude Opus 5.5). Codex independently reviewed it here, then
authored and self-reviewed the corrections below. The final PR receipt is
therefore labeled self-review rather than claiming complete independence.
No child review CLI, review tool, or subagent was invoked.

Two must-fix findings were reproduced in both sweep and named launch and fixed:

- **P2 — unavailable frozen agent aborts the sweep.** `MainAgentUnavailable`
  escaped the resume wrapper and abandoned later templates. Activation errors,
  including unreadable resources, now become per-period refusals.
- **P2 — unreadable asks abort the sweep.** Missing or duplicate blackboard
  fences raised `TaskFileError` outside the per-template error path. The shared
  ask reader now reports an error, preserves the paused ticket, and lets later
  templates run; named launch returns a controlled refusal.

Eight added regression cases passed. They verify both entry points,
sweep/watchdog activation failures, missing/duplicate blocker fences, later
healthy work, and byte preservation of the refused ticket. The owning
scheduling topic and packaged twin describe the failure behavior.

Verification:

- `.venv/bin/python -m pytest -q -p no:cacheprovider`: **4081 passed,
  10 skipped in 414.26s**, Python 3.12.12, on `c5429ef49c63bcd51cfc02afd29d23d3a200454f` against
  `fe0b7fa198f6b11a3f7015073ea382ccc436aed5`. This receipt is historical after the final knowledge-only
  rebase and is not re-stamped.
- Final-head `.venv/bin/python -m pytest -q -p no:cacheprovider
  tests/test_packaging.py`: **30 passed in 3.11s**. `git diff --exit-code`
  verified runtime implementation and tests identical to the full-suite-tested
  revision; `git diff --check origin/main...HEAD` passed. Exact commands and
  head/base pairs are in the PR record below.
- Drove scan-table and run-record rows in real PTYs at 80x24 and 120x40 on
  the final head. Watchdog retries remain loud; resume, open-ask unblock,
  human-pause and headless-refusal rows are complete, using ordinary wrapping
  for long rows. Drove the actual `unblock` prompt at 80x24 in an isolated
  Git-disabled fixture: the ask displayed, the answer persisted, asks cleared,
  and paused status and current step remained. No external agent session or
  live Slack message was used in these checks.

Reconciliation preserved the projected ticket byte-for-byte. Main first added
log events, then PR #1097 (CI and Windows cross-drive skill linking), then
knowledge-only PRs #1099, #1101, #1102 and #1103. Read the changed testing
instructions and relevant incoming contracts. The last rebase added a size
exception to the scheduling topic; it changed no retry policy or runtime code.
Range-diff confirmed both recurring commits unchanged through the rebases.
Main already contains the live blocker-reminders template change from state
publication; its packaged twin remains in this diff. All four requested twin
pairs match.

## Handoff (peer-review → open-pr)

Branch `coga/recurring-unblock-launch-9cca77` is committed and pushed at
`d7b10ad6d0318905b791dcf3024bd90345ce23ed` (explicit force-with-lease against the prior remote tip succeeded).
The only local edit is this projected ticket, which was never staged or
committed. Review is complete; no design decision or must-fix finding remains.
No PR exists yet. The prepared PR title recommends **deep** review, discloses
actual authorship and review independence, explains every current diff path,
and preserves the historical full-suite receipt alongside current checks.
Ready for the mechanical `open-pr` step.

## PR

```yaml
title: Resume non-human-paused recurring periods without --force
author: claude/codex
author_evidence: Claude Opus 5.5 authored the original implementation (implement handoff and
  original commit Co-Authored-By trailer). Codex independently reviewed that implementation
  in this session, then authored the two error-containment fixes and eight regression cases
  in the peer-review commit.
head: 7686375270e02de3d2a0df8c99e3c0a2683ef891
base: 198facc34d3cfeb059d642e38943ad75818698c1
depth: deep
rationale: Changes scheduled execution by using audit provenance to reactivate frozen periods
  and extends unblock to paused recurring periods. Review the pause classification, open-ask
  gate and watchdog failure reporting. Direct review completed with both findings fixed. The
  final diff includes reviewer-authored corrections, so the final receipt is self-review. The
  full-suite receipt predates the final knowledge-only rebase; current runtime/test identity
  verification and packaging checks cover that reconciliation.
implementation: '`recurring._pause_origins` (generalized from `_watchdog_pauses`, still a single
  log pass) classifies a period''s latest pause as watchdog (`system:watchdog`) or sweep (`system:recurring`,
  or the legacy `human:` line with the "Agent recurring launch exited unfinished" suffix). Any
  other pause is human. `DueTask.resumes_pause` admits watchdog pauses, and sweep pauses with
  no open `## Blockers` asks, into `DueScan.due`. The launch loop reactivates them (`_resume_paused_period`,
  actor `system:recurring`) only when it reaches them, then re-leases. The headless TTY refusal
  now applies to these resumes as well as `--force`. A named launch reuses the classification
  through `recurring.resumable_pause` and refuses before reactivating when it has no TTY. `coga
  unblock` resolves the asks on a paused `recurring/` period and leaves it paused. Blocker reminders
  point to `coga unblock`. Unreadable sweep-pause blocker state now becomes a per-template scan
  error (or a named-launch refusal), preserving the paused ticket and continuing the sweep.
  Missing frozen-agent configuration and unreadable activation resources become per-period resume
  refusals instead of escaping and abandoning later templates.'
deviations: No deviation from the confirmed retry policy. Bare sweeps retain watchdog failure
  reporting even after a successful retry; forced recovery retains its existing clearing behavior;
  named launch adds no watchdog reporting. The live coga/recurring/blocker-reminders/ticket.md
  edit was already adopted onto main by state publication, so the current diff contains only
  its matching packaged twin. Template scan errors keep their documented report-only exit semantics.
limitations: The exact legacy human-actor suffix can also match a human pause deliberately given
  that same message. The full suite passed on c5429ef49c63bcd51cfc02afd29d23d3a200454f before
  the final docs/retired-state rebase; its receipt is intentionally historical. Runtime implementation
  and tests are unchanged, and packaging plus terminal checks passed on the final head. Verification
  used Python 3.12.12 on Linux; the available Python 3.11 interpreter lacks pytest. External
  agent sessions and live Slack delivery were not exercised. Codex independently reviewed the
  original Claude implementation and self-reviewed its own corrections.
files:
  src/coga/recurring.py: Pause-origin classification, DueTask resume properties, due-set admission,
    headless refusal for resumes, resumable_pause for named launch. Isolate unreadable blocker
    state per period without treating it as an empty ask list.
  src/coga/recurring_runner.py: system:recurring pause actor, non-forced resume in the launch
    loop and named launch, watchdog report wording, scan-row text. Contain missing-agent and
    unreadable-resource activation errors; render named blocker-read refusals.
  src/coga/recurring_autofix.py: Run-record scan rows mirror the console rows for watchdog retries
    and sweep pauses waiting on asks.
  src/coga/commands/unblock.py: Accept a paused recurring period with open asks; resolve only,
    stay paused.
  src/coga/blocker_reminders.py: Paused-period reminders point to coga unblock and say the next
    sweep resumes.
  src/coga/mark.py: Fix the stale mark_paused docstring caller list.
  docs/contexts/coga/recurring/scheduling/SKILL.md: Owner doc for sweep/named resume rules,
    pause provenance, watchdog loudness, admission. Document isolated blocker-read and activation
    failures.
  docs/contexts/coga/recurring/delegation/SKILL.md: Scans now resume non-human pauses of delegated
    periods.
  docs/contexts/coga/lifecycle/SKILL.md: unblock transition row and Blocking and resume text
    for paused recurring periods.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/scheduling/SKILL.md: Packaged
    twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/delegation/SKILL.md: Packaged
    twin, byte-identical.
  src/coga/resources/templates/coga/bootstrap/contexts/coga/lifecycle/SKILL.md: Packaged twin,
    byte-identical.
  src/coga/resources/templates/coga/recurring/blocker-reminders/ticket.md: Packaged twin, byte-identical.
  docs/contexts/coga-dev/internals/spool-merge/SKILL.md: The audit-line reader list (added by
    PR 1104 during open-pr reconciliation) now names the renamed `recurring._pause_origins`.
  tests/test_recurring.py: Classification matrix; sweep and named resume of watchdog and sweep
    pauses; open asks wait for unblock; human and assist pauses stay parked; headless refusal;
    watchdog retry stays loud; updated expectations for changed behavior. Eight regression cases
    exercise unavailable frozen agents and malformed blocker fences across both entry points,
    including later-template continuation and byte-preserved paused tickets.
  tests/test_commands.py: Unblock on a paused recurring period (with and without asks) and refusal
    of an ordinary paused ticket.
  tests/test_blocker_reminders.py: Paused-period reminder points to coga unblock.
review:
  reviewer: codex
  kind: self
  status: passed
  head: d7b10ad6d0318905b791dcf3024bd90345ce23ed
  base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
  detail: 'Direct review completed on the final diff. Independent review of the Claude implementation
    found two must-fix sweep-abort paths: MainAgentUnavailable during resume and TaskFileError
    while reading paused asks. Codex fixed both, added eight regression cases, and re-reviewed
    the resulting diff, including its own corrections and the final reconciliation. Range-diff
    confirms both recurring commits unchanged through the latest rebases. No unresolved must-fix
    findings; no child review command or agent was used.'
checks:
- command: .venv/bin/python -m pytest -q -p no:cacheprovider -x
  status: passed
  head: 7686375270e02de3d2a0df8c99e3c0a2683ef891
  base: 198facc34d3cfeb059d642e38943ad75818698c1
  detail: 4081 passed, 10 skipped in 322.75s on Python 3.12.12, run during open-pr after rebasing
    onto main that had moved (PR 1104, knowledge-only) and adding one commit that renames
    the function in the coga-dev spool-merge reader list. The review receipt below covers d7b10ad;
    the only commit added since is that one-line doc rename.
- command: .venv/bin/python -m pytest -q -p no:cacheprovider
  status: passed
  head: c5429ef49c63bcd51cfc02afd29d23d3a200454f
  base: fe0b7fa198f6b11a3f7015073ea382ccc436aed5
  detail: 4081 passed, 10 skipped in 414.26s on Python 3.12.12. Historical after the final rebase,
    which brought only documentation, packaged Markdown and retired task records. The current-head
    identity check below confirms unchanged runtime implementation and tests; this result is
    not re-stamped onto the new revision.
- command: .venv/bin/python -m pytest -q -p no:cacheprovider tests/test_packaging.py
  status: passed
  head: d7b10ad6d0318905b791dcf3024bd90345ce23ed
  base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
  detail: 30 passed in 3.11s on Python 3.12.12 after the final knowledge-only rebase; includes
    packaged twins and wheel contents.
- command: git diff --exit-code c5429ef49c63bcd51cfc02afd29d23d3a200454f HEAD -- src/coga src/coga_edge
    tests pyproject.toml .github/workflows/test.yml ':!src/coga/resources/**'
  status: passed
  head: d7b10ad6d0318905b791dcf3024bd90345ce23ed
  base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
  detail: 'Exit 0: non-resource implementation, tests, project metadata and CI configuration
    match the full-suite-tested revision. Inspected the incoming diff: packaged changes are
    Markdown; other changes are knowledge and retired task records. Final-head packaging verification
    covers the changed resource surface.'
- command: git diff --check origin/main...HEAD
  status: passed
  head: d7b10ad6d0318905b791dcf3024bd90345ce23ed
  base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
  detail: No whitespace errors.
- command: 'PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/recurring-unblock-launch-peer-rem7qrxt/render_scan.py
    80 24

    PYTHONPATH=/home/n/Code/coga/src .venv/bin/python /tmp/recurring-unblock-launch-peer-rem7qrxt/render_scan.py
    120 40'
  status: passed
  head: d7b10ad6d0318905b791dcf3024bd90345ce23ed
  base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
  detail: Real PTYs at 80x24 and 120x40, stdin/stdout TTY-checked. Exercised watchdog retry,
    unfinished retry, open asks with unblock command, human pause and headless refusals. Complete
    colored console rows and matching plain run-record rows were emitted; long rows use normal
    terminal wrapping and no cursor-control loop.
- command: PYTHONPATH=/home/n/Code/coga/src:/home/n/Code/coga/tests .venv/bin/python /tmp/recurring-unblock-launch-peer-rem7qrxt/exercise_unblock_tty.py
  status: passed
  head: d7b10ad6d0318905b791dcf3024bd90345ce23ed
  base: 33cb4c613012491b2fed36d9ee1e6f6c45778c52
  detail: Real 80x24 PTY; entered the eu mirror at the live unblock prompt in an isolated Git-disabled
    fixture. Ask displayed, answer persisted, asks resolved, paused status and current step
    preserved. Repeated successfully after the latest rebase.
- command: coga validate --json
  status: not-run
  detail: No config schema, workflow definition or ticket-model schema changed; the full suite
    includes lifecycle behavior and packaged-twin verification.
- command: python3.11 -m pytest
  status: not-run
  detail: The available Python 3.11 interpreter has no pytest; verification used the repository
    Python 3.12.12 venv.
```

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `recurring-unblock-launch`
Recorded: 2026-10-26T21:13:21+00:00

    Branch 'coga/recurring-unblock-launch-9cca77' is not safe to publish. refs/heads/coga/recurring-unblock-launch-9cca77 does not contain latest origin/main. Rebase or merge before opening a PR, e.g. `git fetch origin main` then `git rebase origin/main`. Reconcile it and relaunch, or `coga block --task recurring-unblock-launch`.

## Recipe Failure

Recipe: `open-pr`
Exit: 2
Task: `recurring-unblock-launch`
Recorded: 2026-10-26T21:20:00+00:00

    [open-pr] origin/main advanced only through non-overlapping Coga task/log state; branch is safe to publish
    PR presentation: invalid YAML under ## PR: while parsing a block mapping
      in "<unicode string>", line 92, column 3:
        - command: .venv/bin/python -m pyt ... 
          ^
    expected <block end>, but found '<scalar>'
      in "<unicode string>", line 98, column 5:
            the function in the coga-dev spo ... 
            ^
