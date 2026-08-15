---
slug: recurring-last-serviced-period-compares-as-a-strin
title: 'recurring: last_serviced_period compares as a string, so a non-period value
  suppresses a template forever'
status: in_progress
owner: nicktoper
human: nicktoper
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
step: 3 (open-pr)
---

## Description

`_period_already_serviced` compares the `last_serviced_period` high-water mark
against the current period with a **string** comparison. Any value that is not
a `YYYY-MM`-shaped key still compares, and one that sorts above every future
period key disables the template **permanently** — silently, and while
reporting itself as healthy.

`coga/recurring.py:1029`:

```python
def _period_already_serviced(template: Template, period_key: str) -> bool:
    last_serviced = read_last_serviced_period(template.ticket_path)
    return last_serviced is not None and last_serviced >= period_key
```

`_read_last_serviced_period_text` matches `^last_serviced_period:\s*(?P<period>\S+)\s*$`
— any non-whitespace token, with no shape validation.

## Reproduction

In a template's blackboard region:

```
last_serviced_period: none
```

`"none" >= "2026-08"` → `True`. `"none" >= "2027-02"` → `True`. `"none"` sorts
above **every** `20xx-xx` key, because `n` (0x6E) is greater than `2` (0x32).
The template never fires again, at any point in the future.

Any word starting with a letter behaves the same way: `never`, `unset`, `n/a`,
`TBD`, `pending`.

## Why it is worse than a wrong value

**It reads as healthy.** `coga status` shows the template as
`ran this period — task reaped`, which is exactly what a correctly-serviced
template looks like. Nothing distinguishes "up to date" from "permanently
disabled."

**It fails in the silent direction.** For a deadline reminder, a template that
never fires is the whole failure mode the template exists to prevent — and it
is the one state nobody goes looking for.

**The wrong value is a plausible thing to write.** It was written by an agent
seeding a new template that had not run yet, where a word reads as more honest
than inventing a period key. The correct move — seed a real period key to
suppress the run you do not want — is not obvious from the field name, and
nothing in the codebase says so.

## Where it was hit

`FastJVM/admin`, 2026-08-11, building `coga/recurring/rnd-tax-credit-prep/`. An
annual R&D tax-credit reminder was seeded `last_serviced_period: none` so it
would not fire retroactively for a tax year already claimed. Caught by reading
`recurring.py`, not by any signal from coga. Had it shipped, an annual filing
reminder would have been silently dead from creation, and the failure would
have surfaced as a missed tax credit years later.

Worked around by seeding `2026-02` — the real period key of the firing being
suppressed.

## Suggested fix

Roughly in order of value:

1. **Validate the shape on read.** Reject anything not matching `^\d{4}-\d{2}$`
   and fail loud, naming the template and the offending value. A malformed
   high-water mark is a repo error, not a schedule outcome.
2. **Compare as periods, not strings** — parse to `(year, month)`. Removes the
   whole class of ordering surprise rather than just the words we thought of.
3. **Surface it in `coga status`.** An unparseable mark should read as an error
   state, never as `ran this period`.
4. **Say it in the docs.** Whatever documents recurring templates should state
   that the field takes a real period key and that seeding it is how you
   suppress a first firing — the legitimate use case that led here.

(1) alone closes the silent failure. (2) is the durable fix.

## Notes

Raised from `FastJVM/admin` by Zach, 2026-08-11.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Implement notes

- The original blackboard-backed `last_serviced_period` field was removed by
  `f5543446` in favor of the repo-global append-only log, but the defect moved
  with the state: `_SERVICED_LOG_RE` accepts any non-whitespace token,
  `serviced_periods` chooses the maximum token lexically, and
  `_period_already_serviced` compares it lexically.
- Coga emits five period-key shapes, depending on schedule granularity:
  `YYYY-MM`, `YYYY-Www`, `YYYY-MM-DD`, `YYYY-MM-DD-HH`, and
  `YYYYMMDDTHHMM`. The fix must validate and compare all five as real calendar
  periods rather than narrowing the contract to monthly keys.
