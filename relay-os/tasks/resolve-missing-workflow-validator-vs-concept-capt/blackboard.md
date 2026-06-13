The blackboard is a notepad to be written to often as the human and agent works through a task.

## Decision (2026-06-12, with nick)

Re-scoped from "pick option 1 or 2" to a coherence fix around one governing rule:

**A task ticket must carry a workflow everywhere EXCEPT while it is a `draft`.**
- `draft` = authoring grace period; workflow-less is valid there (concept-capture).
- `active`/`in_progress`/`done` require a workflow.
- Sole exception: machine-authored recurring (dream/cron) + retire tasks, which
  scaffold straight to `active` workflow-less and run their body as the prompt.

### The bug: validator is backwards
- Workflow-less `draft` → emits `missing-workflow` *warn* (validate.py:658-668).
  Nags the ALLOWED state forever (G3 noise — 43 hits on this repo now).
- Workflow-less `active` non-recurring/retire → emits NOTHING
  (validate.py:669 returns after draft-only check). The INVALID state (stuck,
  un-bumpable ticket) slips through silently.

Fix = flip it: stop warning on drafts; error on active workflow-less
(non-exception). Activation gate (mark.py:244) already enforces the boundary;
this just makes the validator agree.

## Comb map (from 3 Explore passes)

Validator: `_check_workflow_shape` validate.py ~L645-700.
  - missing-workflow warn: L658-668 (REMOVE)
  - bad-shape error (step set, wf null): L651-657 (KEEP)
  - missing-step error: L685-692 (KEEP)
Activation gate: mark_active mark.py:244 raises WorkflowMissing (KEEP, unchanged).
validate-drift classifier: run.py ~L232 missing-workflow→human-needed (REPLACE).
Sanctioned workflow-less-active (whitelist in new error):
  - recurring.py:603-623 — status=active, created_by=system, slug recurring-*
  - commands/retire.py:92-105 — status=active, created_by=retire, slug retire-*
Compose/automerge/ticket.current_step already null-safe — no change.

Docs/contexts asserting "workflow-less draft is valid" (KEEP, add symmetric half;
sync packaged copies under src/relay/resources/templates/):
  - relay/architecture SKILL.md ~L128, L136, L259
  - relay/cli SKILL.md ~L47-52, L70, L89, L114
  - bootstrap/ticket SKILL.md L23-26, L127-132 (reconcile internal contradiction)
  - README.md L279-283, L318, L409 (verify, not contexts but user-facing)

Drafts: 43 workflow-less drafts are VALID under the rule (drafts). No migration.
  Classification (informational only): 3 concept-capture, ~44 incomplete-real-work
  that *could* later get workflows (separate backlog hygiene), ~16 unclear/empty.
Sibling ticket document-workflow-less-concept-capture-drafts-as-s: premise now
  correct; fold its doc work into change (3) or close as covered.

## Status
- Ticket body rewritten to the above. Awaiting nick's green-light on the invariant
  before implementing the validator + docs change.
