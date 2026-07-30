---
slug: ship-a-shared-recurring-reminder-engine-battery
title: Ship a shared recurring-reminder engine battery
status: canceled
owner: zach
human: zach
agent: claude
assignee: zach
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

## Orientation (2026-07-24, implement step)

### The golden oracle — the two patents sweeps
- `maintenance-fee-sweep`: `~/dev/patents/coga/tasks/repo/utility/maintenance-fee-sweep/maintenance_fee_sweep.py`
  - Auto-detect path. Windows `[grant+3y,+4y)`, `[grant+7y,+8y)`, `[grant+11y,+12y)`.
    Flag if `opens<=today<closes` UNLESS `patent_maintenance_paid == window_number`.
  - Currently ALWAYS posts (no `--notify` flag). Recorded sample run (2026-07-13):
    8 granted, 1 suppressed, 2 flagged.
- `candidate-sweep`: `~/dev/patents/coga/tasks/repo/candidate/candidate-sweep/candidate_sweep.py`
  - Time-window path. Single window `[filing+14mo, filing+15mo)`, fires once then ages out.
  - Has `--notify` gate. Four evaluate buckets: flags / needs_filing / unreadable / granted-anomaly.
  - Recorded sample run (2026-07-21): 4 candidates, 3 needs-a-filing-date, 0 in-window.

### Genuinely-shared code across both (the engine's ~80%)
`_read_frontmatter` (byte-identical), `default_tasks_dir` (byte-identical),
`_parse_date`/`_parse_granted` (identical), `add_years`/`add_months` (date-add+clamp),
the `opens<=today<closes` kernel, the `coga slack --important` notify plumbing
(`COGA_TASK_SLUG` fallback + failure count), and the argparse `main()` harness
(`--today`/`--tasks-dir`/`--notify`, exit codes).
Unique 20% per sweep: record dataclass + selector, window spec, the satisfied rule,
the evaluate bucketing, and the report/message format strings.

### Where the engine ships — settled by precedent
Reusable logic → a `src/coga/` module imported as `coga.<name>`; a thin bundled-skill
`run.py` imports it. Exact precedent: `coga.branchsweep`/`coga.autoclose` +
`bootstrap/skills/coga/{branch-sweep,autoclose}/sweep/run.py`. So the engine =
`src/coga/reminders.py` (import `coga.reminders`), plus a docs-only bootstrap skill
`bootstrap/skills/coga/reminders/SKILL.md` carrying the migration note. Downstream repos
have `coga` pip-installed, so `import coga.reminders` works with nothing materialized.

### Byte-for-byte parity — key finding
The two report formats are entirely different, so the engine CANNOT own report
formatting. Parity ("same flags, windows, and printed output for the same `--today`")
= identical STDOUT. Plan: vendor the two original scripts + a fixture task-dir into
coga's tests; assert `original.main(argv).stdout == retrofit.main(argv).stdout` across a
matrix of `--today`. Fixtures are hand-crafted fake tickets (not live patents data — see
codebase gotcha "tests must not pin to live dogfooded state").

## Dev

branch: reminder-engine
worktree: /private/tmp/coga-reminder-peer-review.9N76Li/repo
pr: https://github.com/FastJVM/coga/pull/651

Decision: Option A — thin engine (shared primitives + notify + ack helpers + a
`run()` CLI harness driving a caller-supplied `sweep()`). Defer the single-reminder
`run(window=,satisfied=,summarize=)` sugar until admin's first ack reminder shapes it.
Ack helpers ship; the two parity sweeps don't use ack (DoD: ack proven later).

