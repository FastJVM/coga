---
title: Recurring sweep runs Dream cleanup phase last and consolidates ticket deletion
status: in_progress
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
- relay/recurring
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
  - name: review
    skills: []
    assignee: owner
step: 1 (implement)
---

## Description

In a `relay recurring` sweep, run Dream — the recurring janitor — **last**, so
its retro/cleanup pass acts on the period tickets the *same* sweep just produced.
Today templates launch in alphabetical directory order (`digest` → `dream` →
`relay-dev-update`), so Dream can run before the tasks whose `done` tickets it is
supposed to reap. The result is that a sweep's own output isn't cleaned up until
the *next* Dream run — cleanup lags a full sweep.

This is **ordering only**. Do not touch deletion logic: deletion of real `done`
period tickets is already centralized in Dream's Phase-4 retro pass and must stay
there (see the correction below). The fix is to make Dream sort last so that
single existing cleanup path covers the current sweep instead of trailing it.

Done looks like: in a bare sweep that fires `dream` alongside other due
templates, `dream` is launched after them, so its Phase-4 reap sees this sweep's
freshly-`done` period tickets.

## Context

**Why this came up.** Diagnosed live from the 2026-06-09 `recurring --all` debug
sweep (suffix `20260609T151909`). Dream fired at 15:54, ten minutes *before*
`relay-dev-update` at 16:04 — purely because `dream` sorts before
`relay-dev-update`. Evidence is in the template `log.md` files under
`relay-os/recurring/<name>/`. (Note: that diagnosis came from the `--all` *debug*
path; the behavior to fix lives on the *bare* path — see "Which path" below.)

**Root cause — ordering is alphabetical, not phased.** `scan_due` and
`scan_debug` in `src/relay/recurring.py` both iterate `sorted(root.iterdir())`
(lines ~187 and ~382), so launch order is just the template directory names.
Dream is not special-cased to run last; it lands wherever its name sorts. The
sweep loops are in `src/relay/commands/recurring.py`: `main()` (bare sweep, def
~line 51, launch loop ~line 126) and `_launch_all_debug()` (`--all`, def ~line
145).

**Correction — deletion is NOT scattered; do not consolidate anything.** An
earlier draft of this ticket claimed deletion was spread across three mechanisms
to fold into Dream. That is wrong and verified false against source:
- The only deleter of real `done` period tickets is **Dream's Phase-4 retro
  pass** (`retro/done-ticket`). `relay/recurring` SKILL.md (lines ~102–122) states
  it directly: "no recurring-command deletion; Dream-acting-on-`done` is the only
  cleanup path."
- `_finalize_debug_run()` (~line 225) and `_reap_debug_orphans()` (~line 256)
  only `rmtree` `*-dbg-*` throwaway scratch on the `--all` debug path, guarded by
  `is_debug_slug(...)`. They never touch real tickets and must **not** be folded
  into Dream — Dream doesn't even run deletion on the `--all` path.

So there is nothing to consolidate. Keep the single Dream cleanup path; just fix
when Dream runs.

**Severity — this lags, it does not leak.** A period ticket Dream misses in one
sweep is not lost: it sits on disk as `status: done` and the next Dream run's
Phase-4 reaps it. So the fix tightens the cleanup loop (clean up within the same
sweep) rather than plugging a leak. Don't over-engineer it.

**Which path.** The fix targets the **bare `relay recurring` sweep** — that is
where Dream actually performs cleanup. The `--all` debug path is **out of scope**:
it uses `scan_debug` / `_launch_all_debug`, and on it Dream deletes nothing
(scratch is reaped by `_finalize_debug_run`). Don't change `--all` ordering for
cleanup reasons.

**Design decision for the implement step (surface it, don't silently pick):**
how to guarantee Dream-runs-last on the bare sweep.
- Option A — hardcode: the sweep explicitly orders the `dream` template last.
  Simplest, but makes Dream load-bearing in the engine.
- Option B — generic phase: templates declare an ordering/phase hint (e.g. a
  `phase: cleanup` field in the recurring `ticket.md` frontmatter) and the
  scanner sorts cleanup-phase templates last. More general, keeps the engine
  agnostic about Dream; aligns with the "keep things simple / legible" lean.
  Prefer this unless it balloons scope. Note the sort key is **layered**:
  `DueScan.due` already re-sorts by `(not resuming, last_fire)`
  (`src/relay/recurring.py` ~line 162), so a cleanup-phase ordering must compose
  with that resume-first / most-overdue-first order, not replace it.

**Out of scope (call out, don't build here):** backfilling *missed past periods*
(catch-up for periods that never fired) — the un-built
`recurring-catch-up-for-missed-runs` ticket. Current-period orphan resume is
already handled. Keep this ticket to ordering only; split if it grows.

**Touchpoints / sync:** behavior change to the recurring engine — update
`relay-os/contexts/relay/recurring/SKILL.md` in the same PR to describe the
cleanup-phase ordering. There is **no packaged copy** of that context
(`src/relay/resources/templates/relay-os/contexts/` ships only `_template` and
`browser`), so the SKILL.md edit has no twin to sync. Only if this ticket touches
the dream recurring *template* does the packaged copy under
`src/relay/resources/templates/relay-os/recurring/dream/` need to stay in sync.
Tests live in `tests/`; add/extend coverage for sweep ordering.