- Planned behavior: parse the ledger once into valid high-water marks plus
  per-template errors; skip and report only a malformed template during a
  sweep, and render that template as an error in read-only list/status views.
  Preserve `serviced_periods()` as the public string-map view, but make direct
  use fail loudly when malformed ledger state exists.

## Dev

branch: codex/validate-recurring-periods
worktree: /tmp/coga-recurring-period-validation

## Progress

- Added failing regressions first; all nine original regression cases failed
  on `main` (malformed values were accepted, views said `ran this period`, and
  `2026-W01` lexically suppressed `2026-12`).
- Implemented one shared serviced-ledger parser for the working-tree log and
  the control-ref race guard. It validates all five keys Coga emits, normalizes
  them to calendar positions for max/comparison, and retains malformed records
  as per-template errors.
- Scans now skip/report the malformed template while continuing healthy ones;
  `coga recurring list` and `coga status` render the malformed template as an
  error. The writer also refuses to append an invalid key.
- Targeted regressions pass for malformed local/control records, mixed key
  shapes, both views, healthy-template continuation, and the control-branch
  sync guard.
- Final verification: all 188 recurring tests pass; 134 adjacent
  command/create/autoclose tests pass; full suite passes with 1,759 passed and
  1 skipped. The task-scoped `coga validate --json` reports no issues. The
  repository's live serviced ledger parses with 9 templates and no errors
  under the new rules.

## Handoff

- Commits after the final rebase: `360c528b9f1c301bb03832f22cd40002ce01e03c`
  (`Validate recurring serviced period keys`) and
  `085006f691a498002bb7f8bad62ee40797ca2b53` (`peer-review: validate
  control recurring ledger`).
- The feature checkout is clean. The required final `git fetch origin main`
  plus `git rebase FETCH_HEAD` completed successfully, `origin/main` is an
  ancestor of the feature tip, and the live/packaged architecture context pair
  remains byte-identical.
- No push or PR was created in this step.

## Peer review

- `codex review --base main` found two must-fix control-branch cases. An
  override launch (`recurring launch` / `--force`) skipped parsing the control
  ledger because it bypassed dedup, and a normal feature-branch sweep could
  skip a control-only malformed record once but launch the locally-created task
  on its next retry.
- Review reproduced both failures with the real-git fixture. The fix must
  validate control ledger records even when their values do not participate in
  the serviced-period skip, and must keep reused tasks behind the same control
  validation gate on later sweeps.
- Applied the review fix without deleting recovery state: control-ledger
  parsing now always runs inside the race guard even when dedup is disabled,
  and reused/no-task scan rows plus reused named launches pass through a
  read-only control-ledger validation gate. The locally created active task is
  retained, but it cannot launch until the malformed control record is fixed.
- Added real-git regressions for two consecutive named launches and two
  consecutive ordinary feature-branch sweeps, plus a focused override-gate
  test. All 191 recurring tests pass.
- Verification before and after the final rebase: full suite passes with 1,762
  passed and 1 skipped; task-scoped `coga validate --json` reports no issues.

## PR

### Summary

- Parse all five recurring period-key shapes into calendar positions before
  selecting or comparing serviced high-water marks, and reject malformed or
  impossible calendar values instead of treating them as healthy state.
- Isolate malformed ledger records to their template during sweeps while
  surfacing the error in `coga recurring list`, `coga status`, direct ledger
  reads, writers, and the control-branch race guard.
- Keep control-only malformed records blocking override launches and retrying
  feature-branch sweeps, while allowing unrelated healthy templates to
  continue.
- Update the recurring/architecture contracts and operations documentation to
  describe the validated repo-global ledger behavior.

Test plan: `python -m pytest` (1,762 passed, 1 skipped); `coga validate --task recurring-last-serviced-period-compares-as-a-strin --json` (no issues).
