---
title: Repair ticket referents when a referent is renamed or canceled
status: in_progress
owner: nicktoper
agent: claude
workflow:
  name: draft-for-human
  steps:
  - name: agent-produces
    skills: []
    assignee: agent
  - name: human-owns-and-finishes
    skills: []
    assignee: owner
  - name: open-pr
    skills:
    - code/open-pr
    assignee: agent
    requires: pr
  - name: report-to-coga
    skills: []
    assignee: agent
step: 2 (human-owns-and-finishes)
---

## Description

Nothing repairs a ticket's referents when the thing it points at is renamed,
superseded, or canceled. The pointing ticket keeps naming a referent that no
longer means what it did, and a launch gate can name a canceled ticket as a
required precondition — which stops the gate from ever being satisfiable.

Add the repair path: a rule in `coga/skills/tickets/launch-gates/SKILL.md`, a
sweep, or a step that runs at cancel/rename time.

## Context

Raised by the Dream 2026-W36 knowledge scan (Phase 2, shard-09) as a `gap`.

Five live findings in the same run are instances of it:
`resolve-three-stale-multiply-context-claims-flagge` is gated on a canceled
ticket; `v1/communication/doc`'s launch gate names a canceled ticket as a
required referent; `multiply/v1-architecture` names the canceled
`v1/2-self-update` as a live downstream owner; and two `v1/updater/*` drafts
still cite an abandoned design. The pattern is not rare.

### Dream 2026-W39 recheck

The first remedy listed above already exists: `coga/skills/tickets/launch-gates/SKILL.md`
step 4 of "Checking a gate at launch" (added 2026-08-31, commit `80dd373`)
makes a canceled or superseded referent a *broken* gate, tells the agent to
find the successor via the cancel message in `coga/log.md` and rewrite the gate,
and otherwise `coga block` with a "launch gate broken" reason — extended to
renamed, split, or spec-of-record referents. What remains undelivered is the
second and third options only (a sweep, or a repair step at cancel/rename time
that fixes the *pointing* tickets). Narrow the ask to that half. The
`resolve-three-stale-multiply-context-claims-flagge` example cited in
`## Context` has since been resolved on `main`.

<!-- coga:blackboard -->

## Production notes

Moved from FastJVM/multiply on 2026-09-24: filed there by Dream/autofix against coga itself (status there was `draft`; canceled in multiply as moved). Reset to `draft` for re-triage here. Paths, branches, worktrees and ticket slugs in the notes below refer to the multiply repo unless they say otherwise.


The blackboard is a notepad to be written to often as the human and agent works through a task.

## Dev
branch: repair-dead-dependency-asks

## Draft (agent-produces, 2026-10-06)

**Reframe for coga.** `coga/skills/tickets/launch-gates/SKILL.md` is a multiply-only skill; coga has no
launch gates. Coga's machine-readable ticket→ticket referent is the `Depends on <ref>: …` blocker ask
(`coga/lifecycle` § Dependencies and supersession), drained by megalaunch when `<ref>` is `done` or
disappears *during the run*. Stuck cases found: target **canceled** (cancel ≠ completion), target
**renamed/deleted** (slug never resolves; coga has no rename command, so this is a hand `git mv`), and
target **done + retired between runs** (satisfied, but the drain only sees same-run disappearance — a
second bug the ticket didn't name).

**Delivered on branch `repair-dead-dependency-asks` (commit 2e8018b9b), report-only:**
- `src/coga/dependency_asks.py` — shared helper `dead_dependency_asks(cfg, refs, targets=)`; classifies
  canceled / missing / retired using ticket status plus newest terminal `coga/log.md` line; extracts a
  `Superseded by <ref>` successor from the cancel reason. Two consumers ⇒ core per microkernel rule.
- `coga validate` → new warn `dead-dependency` per stranded ask (this is the "sweep": Dream's weekly
  validate-drift runs it; classified `human-needed` in `dream_validate_drift.py`).
- `coga mark canceled` → after a successful cancel, prints each live dependent it stranded + remedy
  (best-effort, never fails the cancel).
- `coga/lifecycle` + `coga/codebase` topics updated (packaged twins copied, byte-identical).
- `tests/test_dependency_asks.py` (8 tests).

**Decisions / weak spots for the human:**
1. *No auto-rewrite.* Even with `Superseded by X`, the dependent's ask is not re-pointed — the successor
   may not cover what B needed. Remedy text spells `coga unblock` + `coga block --reason "Depends on X: …"`.
   If you want auto-repair at cancel time, that's a cross-ticket mutation and needs its own publish story.
2. *Retired* detection is heuristic: missing file + newest terminal log line is `task done…` or contains
   `→ done`. Alternative: teach the megalaunch drain to treat a log-done missing ref as satisfied
   (would fix that case instead of reporting it). Not done — changes drain contract.
3. Only the `Depends on <ref>` spelling is recognized (narrower than the drain, which accepts any full ref
   in a blocker reason). Prose referents in bodies/topics (e.g. multiply's `v1-architecture` naming a
   canceled ticket) stay Dream knowledge-scan territory.
4. Stdout of `mark canceled` gains extra lines when dependents exist; I found no parser of that output.

**Verification:** `pytest tests/test_dependency_asks.py tests/test_validate.py tests/test_mark.py
tests/test_megalaunch.py tests/test_dream_validate_drift.py tests/test_packaging.py` → 392 passed.
Full suite: 3281 passed, 1 failed — `test_edge_distribution.py::test_documented_legacy_adoption_preserves_state_and_reconciles_callers`,
which fails identically on `main` without this change (pre-existing). `coga validate` on this repo:
no `dead-dependency` findings today.
