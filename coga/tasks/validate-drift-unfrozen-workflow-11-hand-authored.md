---
title: 'validate-drift: unfrozen-workflow — 11 hand-authored drafts carry an unfrozen
  workflow'
status: in_progress
owner: nicktoper
workflow:
  name: brief-for-human
  steps:
  - name: brief-and-hand-off
    skills: []
    assignee: agent
  - name: human-executes
    skills: []
    assignee: owner
  - name: verify-read-only
    skills: []
    assignee: agent
step: 2 (human-executes)
agent: claude
---

## Description

validate-drift: unfrozen-workflow

Filed by Dream 2026-W39, Phase 6 (validate-drift disposition). `coga validate --json` is the live member list for this class; membership below is this run's snapshot and is not copied run to run. This ticket is the durable record that the class needs a human decision. Dream does not change lifecycle, workflow, or assignee state.

**Completion rule.** This ticket stays open until the class is empty or the decision is recorded in a context. Before closing it with accepted warnings remaining, preserve the same tag line, the decision, its rationale, and the scope (conditions or members it covers) in the appropriate context, so the decision survives this ticket's retirement and later Dream runs can apply it instead of refiling.

**Class.** 11 tickets carry a `workflow:` that is a bare name rather than the frozen dict `coga launch`/`coga mark active` writes — hand-authored drafts awaiting first launch. Recipe remediation: "Needs an owner decision because the correction changes task routing, workflow state, or who is expected to act next."

**Decision needed.** Either activate/launch each member so its workflow freezes, leave it parked (and record in a context that unfrozen drafts under `coga/tasks/v2/` and hand-authored root drafts are an accepted baseline), or cancel. Five members are `v2/cleanup-core-commands/*` drafts that `coga/tasks/v2/README.md` already defines as off the execution path; `clean-up-all-the-working-trees`, `fix-git-sync-failure` and `parse-agents-rejects-cogalocaltoml` (both already `status: canceled` at scan time — the validator still reports them, so the decision may simply be that a canceled ticket's unfrozen workflow is accepted), and the two `marketing/plan/*` drafts are root-level.

**Members this run (2026-09-21):**
- `clean-up-all-the-working-trees` — workflow 'maintenance/with-approval' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `fix-git-sync-failure` — workflow 'code/with-self-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `marketing/plan/collect-public-examples-for-the-launch` — workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `marketing/plan/write-the-pitch-and-narrative` — workflow 'draft-for-human' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `parse-agents-rejects-cogalocaltoml` — workflow 'code/with-review' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `v2/cleanup-core-commands/lifecycle-verbs-to-ticket-operations` — workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `v2/cleanup-core-commands/read-report-commands-as-ticket-workflows` — workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `v2/cleanup-core-commands/residual-command-surfaces` — workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `v2/cleanup-core-commands/support-commands-boundary` — workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `v2/cleanup-core-commands/work-orchestration-commands-to-tickets` — workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch
- `v2/fix-windows-cli-import-crash` — workflow 'code/design-then-implement' is not a frozen dict — likely a hand-authored ticket awaiting first launch

## Context

<!-- coga:blackboard -->

## Decision and handoff — 2026-10-06

The human accepted the proposed warning baseline and explicitly authorized
the agent to override this step's read-only restriction for the context edits
and checks. The standing decision, rationale, scope, and reopening condition
now live in `docs/contexts/coga/workflows/SKILL.md`, under "Required at
activation, not at draft", tagged `validate-drift: unfrozen-workflow`. Its
packaged bootstrap twin has the identical change.

The current source validator reports 14 members: 10 drafts and 4 canceled
tickets, all within the accepted statuses. The original 11-member list above
is historical; `coga/tasks/v2/README.md` no longer exists. No member ticket's
lifecycle or workflow was changed.

Verification:
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -B -m coga.cli validate --json`
  (invoked through a read-only subprocess to count statuses): exit 0; all
  14 unfrozen warnings covered. Other warning classes remain out of scope.
  Used checkout source because the installed `coga` binary reports version skew.
- `.venv/bin/python -m pytest tests/test_packaging.py`: 23 passed.
- `git diff --check`: passed for the context edits.

The acceptance decision is recorded and the documentation checks pass.
Hand off to the human-owned step; do not skip its gate or close this ticket
from the briefing step.
