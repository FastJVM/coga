---
title: Stop one failing ticket.py from starving the rest of the sweep
status: in_progress
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
step: 3 (pr)
launch_generation: 8b615f5a-bf7d-44b5-b7d2-81e6f299c2b0
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

## Verified against run-log.md

Confirmed: 7 due, `tasks run: 3`, `skill-update` failed (exit 1), and the
four templates behind it appear nowhere in the outcomes or notes.

## Already landed vs. remaining

PR #777 (`6224faf0`, 2026-09-09, after the 2026-09-08 sweep) landed the bulk
of this ticket in `recurring_runner._launch_due_tasks`:

- The delegated `if delegated.exit_code`, the `except SystemExit` arm around
  `launch_cmd`, and the missing-period-lease refusal now record the failure,
  append to a `failures` list, and `continue`; the first failing code is
  returned after the loop with a `N of M due template(s) failed: ...` note.
- `tests/test_recurring.py::test_recurring_scan_returns_failed_script_exit_without_unwinding`
  now asserts continuation + exit 17, and
  `test_recurring_scan_names_every_failed_template_in_the_run_record` covers
  the record naming each failure.

**Remaining gap (ticket item 3):** three early exits still survive by design —
`return 2` when a period cannot be classified after reconciliation, and the
two `raise` paths for exit 75 (`git.RETRY_WITHOUT_SWEEP_EXIT_CODE`) and
signal exits ≥128 — and none of them tells the `RunRecord` which admitted due
tasks were never launched. `run_autofix` still runs from the caller's
`finally`, so the report is written, but it would read exactly like the
2026-09-08 one: fewer tasks run than due, no explanation.

## Plan

- Add `_record_abandoned_due(record, due, stopped_at, reason)` beside
  `_record_unlaunched_creates` in `src/coga/recurring_runner.py`; it appends
  one `scan_problems` entry per unlaunched due task (so the `problems:`
  header counts them, matching how created-but-never-launched periods are
  already reported) plus a single summary note.
- Call it from the three surviving early exits before returning/raising.
- Tests: extend `test_recurring_scan_stops_immediately_on_non_template_exits`
  to assert the record names the abandoned task, and add one for the
  classify-failure `return 2` path.

## Dev

pr: https://github.com/FastJVM/coga/pull/813
branch: sweep-abandoned-record
worktree: /home/n/Code/claude/coga-sweep-abandoned-record

## What changed (commit `e2aefc31` on `sweep-abandoned-record`)

- `src/coga/recurring_runner.py`: new `_record_abandoned_due(record, due,
  stopped_at, reason)` beside `_record_unlaunched_creates`. Called from the
  three surviving early exits in `_launch_due_tasks` — the classify-refusal
  `return 2`, the exit-75 `raise`, and the ≥128 signal `raise` — before they
  leave the loop. Each due task behind the stopping one becomes a
  `scan_problems` entry (`admitted as due but never launched: <reason>
  stopped the sweep at <slug>`), so the `problems:` header counts it, plus
  one sweep note `N of M due task(s) never launched after <slug>: ...`.
