# fix-recurring-templates-not-instantiated

## Dev

- branch: codex/validate-recurring-cron
- worktree: /tmp/relay-validate-recurring-cron
- pr: https://github.com/FastJVM/relay/pull/381

### open-pr (2026-06-17)
- Pushed branch and opened PR #381 (base `main`). `gh pr checks 381` → "no
  checks reported on the branch" — this repo has no CI configured, so green/red
  is N/A; correctness rests on the local suite (756 passed, 1 skipped).

## Implementation (2026-06-17)

- Added load-time cron validation in `Template.load`, catching `CroniterError`
  after probing `croniter(schedule, base).get_prev(datetime)`. Malformed
  schedules now become `RecurringError`, so scans/listing report per-template
  errors instead of letting raw croniter exceptions kill the sweep.
- Added regressions for malformed schedules, missing `ticket.md` template
  directories, and a bare recurring sweep that still launches other due
  templates after skipping a malformed one.
- Verification:
  - `PYTHONPATH=/tmp/relay-validate-recurring-cron/src python -m pytest tests/test_recurring.py -q` → 71 passed
  - `PYTHONPATH=/tmp/relay-validate-recurring-cron/src python -m pytest -q` → 755 passed, 1 skipped

## Verification findings (2026-06-17, bootstrap session)

Ran the v1 cron verification gate against the create path. PR #357's
restructure is sound; cron path is mostly proven. One real gap.

### Covered — proven by existing tests, no work needed
- No-TTY sweep instantiates **and** launches: `test_bare_recurring_scans_and_launches_due`,
  `test_bare_recurring_skips_interactive_without_tty_and_continues` (script-mode
  launches under no TTY; interactive templates are skipped, not crashed).
- `_`-prefixed inert dirs: `test_scan_due_skips_underscore_template`.
- Same-period dedup via `last_serviced_period`: `test_scan_due_idempotent`,
  `test_scan_due_recognizes_blackboard_high_water`,
  `test_scan_due_does_not_recreate_after_period_task_deleted`.
- Missing-frontmatter template: `test_scan_due_skips_bad_template` (handled,
  but this is *missing frontmatter*, not a *missing ticket.md* — see gap #2).

### Gap (the v1 blocker) — malformed schedule wedges the whole sweep
- `scan_due` calls `_last_firing(template.schedule, now)` at `recurring.py:242`,
  **outside** the `try/except RecurringError` (starts line 271).
- `croniter('not a cron', ...)` raises `CroniterBadCronError` — MRO is
  `CroniterBadCronError -> CroniterError -> ValueError -> Exception`. NOT a
  `RecurringError`, so it propagates and kills the entire `relay recurring` run.
  Under cron every other due template then silently fails to instantiate.
- `Template.load` (lines 43–64) checks `schedule` is *present* but never that
  it parses.

### Suggested fix
- Validate the cron inside `Template.load`: try `croniter(fm["schedule"])`,
  raise `RecurringError("`schedule` is not a valid cron expression: …")` on
  failure. Both `scan_due` and `list_templates` then inherit the guard and the
  bad template lands in `DueScan.errors` like any other skip.
- Tests to add in `tests/test_recurring.py`:
  - malformed `schedule` → that template skipped (in `scan.errors`), the rest of
    the sweep still creates/launches.
  - template dir with **no `ticket.md`** → skipped (covers the "missing ticket.md"
    branch at `recurring.py:46-47`, distinct from missing-frontmatter).
- After fix lands, add the one-line "verified for cron" note to ticket `## Context`.

## Ticket setup (bootstrap)
- Workflow: `code/with-review` (implement → peer-review → open-pr → owner review).
- Context attached: `relay/recurring` (agent changes the recurring create/scan path).
- assignee/agent: claude.

## Evaluator review

**1. Cold-start clarity & accuracy of the named gap**

Yes, an agent could start from the ticket alone — it names the file, the two functions, the exact line, the exception class and its MRO, and the fix location. All accurate against the code:

- `recurring.py:242` is `last_fire = _last_firing(template.schedule, now)`, which is indeed *outside* the `try/except RecurringError` at line 271. Confirmed.
- `_last_firing` (line 663) calls `croniter(cron, now)` unguarded; a malformed cron raises `CroniterBadCronError`, which subclasses `ValueError`/`Exception`, not `RecurringError`. So it propagates past the line-237 `Template.load` guard (already passed) and there is no enclosing guard until 271. Confirmed — it kills the whole sweep. The blackboard's MRO note is correct.
- `Template.load` (43–64) validates `schedule` is *present* (line 54) but never that it *parses*. Confirmed.

**2. Fix correctness & altitude**

Validating cron in `Template.load` is the right altitude and is correct. Every entry point constructs Templates through `Template.load`, so the guard is inherited everywhere:

- `scan_due` (236), `list_templates` (489), `scan_debug` (418), `create_named` (310) all call `Template.load` inside or before their `except RecurringError` handling. The bad template lands in `DueScan.errors` / `TemplateStatus.error` as claimed.
- Importantly, **after** the fix `template.schedule` is guaranteed parseable, so the *unguarded* `_last_firing` calls at 242, 243, 324–325, 506–508 all become safe without touching them. This is the elegant part and the ticket calls it out correctly.

One real under-reach to flag — the fix does **not** fully cover `create_named` / `create_template`:

- `create_named` (296) calls `Template.load` (310) then `create_template`. With the fix, `Template.load` raises `RecurringError` on a bad cron — but `create_named` has **no** try/except; it propagates `RecurringError` to the caller. That's acceptable (it's a single explicit `relay recurring launch <name>` invocation, not a sweep, and `RecurringError` is the declared failure type), but it's not "skipped" the way the sweep is — the ticket's "both scan_due and list_templates get the guard for free" wording is accurate as far as it goes but silently omits the create paths. Worth a sentence so the implementer doesn't assume every path now degrades gracefully.
- The fix changes behavior of `_effective_mode`-ordering too: note that in `create_template`, `_last_firing` at 324 runs *after* `_effective_mode` (322). Irrelevant once cron is validated at load, but confirms there's no second unguarded cron parse the load-fix misses.

