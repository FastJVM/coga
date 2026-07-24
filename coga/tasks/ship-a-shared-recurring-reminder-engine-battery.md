---
slug: ship-a-shared-recurring-reminder-engine-battery
title: Ship a shared recurring-reminder engine battery
status: active
owner: zach
human: zach
agent: claude
assignee: claude
contexts:
- coga/period-task
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

Ship a shared engine, bundled as a coga battery (a package-backed bootstrap
skill), for the logic every recurring reminder and sweep repeats:

```
fire = in_window(today) AND NOT satisfied()
```

Admin and patents each hand-roll this periodic-sweep logic in every script. The
engine owns the shared ~80%; each reminder supplies only its unique 20% — a
window spec and a `satisfied()` callable. Downstream repos get it without
copying code.

## Context

### The engine owns the shared 80%

- Window evaluation: whether `today` is in the reminder's window — a monthly
  period, or an annual window opening N days before a deadline.
- Past-deadline firing: money obligations keep firing after the deadline until
  satisfied, so a miss is never silent.
- Ack helper: reads and writes `Acked: <period>` in the reminder's own
  blackboard, coga's sanctioned cross-run state home; a uniform `--ack` records
  it, ideally with a `coga recurring ack <name>` wrapper.
- Notify: the engine owns the notify plumbing, gated behind `--notify` so bare
  runs are print-only, and defaults to `coga slack --important` since a firing
  reminder is unfinished work a human must act on.
- Each reminder can override the level — down to a normal `coga slack`, or its
  own notify — when its fire is informational rather than actionable.
- CLI harness: `--notify`, `--ack`, `--today <date>`, plus test overrides such
  as `--tasks-dir`; exit 0 when handled, nonzero on failure so script-mode
  posts 💥 and leaves the task inspectable.

### Each reminder supplies the unique 20%

- Its window spec.
- A `satisfied()` callable returning bool, resolved by a priority chain:
  auto-detect first — query a source and return True when the obligation is
  provably met (patents `patent_maintenance_paid == N`; admin brex `count == 0`
  or stripe no-drift) — then the recorded `Acked: <period>` as the universal
  fallback.

Illustrative shape, to be refined in the build:

```python
import remlib
def satisfied():
    return brex_missing_receipt_count() == 0
remlib.run(window="monthly", satisfied=satisfied, summarize=...)
```

### Why now

- Both admin and patents already repeat this sweep in every script; a second
  customer with the same code is the signal to factor it out.
- It becomes a battery two-plus repos depend on, so the surface must be designed
  deliberately and stay stable.
- It must serve both worlds without bias: patents' `satisfied()` reads a
  patent-ticket field, admin's is a brex/xero query or an ack. Ack is one
  helper, not the only path — callers supply their own detection.

### Constraints

- Stdlib-only, dependency-free, Python >= 3.11, matching existing coga scripts.
- Ships as a package-backed bootstrap skill, resolved from the installed package
  like every other core battery; nothing is materialized into a repo (see
  `coga/architecture`).

### Definition of done

- Retrofit two existing, already-done patents sweeps onto the engine and assert
  byte-for-byte parity with their current output; the sweeps and their recorded
  sample runs are the golden oracle, vendored into coga's tests as fixtures.
- Use two diverse sweeps — `maintenance-fee-sweep` (auto-detect via
  `patent_maintenance_paid == N`) and `candidate-sweep` (time-window) — so both
  the window and auto-detect paths are exercised. Parity means same flags,
  windows, and printed output for the same `--today`.
- The ack path is proven later, when admin's first ack-based reminder adopts the
  engine.
- Ships as one PR against coga; nothing merges until parity holds and review
  passes.

### Scope

- In: the engine, its own test suite, and a short "how a reminder/sweep adopts
  this" migration note.
- Out: editing the live patents or admin repos. This PR only vendors the two
  patents sweeps as parity fixtures; the real per-repo migrations are downstream
  follow-ups.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.