- Decision: kept all three early exits as-is. The ticket allows them for
  repo-unsafe states and PR #777 deliberately retained the classify `return
  2`; widening that to `continue` is out of scope here.
- Decision: `scan_problems` over `notes` alone, so the header cannot read as
  a clean sweep; mirrors how created-but-never-launched periods are reported.
- `tests/test_recurring.py`: `test_recurring_scan_stops_immediately_on_non_template_exits`
  now captures the run record and asserts `recurring/beta` is named with
  `problems: 1`; new `test_recurring_scan_names_due_tasks_abandoned_by_a_classify_refusal`
  covers the `return 2` path (`problems: 3`, both trailing tasks named).
- `coga/contexts/coga/recurring/SKILL.md` and its bundled twin under
  `src/coga/resources/templates/coga/bootstrap/contexts/coga/recurring/`:
  documented the third (classify) stop and the abandoned-task reporting.

Verification: `python -m pytest` (2496 passed before the context edit;
`tests/test_recurring.py` + `tests/test_packaging.py` re-run green after it).
Rebased on `origin/main`: already up to date. Not pushed; no PR.

## Self-QA

Both passes ran against `sweep-abandoned-record` and **returned**; nothing is
still in flight. Two QA commits on top of `e2aefc31`: `a3a7ca22`, `bb2d017f`.

- `/code-review` (Claude Code slash command, default effort, target
  `sweep-abandoned-record`; a first invocation without a target reviewed the
  primary checkout's empty diff and was discarded). Returned two findings,
  both confirmed by reading the code and both fixed:
  1. **Medium** — a signal / exit 75 escaping `_run_delegated_task` (or a
     `RecurringError` out of `_stop_if_unfinished_after_launch`) left the loop
     without naming the tasks behind it; the context's "never again abandons
     work silently" claim was false for every delegating template. Fixed by
     wrapping the loop in one `try/except BaseException` that calls
     `_record_abandoned_due` then re-raises — the single owner — and dropping
     the per-site calls. `git diff -w` shows the real change; the plain diff
     is mostly the loop re-indent.
  2. **Low** — on the classify `return 2`, `_record_unlaunched_creates` named
     every created-then-abandoned period a second time (`problems: 5` for 3
     due). Fixed first by dedup, then made moot (below).
- `/simplify` (4 review agents: reuse, simplification, efficiency, altitude).
  Efficiency: no findings. Applied: one `_sweep_stopping_exit(code)`
  classifier now decides both the re-raise and the record wording (the 75 /
  ≥128 ladder lived twice); `_record_abandoned_due` takes the loop's 1-based
  `i` (no `i - 1` / `+ 1` pair); tests reuse `_allow_interactive_recurring`
  and parametrize just the reason. **Altitude finding, applied — reverses
  the implement step's decision:** the classify `return 2` was a leftover,
  not a deliberate stop (PR #777's message lists the three early returns it
  fixed and never mentions it), and an unclassifiable period is one task's
  routing problem, exactly like the forced-launch refusal ten lines above.
  It now counts a refusal and `continue`s; the sweep still exits 2. That
  leaves an escaping exception as the only way the loop stops short, so the
  dedup from finding 2 was reverted, the "third stop" paragraph in both
  `recurring/SKILL.md` twins was replaced, and the classify test became
  `test_recurring_scan_continues_past_an_unclassifiable_period` (beta and
  gamma launch, `tasks run: 3`, `problems: 1`, no "never launched"). Reviewer:
  this is the one judgement call in the PR worth a look.
- Skipped: consolidating the ~40-line monkeypatch scaffold shared by ~10
  in-process sweep tests (pre-existing pattern; a follow-up across all of
  them is the only version with payoff); a `DueTask.slug` property for the
  `ref.id_slug if ref else template` fallback (pre-existing, four sites).
  One simplification suggestion was wrong (dropping `last_fire` etc. from a
  fake — `scan_lines_for_record` reads them) and is gone with that test.
- Noted, out of scope: `_record_unlaunched_creates` sits inside the `try` in
  `run_recurring_scan`, so on an escaping exception admission-skipped creates
  still go unnamed (pre-existing).
- No hand-swept surface: the change is record/stderr text and control flow,
  fully reachable by the suite.

Verification (worktree, `../coga/.venv/bin/python`): full `python -m pytest`
2499 passed after each QA commit; `tests/test_recurring.py` 353 passed;
twins byte-identical. `coga validate --json` exits 1 in the worktree and the
primary checkout alike from pre-existing repo-state warnings (no `user` in the
local toml, stuck tasks) — not from this change. `origin/main` moved 8
task-state-only commits (no `src`/`tests`) since the base; no rebase needed
before the PR step. Working tree clean.
