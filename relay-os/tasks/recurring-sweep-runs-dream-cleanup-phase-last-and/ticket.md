---
title: Recurring sweep runs Dream cleanup phase last and consolidates ticket deletion
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: claude
contexts:
  - relay/recurring
skills: []
workflow: code/with-review
---

## Description

The `relay recurring` sweep should run as a clean linear pipeline: instantiate
the due period tasks, execute everything it can (including runs left orphaned by
a prior crash), and then run Dream **last** as a cleanup/retro phase that retros
the period, deletes the period's spent tickets, and finishes itself. Today it
does not — Dream is just another template in the rotation, ordered
alphabetically, so it can run before the tasks it is supposed to clean up.

Make the sweep run the Dream cleanup/retro phase last, and consolidate the
currently-scattered ticket-deletion logic into that phase so there is one
legible place that reaps a sweep's tickets instead of three.

Done looks like: in a sweep that fires `digest`, `dream`, and `relay-dev-update`,
Dream runs after the other two and is the thing that reaps their spent period
tickets — regardless of template names.

## Context

**Why this came up.** Diagnosed live from the 2026-06-09 `recurring --all` debug
sweep (suffix `20260609T151909`). Dream fired at 15:54, ten minutes *before*
`relay-dev-update` at 16:04, so it could not have swept the tickets that the
later leg produced. Evidence is in the template `log.md` files under
`relay-os/recurring/<name>/`.

**Root cause — ordering is alphabetical, not phased.** `scan_due` and
`scan_debug` in `src/relay/recurring.py` both iterate `sorted(root.iterdir())`,
so launch order is just the template directory names (`digest` → `dream` →
`relay-dev-update`). Dream is not special-cased to run last; it lands wherever
its name sorts. The sweep loop itself is `src/relay/commands/recurring.py`
`main()` (bare sweep, ~line 124) and `_launch_all_debug()` (~line 165).

**Deletion is scattered across three mechanisms** that this ticket should
consolidate into the final Dream phase (or at least route through one place):
- `_finalize_debug_run()` — rmtrees each `--all` debug run as it completes
  (`src/relay/commands/recurring.py` ~line 223).
- `_reap_debug_orphans()` — clears `*-dbg-*` scratch a crashed prior sweep left
  behind (~line 254).
- Dream's own "sweep done recurring period tickets" behavior (shipped in #322)
  plus its `cleanup-orphan-markers` step.

**Design decision for the implement step (surface it, don't silently pick):**
how to guarantee Dream-runs-last.
- Option A — hardcode: the sweep explicitly orders the `dream` template last.
  Simplest, but makes Dream load-bearing in the engine.
- Option B — generic phase: templates declare an ordering/phase hint (e.g. a
  `phase: cleanup` field in the recurring `ticket.md` frontmatter) and the
  scanner sorts cleanup-phase templates last. More general, keeps the engine
  agnostic about Dream. Aligns with the "keep things simple / legible" lean.
  Prefer this unless it balloons scope.

**Out of scope (call out, don't build here):** backfilling *missed past periods*
(catch-up for periods that never fired) is a separate concern — the
`recurring-catch-up-for-missed-runs` ticket was never built. This ticket only
covers current-period orphan resume (already handled) + ordering + deletion
consolidation. If it grows past that, split it.

**Touchpoints / sync:** behavior change to the recurring engine — update
`relay-os/contexts/relay/recurring/SKILL.md` in the same PR to describe the
cleanup-phase ordering. Keep the live `relay-os/` copy and the packaged copy
under `src/relay/resources/templates/relay-os/` in sync if the recurring
templates change. Tests live in `tests/`; add/extend coverage for sweep
ordering.
