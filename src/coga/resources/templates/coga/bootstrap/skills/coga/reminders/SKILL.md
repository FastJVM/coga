---
name: coga/reminders
description: How a recurring reminder or sweep adopts the shared reminder engine (coga.reminders) — the fire = in_window(today) AND NOT satisfied() battery that owns the shared periodic-sweep machinery so each reminder writes only its window spec, satisfied rule, and report.
---

# Shared reminder engine

`coga.reminders` is the shared engine for any recurring reminder or sweep. Every
one repeats the same shape:

```
fire = in_window(today) AND NOT satisfied()
```

The engine owns the shared machinery; each reminder supplies its unique 20%.
Import it from the installed package — nothing is materialized into a repo:

```python
from coga import reminders
```

Stdlib-only and dependency-free (Python >= 3.11). Implementation lives in
`src/coga/reminders.py`.

## What the engine owns

- **Frontmatter reading** — `reminders.read_frontmatter(path)` returns a ticket's
  top-level scalar frontmatter as a `dict[str, str]` (nested/indented keys and
  the workflow block are ignored).
- **Tasks directory** — `reminders.default_tasks_dir()` returns
  `$COGA_COGA_OS_ROOT/tasks` (set on every launch), or `None` when unset so a
  standalone run must pass `--tasks-dir`.
- **Date-window math** — `add_years`, `add_months` (both clamp to the target
  month/day), `parse_date` (blank/unparseable → `None`).
- **The in-window kernel** — `in_window(today, opens, closes, *,
  past_deadline_fires=False)`. Default window is `[opens, closes)`:
  open-inclusive, close-exclusive (a monthly period or an annual window that
  ages out). With `past_deadline_fires=True` it has no upper bound — a money
  obligation keeps firing after its deadline until `satisfied()`, so a miss is
  never silent.
- **Ack helper** — `read_ack(blackboard)` / `record_ack(blackboard, period)`
  read and write `Acked: <period>` in the reminder's own blackboard, coga's
  sanctioned cross-run state home. Ack is the universal `satisfied()` fallback,
  not the only path: a caller that can auto-detect satisfaction (query a source
  and return `True` when the obligation is provably met) does not need it.
- **Notify** — `notify(task, message, *, important=False)` shells to `coga slack`.
  It posts to the normal channel by default; pass `important=True` to route to
  coga-important. Reserve important for a hard-deadline or money obligation — a
  routine reminder does not belong there.
- **The CLI harness** — `run(sweep, *, task_slug, description="",
  important=True, argv=None)`. It parses `--today` / `--tasks-dir` / `--notify`,
  resolves the date and tasks dir, calls your `sweep`, prints its report, and —
  only under `--notify` — posts each alert (a bare run is print-only). It returns
  0 when handled, non-zero on failure so a script-mode launch posts 💥 and leaves
  the task inspectable.

This first battery deliberately stops at the shared primitives and sweep
harness. The ack shape is now concrete — the monthly Xero reconciliation sweep
(below) pins it: the period is the *prior* calendar month as `YYYY-MM`, and a
reminder is satisfied once its blackboard carries `Acked: <period>`. A
higher-level single-reminder API that folds `window=` / `satisfied=` / a uniform
`--ack` into `run()` can build on that shape but is not shipped yet.

## What each reminder supplies

Write one `sweep(today, tasks_dir) -> reminders.SweepResult` that:

1. loads its records with `reminders.read_frontmatter`,
2. applies its **window spec** with `add_years` / `add_months` +
   `in_window`, and its **`satisfied()` rule** (auto-detect first — a source
   query — then the recorded ack as the fallback),
3. returns a `SweepResult(report=<stdout>, alerts=[<one message per fire>])`.

Then `main()` is one line:

```python
def main(argv=None):
    return reminders.run(_sweep, task_slug="repo/utility/maintenance-fee-sweep",
                         description="…", argv=argv)
```

The engine posts each `alert` only under `--notify`, to the normal `coga slack`
channel. Pass `important=True` to `run` to route alerts to coga-important —
reserve it for a hard-deadline or money obligation (e.g. a maintenance fee that
lapses), so the important channel stays rare.

## Worked examples

Two diverse patents sweeps are retrofitted onto the engine under
`tests/fixtures/reminders/retrofit/`, asserted byte-for-byte against their
standalone originals in `tests/fixtures/reminders/golden/` (see
`tests/test_reminders.py`):

- `maintenance_fee_sweep.py` — the **auto-detect** path. Three grant-anchored
  windows; `satisfied()` is `patent_maintenance_paid == window_number`.
- `candidate_sweep.py` — the **time-window** path. One `[filing+14mo,
  filing+15mo)` window that fires once then ages out.

A third example is engine-native — the engine is its first implementation, so
there is no standalone original to match and it is verified behaviourally:

- `admin/xero_reconcile_sweep.py` — the **ack** path. A monthly reminder whose
  `satisfied()` is `read_ack(ticket) == period_for(today)`, with the period the
  prior calendar month (`YYYY-MM`). A missed month goes quiet at rollover; the
  ack round-trip test (record then re-run) is what locks the shape.

## Adopting it in a repo

A live per-repo migration (patents, admin) rewrites the repo's sweep to import
`coga.reminders`, keeping its own record dataclass, selector, window spec,
`satisfied()`, and report/message formatting, and deleting the machinery the
engine now owns. `coga` is pip-installed in the repo, so `from coga import
reminders` resolves with nothing copied. Assert parity against the sweep's prior
output before landing the change.
