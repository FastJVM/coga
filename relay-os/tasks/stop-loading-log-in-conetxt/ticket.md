---
title: stop loading log in conetxt
status: draft
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
contexts:
  - relay/architecture
skills: []
workflow: null
---

## Description

Keep the **composed** prompt small by drawing a hard line between what gets
loaded into an agent's context and what doesn't, and stop the recurring
blackboards from accumulating history that bloats every future run.

Three work items:

1. **Document that logs are never composed.** `compose_prompt` only loads
   `blackboard.md` (layer 7); no `log.md` (task or recurring template) is ever
   a composition layer. Make that explicit in `relay/architecture` so the
   division of labor is canon: blackboard = forward state (composed, keep
   small); log = durable history (never composed, may grow). — **DONE**
   (architecture context, all three synced copies).

2. **Trim the blackboard to the last ~2 runs.** The recurring template
   blackboard *is* composed (layer 7) and grows unbounded — relay-dev-update
   accumulates `scaffolded …` ledger lines, digest accumulates spool/ledger
   records. Only the last run or two is ever useful to the next run. Provide a
   "clear blackboard except the last N runs" operation (default N=2) so the
   composed payload stays bounded.

3. **Debug/run records go to the log, not the blackboard.** Debug runs (and
   period-ledger bookkeeping) currently leave records in the composed
   blackboard/spool (e.g. `*-dbg-*` entries). Those belong in `log.md`
   (uncomposed), not in the blackboard the next run reads. Append them to the
   log instead. — **DONE** (`_record_run` writes to `log.md`;
   `_period_already_scaffolded` reads it with a legacy-blackboard fallback;
   live digest + relay-dev-update blackboards migrated).

**Item 2 resolved without new code:** moving the ledger + debug records to
`log.md` (item 3) removed the only unbounded accumulator in the composed
blackboard. What remains is working state each run overwrites
(relay-dev-update's State block) or drains (digest's spool), so the blackboard
no longer grows without bound — no `trim` command needed. (Decision 2026-06-06.)

All three items complete.

## Context

Verified during the session: `compose_prompt` (src/relay/compose.py) composes
only `blackboard.md`. The recurring period ledger currently lives in the
template `blackboard.md` and `scan_due` reads it for idempotency
(`_record_run` in src/relay/recurring.py) — so item 2/3 must move the *write*
and the *read* together, or scan_due will re-scaffold an already-handled
period. That coupling is the main design decision to settle before coding 2/3.
