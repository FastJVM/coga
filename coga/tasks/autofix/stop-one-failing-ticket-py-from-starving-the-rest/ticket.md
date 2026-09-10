---
title: Stop one failing ticket.py from starving the rest of the sweep
status: active
owner: nicktoper
agent: claude
workflow:
  name: code/with-self-review
  steps:
  - name: implement
    skills:
    - code/implement
    assignee: agent
    requires: branch
  - name: self-qa
    skills:
    - code/self-qa
    assignee: agent
  - name: pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: review
    skills:
    - code/address-pr-comments
    assignee: owner
step: 1 (implement)
---

## Description

The 2026-09-08 bare sweep scanned 7 templates, found all 7 due, announced
`launching 7 due task(s) sequentially` — and then ran only 3. After
`recurring/skill-update` exited 1, the sweep returned that exit code and the
four due tasks behind it (`autoclose-merged`, `digest`, `blocker-reminders`,
`dream`) never launched and were never mentioned in the report.

## Evidence

- Scan lists 7 due templates; header says `tasks run: 3`, `problems: 1`.
- The only sweep note is `launching 7 due task(s) sequentially`. Nothing
  records that four admitted tasks were abandoned, so the report reads as if
  the sweep completed with a single failure.
- Launch order matches `_sweep_order` in `src/coga/recurring.py:400`
  (cleanup/Dream last, then most-overdue first): branch-sweep (Mon 07:00),
  resolve-conflicts (Mon 08:00), skill-update (Mon 09:00), then
  autoclose-merged (Tue 08:00), digest (Tue 09:00), blocker-reminders
  (Tue 10:00), dream last. The three that ran are exactly the prefix before
  the failure; the four that did not are exactly the suffix after it.
- The trigger was not a crash. `coga/tasks/recurring/skill-update/ticket.md`
  documents the non-zero exit as a deliberate visibility signal: "A week with
  only follow-up statuses is intentionally loud: after writing the
  `## Skill Update` report, `ticket.py` exits non-zero so this period task
  remains visible until a human resolves or parks it." The follow-up here was
  one routine URL-skill divergence (`clarity`: `conflict`). A single
  hand-resolvable skill conflict cost the repo a week of four unrelated
  recurring jobs.

## Where it lives

`_launch_due_tasks` in `src/coga/recurring_runner.py`, the `except SystemExit`
arm around the `launch_cmd(...)` call (~line 1862): it records the failed
outcome and then `return code`, exiting the per-task loop. The delegated-task
path a few lines above does the same via `if delegated.exit_code: return
delegated.exit_code`. The comment justifies this as preserving where "the old
recipe dispatch stopped", and
`tests/test_recurring.py::test_recurring_scan_returns_failed_script_exit_without_unwinding`
pins it — that test asserts the return-instead-of-unwind, and currently also
locks in the starvation of the task behind the failure.

## What a fix has to do

- Keep the sweep going after a task's deterministic phase exits non-zero:
  record the failure in the `RunRecord`, continue to the next due task, and
  return the first (or a summarizing) non-zero code once the loop finishes, so
  the command still reaches its exit-boundary git sync and still reports
  failure to its caller.
- Keep the failed period unfinished/visible exactly as today — the fix is
  about the tasks behind it, not about hiding the failure.
- If any early return survives (a genuinely repo-unsafe state, e.g. the
  refusal paths that return 2), the run record must say which due tasks were
  admitted but never launched, so the sweep report can never again show
  `tasks run: 3` out of 7 due with no explanation.
- Update the pinning test to assert continuation plus non-zero exit, and add
  coverage that the abandoned/failed set is reflected in the record the autofix
  analyst sees.

---

Written by the `coga recurring` autofix loop from the sweep this
ticket's `run-log.md` records. The finding is an agent's
reading of that run, not a verified diagnosis: confirm it against
`run-log.md` before changing anything, and close the ticket
through the workflow's already-satisfied path if the problem was
transient or already fixed.

## Context

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
