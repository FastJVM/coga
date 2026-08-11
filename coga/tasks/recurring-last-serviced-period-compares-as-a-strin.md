---
slug: recurring-last-serviced-period-compares-as-a-strin
title: 'recurring: last_serviced_period compares as a string, so a non-period value
  suppresses a template forever'
status: active
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
step: 1 (implement)
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
