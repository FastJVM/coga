---
title: Retry the shared recurring-reminder engine at a smaller boundary
status: in_progress
owner: zach
agent: claude
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
    skills: []
    assignee: owner
step: 3 (open-pr)
---

## Description

Retry the shared recurring-reminder engine, owning less than the first attempt
did. That attempt shipped `src/coga/reminders.py` plus a bundled `coga/reminders`
skill, reached PR #652, and was closed unmerged on 2026-07-27. Keep the fixtures
and the sweep-shape work, which is the part that paid off, and re-cut the
boundary before writing anything.

## Context

Three things to do differently, from Zach's read of the first attempt:

- Most of the work was an attempt to add more commands to Coga, and Coga is
  already inundated with commands.
- It lived in both a SKILL and a `.py`; it should have been one or the other,
  decided up front.
- The engine's boundary was pushed too far, and it ended up owning things that
  belong in the individual scripts.

What was worth keeping: the fixtures, and the real headway on which shapes of
`coga recurring` work a reminder engine has to cover — a period ack, a date
high-water ack, a date window, and a live query with no window at all.

The first attempt's code is not lost. PR #652 is closed but retains the full
diff, and the `reminder-engine` branch can be restored from it; the last two
commits are `2c72048d` (defect fixes) and `18e56c0d` (the review write-up). The
prior ticket was `ship-a-shared-recurring-reminder-engine-battery`.

<!-- coga:blackboard -->

## Dev

pr: https://github.com/FastJVM/coga/pull/853
branch: reminders-harness
worktree: /home/n/Code/coga-reminders-harness

## Implementation (v2, 2026-09-20)

Zach chose the `.py`-only cut in session. One commit on the branch, rebased on
`origin/main`, full suite green (2723 passed).

### The boundary

- `src/coga/reminders.py` is `run()` + `SweepResult` and nothing else (~150
  lines, most of it docstring): parse `--today` / `--tasks-dir` / `--dry-run`,
  resolve the tasks dir from `$COGA_COGA_OS_ROOT`, print the report, post each
  alert via `python -m coga.cli slack` (normal channel; `important=True`
  opt-in). No skill, no CLI command. The docstring names the four shapes and
  points at the fixtures as the worked examples.
- **Posting is the default; `--dry-run` suppresses.** Inverts the first
  attempt's opt-in `--notify`. Reason: a `ticket.py` under `coga recurring`
  gets no operands, so an opt-in flag can never be reached there — that was
  the "retrofit silently turned off Slack" defect, now fixed once at the
  harness instead of per launch command. Golden parity still holds: the
  goldens posted whenever something fired, and
  `test_maintenance_retrofit_posts_on_a_bare_run_like_the_golden` pins it.
- Dropped and where each went: `add_years` / `add_months` / `parse_date` →
  each sweep owns its date math; `in_window` → inline comparison (the Xero
  call was the tautology and is deleted outright); `read_frontmatter` → the
  patents sweeps keep their own string-typed reader (core's `Ticket.parse` is
  YAML-typed — dates become `date`, ints become `int` — and raises on a
  fence-less file, both of which break byte parity with the goldens);
  `read_ack` / `record_ack` → the ack is a blackboard `key: value` line read
  with `period_state.parse_keys` over `taskfile.read_blackboard`, and there is
  no writer because a human edits the ticket; `notify`, `default_tasks_dir` →
  private to `run()`.
- Completion (`coga bump` after `run()` returns 0) stays the script's job,
  matching every shipped `ticket.py`; the module docstring says so.

### Fixtures

- All five sweeps and the recorded data kept from PR #652, rewritten to own
  their helpers. Parity tests unchanged in shape; ack tests write the ack the
  way a human does (`_write_ack` edits the blackboard line).
- The three unresolved fixture items are resolved: both Brex sweeps read
  amounts the same way (`float | None`) and surface an unreadable amount as
  `USD ?` instead of receipts skipping it and GL showing `0.00`;
  `is_missing_receipt`'s docstring now describes only the attachment check;
  `recorded/brex/README.md` labels `receipts-missing.json` as a
  reconstruction (every `posted_at` is a synthetic `T12:00:00.000Z`; the GL
  and record-shape files are real captures).
- `coga/codebase` context (live + packaged twin, still byte-identical) gained a
  `reminders.py` entry under Source layout.

### Microkernel note for the reviewer

The only in-repo consumers of `coga.reminders` are the test fixtures; the real
consumers are the patents and admin sweeps that migrate downstream. That is
the tradeoff Zach accepted in session. The ~82 lines shared between the two
Brex sweeps stay duplicated on purpose — both live in the admin repo, so a
sibling helper there is that repo's call, not a reason to widen the harness.

### Follow-ups (not in this PR)

- Downstream migrations: patents `maintenance-fee-sweep` and `candidate-sweep`,
  admin Xero / Brex sweeps. Each must end its `ticket.py` with `coga bump` and
  must drop any `--notify` from launch commands (argparse now rejects it;
  use `--dry-run` for a quiet run).
- The Xero changeover fires once (old script acks the current month, this
  acks the prior month) — documented in the sweep's docstring.


## Peer review

2026-09-20: `codex review --base main` **returned** (exit 0), reporting no
actionable regressions in the harness, sweep examples, or tests. No code fixes
were needed. Review log for this session: `/tmp/reminders-peer-review.log`.
The accepted fixture-only consumer boundary above remains unchanged; downstream
migrations are still follow-up work.

