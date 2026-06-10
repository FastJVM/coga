The blackboard is a notepad to be written to often as the human and agent works through a task.

## Design decisions (this session)

- **Premise reversed: authoring-time, not impl-ready.** Owner (nick) decided
  triage runs at `relay ticket` / `bootstrap/ticket`, reversing both the
  predecessor (`automation-triage`) and the original draft of this ticket.
  Rationale: tier == workflow, so triage must run *before* the workflow is
  frozen; a step inside a `code/*` workflow runs too late to re-route. Full
  reasoning is in the ticket Description.
- **Surface area shrank.** No `code/*` / `dev/*` / `_template` *workflow* step
  is added. The change is concentrated in the `bootstrap/ticket` skill (+ its
  packaged mirror) plus an `## Autonomy` section on the task `_template`.

## Open Questions — RESOLVED by owner (this session)

1. **Advisory vs. mandatory tier→workflow mapping.** → **Advisory.** Tier informs
   the step-3 recommendation; human can override. (A `human-verify` code task can
   still use `code/with-review`.)
2. **Where to record the tier.** → **In `mode`** (`autonomous` / `human` /
   `human+ai`) — but that representation is **its own ticket** (filed below).
   This ticket adds **no** `## Autonomy` field/section and does **not** edit the
   task `_template`. The tier is expressed via the chosen workflow/assignees and
   shown in the step-7 summary only.
3. **`fully-automated` → mode?** → Triage may **suggest** an unattended mode
   (`script`, or `auto` = script + `claude -p`); do not auto-set, do not encode
   mode semantics here. Note: the predecessor ticket's "`mode: auto` is disabled"
   claim is *not* carried forward — owner's taxonomy differs; mode is the other
   ticket's job.
4. **Evaluator checks the tier?** → No special instruction needed; the owner's
   review already scrutinizes the classification.
5. **Active-edit re-classification?** → **No need** — human edits handle it. No
   special branch.

No open questions remain blocking. The spec is fully specified.

## Follow-up ticket (filed)

Per owner: the structured representation of the tier in `mode` (autonomous /
human / human+ai), reconciled with interactive/auto/script, is split out. Filed
as a draft: `represent-autonomy-tier-in-ticket-mode-field` (needs a
`bootstrap/ticket` interview to scope + pick a workflow before activation).

## Note on ticket status

This ticket is still `status: draft` (predecessor filed it as a draft). The
design step ran against it anyway. The owner will need `relay mark active`
before the implement step can run for real — flagging so it isn't a surprise at
the review-design → implement boundary.