### open-pr recovery note (2026-07-24)
The peer-review evaluator ran sandboxed and made the linked worktree read-only,
so its fixes landed in an independent temp clone (`worktree:` above) as commit
`63e84bef` (implement + `peer-review: apply reminder engine findings`, rebased
onto current `origin/main`, 2 ahead / 0 behind). This repo's *local*
`reminder-engine` (`8c6f225b`) stayed stale (implement-only, old base) and is
NOT what shipped. `coga open-pr` couldn't run because the primary checkout is on
`v2/sequence-op-webhook-tickets`, not `main`. With Zach's approval, recovered
manually: verified the temp-clone branch clean/fresh/ahead with a sane reminders-only
diff, pushed it to `origin/reminder-engine`, and opened PR #651 by hand (same
title + `## PR` body `coga open-pr` would have used). The good work is now durable
on GitHub. Follow-up hygiene: the durable worktree `/Users/zach2179/dev/coga-reminder-engine`
still has the stale local `reminder-engine`; reconcile it to `origin/reminder-engine`
when convenient (a `git reset --hard` was declined by the safety classifier during recovery).

## Implemented (2026-07-24) — committed on `reminder-engine`, ready for self-review

Approach: Option A (thin engine), decided with Zach. What landed:

1. `src/coga/reminders.py` — the engine (`coga.reminders`): `add_years`,
   `add_months`, `parse_date`, `read_frontmatter`, `default_tasks_dir`,
   `in_window(today, opens, closes, *, past_deadline_fires=False)`, ack helpers
   (`read_ack` / `record_ack`), `notify(task, msg, *, important=True)`, and the
   `run(sweep, *, task_slug, ...)` CLI harness + `SweepResult`. Stdlib-only.
2. `bootstrap/skills/coga/reminders/SKILL.md` — docs-only battery: the adoption note.
   Packaged-only (not dogfooded by coga, so no live `coga/skills/` mirror); added to
   the `test_packaging.py` allowlist so the wheel-build test proves it ships.
3. `tests/fixtures/reminders/` — `golden/` (the two originals, vendored verbatim,
   byte-identical to the patents sources), `retrofit/` (engine-backed), and a
   fake-ticket `tasks/` dir exercising every path.
4. `tests/test_reminders.py` — 42 tests: engine unit tests (incl. `past_deadline_fires`
   and ack roundtrip) + stdout parity `golden.main == retrofit.main` across a `--today`
   matrix + two frozen recorded-sample-run snapshots.

Tests: `tests/test_reminders.py` 42 passed; packaging (wheel build) + validate/skill
suites green. Full suite: 1543 passed, 1 skipped, **1 pre-existing failure unrelated
to this change** — `test_launch_script.py::test_script_launch_preserves_cancellation_made_by_script`
fails on macOS because its fixture uses GNU-only `sed -i` (`sed: invalid command code v`);
not in any path this change touches. Branch is 1 ahead / 0 behind `origin/main`, tree clean.

Deferred (out of scope, per DoD): the single-reminder `run(window=,satisfied=,summarize=)`
sugar and the `--ack` harness flag — shaped later by admin's first ack reminder. Live
patents/admin migrations are downstream follow-ups.

## Third-sweep validation — admin's Brex missing-receipts (2026-07-24, at Zach's ask)

Proved the engine serves admin's world too, not just patents. Wrote a scratch
engine-backed version of admin's `coga/skills/brex/api/missing_receipts.py`
(scratchpad only — NOT committed; it needs a live Brex token + the admin repo, so it
can't live in coga's suite) that reuses admin's logic verbatim and only swaps the
harness for `coga.reminders.run`. Shape: monthly window (prior calendar month),
`satisfied()` = the Brex API query returns zero over-$40 card expenses missing a
receipt — an EXTERNAL-query satisfied, the opposite of patents' ticket-field checks.

- Read-only run (June 2026): engine drove the window + external `satisfied()` and
  rendered admin's own table — 5 missing receipts found.
- `--notify` run: engine posted ONE coga-important summary end-to-end; `coga slack
  --important` returned `posted` (webhook 200), engine exit 0. Real post landed.

Design note surfaced (not blocking): the harness requires a valid `--tasks-dir` even
for an external-query reminder that reads no tickets (brex passes a throwaway dir).
Left as-is for consistency with the deferral discipline — add a `needs_tasks_dir=False`
option when admin's first reminder actually adopts the engine, rather than speculate now.