Ran `git fetch origin main && git rebase FETCH_HEAD` in the feature worktree;
the rebase completed without conflicts. Feature commit is now `3294d129`, one
commit ahead of fetched `origin/main`; the worktree is clean.

The review's test attempt and the ambient `python -m pytest` lacked test
dependencies. Full verification used the existing worktree virtualenv:
`PYTHONPATH=/home/n/Code/coga-reminders-harness/src .venv/bin/python -m pytest`.
Confirmed that imports resolve to this feature worktree: **2723 passed** in
173.16s (exit 0). Two warnings were sandbox-denied pytest cache writes, not test
failures. No additional implementation commit was necessary.

Terminal checks: ran the candidate fixture at 80x24 and maintenance fixture at
120x40 in a real PTY, both with `--today 2026-07-13`, their respective
`tests/fixtures/reminders/recorded/{candidate,maintenance}` tasks directory, and
`--dry-run`. Reports showed three missing filing dates and two maintenance
windows respectively, followed by the correct dry-run suppression notices.
Output is plain scrolling text, with no cursor positioning or interactive UI.
No live Slack posts were sent; Slack rendering itself is unchanged and the
existing CLI owns delivery. `git diff --check` passed.

## PR

Recurring sweeps repeat date/task-directory argument handling, reporting, and
Slack delivery. Add a Python-only `coga.reminders.run()` harness and
`SweepResult` for that shared tail. Posting is the default so operand-free
`ticket.py` launches send alerts; `--dry-run` suppresses delivery. Each sweep
retains its date math, record loading, acknowledgement rules, and wording.

Keep five worked sweep fixtures spanning date windows, period acknowledgements,
date high-water acknowledgements, and live queries. Patent retrofit tests pin
golden stdout and default posting; Brex fixtures expose unreadable amounts and
document reconstructed data. Update the live and packaged codebase contexts
together. Production consumers migrate downstream in follow-up work.

Test plan: `PYTHONPATH=/home/n/Code/coga-reminders-harness/src .venv/bin/python -m pytest` — 2723 passed; fixture dry runs in 80x24/120x40 PTYs; `git diff --check`.

## Production notes

Carried over from the first attempt so a v2 launch starts oriented. Kept
deliberately short — this is composed into every launch prompt.

### What was built

- `src/coga/reminders.py`: date math, an in-window check, a frontmatter reader,
  ack read/write, `coga slack` notify plumbing, and a `--today` / `--tasks-dir`
  / `--notify` CLI harness.
- A bundled `coga/reminders` skill documenting the same contract.
- Five sweeps as fixtures: two patents retrofits with byte-for-byte parity
  against their standalone originals, and three admin sweeps covering Xero
  reconcile and the two Brex query shapes.

### Independent review, 2026-07-26

Three subagents reviewed the branch on separate lenses. The measured findings:

- Real duplication removed was about 55 code lines, once, against a library
  costing 110 code lines plus a 159-line skill.
- The extraction had two source scripts, not several, and both were patents
  sweeps over ticket frontmatter with a grant-anchored window.
- Two of the three sweeps written afterward use no date window at all, and the
  third's `in_window` call is a provable tautology.
- The third consumer forced an interface change, which is the signature of an
  abstraction validated on two samples.
- About 82 lines are genuinely duplicated between the two Brex sweeps and sit
  outside the library.
- No shipped code imported `coga.reminders`; all five consumers were fixtures.

Consumer counts, grep-verified across the five sweeps:

| Symbol | Sweeps | Verdict |
|---|---|---|
| `run` | 5/5 | earned |
| `SweepResult` | 5/5 | earned |
| `parse_date` | 4/5 | earned |
| `read_ack` | 3/5 | earned, duplicates `period_state.parse_keys` |
| `in_window` | 3/5 | one caller is a tautology |
| `read_frontmatter` | 2/5 | second frontmatter parser in a package that has one |
| `add_months` | 2/5 | earned |
| `add_years` | 1/5 | redundant with `add_months(d, 12*y)` |
| `default_tasks_dir` | 0/5 | internal to `run()` |
| `notify` | 0/5 | internal to `run()` |
| `record_ack` | 0/5 | no production writer existed |
| `in_window(past_deadline_fires=True)` | 0/5 | unused by the one obligation it was written for |

### Defects found and fixed on the dead branch

- `record_ack` destroyed the blackboard fence on a ticket whose file ended at
  the fence, leaving zero fences and breaking every blackboard reader in coga.
- `read_ack` raised `TaskFileError` on a fence-less ticket while promising
  `None`, so a hand-authored reminder crashed the sweep.
- Retrofitting a sweep silently turned off Slack, because the engine gated
  posting on `--notify` and the old launch command could not already carry it.

### Start here next time

- `run()` plus `SweepResult` was the only cut with all five consumers; start
  from that and add nothing until a third real consumer asks for it.
- The Brex high-water ack is the duplication actually worth sharing and was
  never in the library.
- Any blackboard writer must keep the fence on its own line, because the fence
  is matched as a whole line and an appended byte silently unmakes it.
- Any retrofit that introduces a print-only default must update the sweep's
  launch command in the same change.
- Unresolved: the two Brex sweeps disagree on `record_amount` null-handling,
  `is_missing_receipt` is not the predicate its docstring describes, and
  `receipts-missing.json` is labelled a captured run but is not.
