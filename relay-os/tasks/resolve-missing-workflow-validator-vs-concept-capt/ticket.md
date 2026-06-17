---
title: Resolve missing-workflow validator vs concept-capture drafts
status: done
mode: interactive
owner: nick
human: nick
agent: claude
assignee: nick
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
  - name: review
    skills: []
    assignee: owner
---

## Description

**Governing rule: a task ticket must carry a workflow everywhere EXCEPT while
it is a `draft`.** `draft` is the authoring grace period — workflow-less is a
valid, intentional state there (concept-capture: stash the idea before its
shape is settled). Once a ticket leaves `draft`, a workflow is mandatory. The
only sanctioned workflow-less *active* tasks are the machine-authored
recurring (dream/cron) and retire tasks, which create straight to `active`
and run their body directly as the prompt.

The validator currently enforces the **opposite** of this rule, and that
incoherence is the bug (surfaced as Dream-2026-W21 gap G3, where validate-drift
returned 12 — now 43 — `missing-workflow` warnings):

- Workflow-less **`draft`** → emits a `missing-workflow` *warn*
  (`validate.py:658-668`). This nags the *allowed* state on every run forever.
  The author already chose it; the activation gate (`mark_active`,
  `mark.py:244`) already blocks the only thing the warning warns about. Pure
  noise — it dominates every validate-drift run and trains the operator to
  ignore the whole bucket.
- Workflow-less **`active`/`in_progress`** (not recurring/retire) → emits
  **nothing**. After the draft-only check, `_check_workflow_shape` returns
  (`validate.py:669`). The *actually-invalid* state — an activated ticket that
  no `relay bump` can ever advance — slips through silently.

So the validator warns on the valid case and is silent on the invalid case.
The fix is to flip it to match the governing rule.

### What to change

1. **Validator (`validate.py`, `_check_workflow_shape`)**
   - **Remove** the `missing-workflow` warn on `draft` tickets
     (`validate.py:658-668`). A workflow-less draft is valid; stop flagging it.
   - **Add** an `error` for a non-`draft`, non-`done` ticket that is
     workflow-less AND is not a sanctioned recurring/retire task — that ticket
     is structurally stuck (cannot be bumped). Whitelist the sanctioned
     exceptions by their existing marker (`created_by` is `system` for
     recurring / `retire` for retire; confirm the reliable signal — see
     `recurring.py:603-623`, `commands/retire.py:92-105`).
   - **Keep** the existing `bad-shape` error (step set but workflow null,
     `validate.py:651-657`) and `missing-step` error.

2. **validate-drift classifier (`bootstrap/dream/tasks/validate-drift/run.py`,
   line ~232)** — drop the `missing-workflow → human-needed` mapping (kind no
   longer emitted) and add handling for the new active-workflow-less error
   (route to `human-needed`: an activated stuck ticket is a lifecycle decision).

3. **Docs/contexts — make the prose state the rule explicitly.** The comb found
   the prose is *mostly* already consistent ("a workflow-less draft is a valid
   authoring state") but never states the symmetric half (required once
   active). Update and keep both halves in sync with packaged copies under
   `src/relay/resources/templates/`:
   - `relay/architecture` SKILL.md (~L128, L136, L259) — add: required from
     activation onward; recurring/retire are the only workflow-less active
     tasks.
   - `relay/cli` SKILL.md — `--workflow` optional *in draft only*; clarify the
     validator now errors on workflow-less active tickets.
   - `bootstrap/ticket` SKILL.md — the "if genuinely nothing fits, hand back a
     workflow-less draft" branch stays valid (draft is exempt); reconcile with
     the "you do not hand back a ticket without one" line so they don't
     contradict.

### Out of scope (no migration needed)

The 43 existing workflow-less drafts are **valid** under this rule — they are
drafts. They simply stop being flagged; none need a workflow assigned to
satisfy the invariant. (Triaging the "incomplete-real-work" ones into proper
tickets is separate backlog hygiene, not this ticket.)

The sibling ticket `document-workflow-less-concept-capture-drafts-as-s`
(Dream W22 G5) documents the same "workflow-less draft is supported" half —
its premise is correct under this rule. Fold its doc work into change (3) here
or close it as covered.

## Acceptance

- `relay validate` no longer emits `missing-workflow` on workflow-less drafts;
  re-run validate-drift on this repo and confirm the ~43 drafts no longer
  surface in `human-needed`.
- `relay validate` emits an `error` on a workflow-less `active`/`in_progress`
  non-recurring/retire ticket (covered by a new test mirroring the existing
  `tests/test_validate*.py` style).
- Recurring/retire tasks (workflow-less by design, `active`) do NOT trip the
  new error — regression-tested.
- Contexts/docs above state both halves of the rule; live and packaged copies
  in sync.
- Full suite green (`python -m pytest`); `relay validate --json` clean on the
  example fixture.

This finding came out of the Dream-2026-W21 knowledge scan as gap G3.

## Context

The validator chokepoint is `_check_workflow_shape` in `src/relay/validate.py`
(~L645-700). The activation gate that already enforces the draft→active
boundary is `mark_active` (`src/relay/mark.py:244`, raises `WorkflowMissing`);
this ticket does not change that gate — it makes the validator agree with it.

Sanctioned workflow-less-active exceptions and how they're created:
`recurring.py:603-623` (recurring/dream, `status="active"`, `created_by`
`system`) and `commands/retire.py:92-105` (retire, `status="active"`,
`created_by` `retire`, slug `retire-*`).