Second admin sweep — Brex missing-GL (fiscal-year window, external `satisfied()` =
no current-year CARD charge missing a Debit GL account). Reused admin's `missing_gl.py`
verbatim. Live read-only: 1104 CARD records, 133 in scope (FY2026), 11 missing a GL
account. `--notify` posted admin's own Slack message to coga-important; `coga slack
--important` returned `posted` (webhook 200), engine exit 0.

So the engine is validated across FOUR distinct shapes: patents auto-detect (ticket
field), patents time-window, admin monthly external-query (receipts), admin fiscal-year
external-query (missing-GL). Two real coga-important posts landed during testing (both
authorized by Zach).

Recurring coverage (answer to Zach): `check-receipts-in-brex` is a LIVE monthly template
(`schedule: "0 9 1 * *"`), so the receipts items are caught by real `coga recurring`.
`brex-missing-gl` is NOT scheduled (still `draft` in admin's `recurring-buildout/`), so
those 11 missing-GL charges are not otherwise auto-surfaced — which is why the coga-important
post for it was worth sending. Both are admin-repo concerns, out of scope for this ticket.
None of the Brex scratch scripts are committed (live-cred + admin-repo deps; real recurring
covers receipts).

## Peer review (2026-07-24)

- Feature worktree is clean on `reminder-engine`; the branch is 1 commit ahead
  and 3 commits behind `origin/main`.
- `codex review --base main` could not start in the managed launch:
  `failed to initialize in-process app-server client: Operation not permitted`.
  Zach authorized a fresh cold-review subagent as the equivalent independent
  review path.
- Cold review verification: golden scripts are byte-identical to patents;
  focused reminder/packaging tests 46 passed; full suite 1543 passed, 1 skipped,
  with only the known macOS GNU-`sed -i` fixture failure (also on `main`).
- Finding 1 (must-fix): `read_ack` / `record_ack` search the entire ticket,
  rather than only the region below `<!-- coga:blackboard -->`; body prose can
  be mistaken for state or overwritten.
- Finding 2 (design decision): `run()` accepts an already-evaluated sweep and
  does not itself compose window + `satisfied()`, the auto-detect→ack fallback,
  or `--ack`. This conflicts with the task's broad contract but matches Zach's
  recorded Option A decision to defer single-reminder sugar and `--ack`.
- Finding 3 (must-fix): the tests label synthetic snapshots as the recorded
  patents sample runs; the real recorded outputs were not vendored/proven.
- Asked Zach whether to preserve Option A and fix findings 1/3, or expand the
  API now to address finding 2.
- Zach approved preserving Option A: fix ack blackboard safety and recorded-run
  fixtures; clarify that higher-level `window=` / `satisfied=` / `--ack`
  orchestration remains deferred until the first ack-based admin adoption.
- The recorded linked worktree was read-only in this launch, so review continued
  in the supported independent-clone fallback now recorded under `## Dev`.
- Fixed ack helpers to use Coga's fence-aware blackboard reader/writer, with a
  regression proving ticket body examples are ignored and preserved.
- Replaced the mislabeled synthetic snapshots with frozen inputs and outputs for
  the patents production runs: maintenance 2026-07-13 and candidate 2026-07-21.
- Documented the approved Option A boundary in the bundled adoption guide.
- Committed as `peer-review: apply reminder engine findings`, fetched
  `origin/main`, and rebased cleanly. Branch is clean and 2 commits ahead.
- Post-rebase verification: focused reminder/packaging suite 46 passed; full
  suite 1543 passed, 1 skipped, with only the known macOS GNU-`sed -i` fixture
  failure that reproduces on `main`.

## PR

Ship a stdlib-only `coga.reminders` battery with shared date/window primitives,
fence-aware ack state, notification plumbing, and a print-first CLI harness.
Bundle the adoption guide plus two engine-backed patents retrofits, proving
byte-for-byte parity against the original scripts and their frozen production
runs. Higher-level `window=` / `satisfied=` / `--ack` orchestration remains
deliberately deferred until the first ack-based admin adoption supplies its
concrete period shape.

Tests: `python -m pytest` — 1543 passed, 1 skipped; one pre-existing macOS GNU-`sed -i` fixture failure reproduces on `main`.
