---
slug: v2/ship-a-shared-recurring-reminder-engine-battery
title: Retry the shared recurring-reminder engine at a smaller boundary
status: draft
owner: zach
human: zach
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
    skills: []
    assignee: owner
secrets: null
script: null
step: 1 (implement)
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