**3. Workflow & context**

- `code/with-review` is appropriate — this is a real code+test change with a peer review gate, proportionate to a v1 launch blocker.
- `relay/recurring` is the correct and sufficient context; the change is entirely within the recurring create/scan path. Nothing missing or superfluous.

**4. Scope**

Reasonable for one ticket, lightly bundled but cohesively. Deliverable 1 (the fix) is the core. Deliverable 2 bundles **two** tests: (a) malformed-schedule skip, which is the direct regression test for this fix — clearly in scope; and (b) missing-`ticket.md` test, which covers the `recurring.py:46-47` branch that is *already implemented* and unrelated to the cron bug. That second test is opportunistic coverage-filling riding along on this ticket. It's small and the ticket is honest that it's filling a gap distinct from missing-frontmatter, so it's defensible — but an implementer should know (b) is not testing any code this ticket changes. Deliverable 3 (one-line context note) is trivial bookkeeping.

**5. Assumptions to question before launch**

- **`CroniterBadCronError` is the only exception class.** The ticket assumes a single exception type. Verify the implementer catches the right surface: `croniter()` can also raise `CroniterNotAlphaError`/`CroniterBadDateError` for some inputs, all subclassing `CroniterError`. The fix should catch `CroniterError` (or `(ValueError, ...)`), not just `CroniterBadCronError`, or some malformed schedules still leak. The ticket's narrow naming could mislead a literal implementer.
- **`croniter(fm["schedule"])` validity vs. `croniter(cron, now)` usage.** The blackboard suggests `try croniter(fm["schedule"])`. croniter's lazy validation: constructing `croniter` without a base time, or without calling `get_prev/get_next`, may not trigger full validation for every malformed input. The validator should construct it the same way the real call does (`croniter(cron, now)`) and ideally probe a firing, to guarantee it catches everything `_last_firing` would. Worth confirming in the test that the malformed input chosen actually raises at construction.
- **Slack-summary claim.** The comment at line 277 says the command "posts a Slack summary so the failure is never silent." The ticket leans on errors landing in `DueScan.errors` as sufficient. Confirm the `relay recurring` CLI actually surfaces `DueScan.errors` to Slack/stderr under cron (no TTY) — that's the whole "no human is watching" justification. Not in the files reviewed; the implementer should not assume it.

Net: ticket is high-quality and launch-ready. Two things to fix before/at implementation — catch `CroniterError` (not just `CroniterBadCronError`) and make the load-time probe match the real `_last_firing` call so validation can't be bypassed by lazy parsing.

## Peer review (2026-06-17, Codex)

- Ran native review from `/tmp/relay-validate-recurring-cron` with
  `codex review --base main` (sandbox retry required because the first attempt
  hit Codex's read-only app-server init failure).
- Finding: the implementation validated schedules against fixed
  `datetime(2000, 1, 1)`, which could reject croniter-valid year-scoped
  schedules that are valid at the actual sweep date.
- Applied must-fix in commit `062d9b5`:
  `Template.load(..., now=...)` now validates with the caller's `now`, and
  `scan_due`, `scan_debug`, `list_templates`, and `create_named` pass their
  resolved timestamp through. Added a regression for a 2026 year-scoped
  schedule.
- Verification after peer fix:
  - `PYTHONPATH=/tmp/relay-validate-recurring-cron/src python -m pytest tests/test_recurring.py -q` → 72 passed
  - `PYTHONPATH=/tmp/relay-validate-recurring-cron/src python -m pytest -q` → 756 passed, 1 skipped
  - `git diff --check` → clean
