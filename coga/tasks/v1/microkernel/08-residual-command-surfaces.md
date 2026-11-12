---
title: Classify residual command surfaces
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/microkernel/objectives
  - coga-dev/principles
  - coga/init
  - coga/tickets
  - coga/skill-management
  - coga/recurring/scheduling
  - coga/checkout-cleanup
  - coga-dev/codebase
  - coga-dev/testing
  - coga-dev/current-direction
  - coga-dev/microkernel
  - coga-dev/project-stage
  - coga/cli
  - coga/checkouts
workflow: code/design-then-implement
---

## Description

Classify the remaining authoring/tooling surfaces and give each a concrete
implementation owner: `ticket`, `skill *`, and the previously unassigned
`recurring promote` row. Prefer procedure scripts over permanent core heads,
while retaining the real shared validation/publication operations they use.
This is a refreshed classification scope for owner review.

### Objectives advanced

Hackability and ticket ownership: guided authoring, skill maintenance policy
and task-to-template promotion should be understandable and editable as
procedures. Simplification: remove redundant coordinators and command-to-command
imports rather than replacing them with equally coupled wrappers.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12); physical lines include blanks/comments.

1. All subjects remain. The microkernel open table also contains
   `recurring promote` with no ticket; this scope proposal supplies its owner.
2. `commands/ticket.py` is 423 lines, `authoring.py` 352;
   `commands/skill.py` is 211, `skill_manager.py` 2,123. Promotion is
   `commands.recurring.promote` plus `recurring.promote_task`.
   Guided authoring already uses the `coga.launch` service.
3. Requirements are stated here. The old description of `skill *` as merely
   a thin `gh skill` wrapper omits URL installation, provenance, adapted-tree
   updates and the PR flow; use the current module, not that shorthand.
4. Alias dispatch, package fallback resolution and guarded authoring
   finalization already ship. None of the three remaining placements is settled
   by those facts; do not rebuild those delivered mechanisms.

### Proposed classifications

| Surface | Proposed boundary | Evidence/constraint |
| --- | --- | --- |
| `ticket` | Move interview selection, create/edit kickoff and post-session coordination into `bootstrap/ticket` script behavior, consuming the public one-session executor | A plain agent-only launch alias would lose preflight-before-create and the deterministic post-exit phase |
| `authoring.finalize_authored` | Move authoring-only finalization orchestration with its ticket; retain shared validation and `git.publish` primitives | Only the ticket command calls this finalizer. Preserve validation of all authored tickets and changed knowledge before one guarded publication |
| `skill *` | Propose script command tickets for procedure and CLI policy; retain only demonstrated shared helpers or use the external tool directly where sufficient | Whole `skill_manager.py` is not proved shared by the generic runner or test imports; URL/provenance/adaptation/PR behavior must survive |
| `recurring promote` | Propose deterministic command-ticket orchestration over shared template validation, task IO and deletion primitives | Validate schedule/destination/workflow and load the new template before source removal; preserve attachments and explicit audit/publication behavior |

### Design work and bounded follow-ups

For authoring, preserve no-target/new/existing interviews, agent picking,
readiness checks before creating a draft, least-privilege environment and no
ticket-secret injection, snapshot-based changed-file selection and post-exit
finalization. An authoring script can orchestrate a single agent session using
the shared API; it must not recursively launch its own ticket or imitate a
stateful workflow transition. `resolve_authoring_agent` has real consumers in
authoring and megalaunch; that helper can remain shared without retaining the
whole authoring procedure in core. Remove the import from `commands.create` by
placing actually shared creation helpers with the existing creation machinery.

For skills, inventory per-symbol consumers in skill commands, init/agent-view
support and the recurring updater. Keep GitHub and URL sources, include
allowlists, local adaptations and PR publication in the comparison. Define a
bounded first migration and name any later implementation follow-up at owner
scope review; do not close the open row merely because a future move is named.
Changing the supported sources or installing a new plugin system is not part
of this classification.

For promotion, account for file and directory tasks, attachments, schedule
validation, workflow conversion, fresh template verification and removal
failure. `promote_task` is ordered filesystem work, not a proven distributed
atomic transaction. Reuse the existing primitives without promising stronger
atomicity, and preserve failures rather than suppressing a partial result.
This ticket owns promotion only; the read/report sibling owns `recurring list`,
and the recipe sibling owns `recurring-scan`.

### Acceptance and reduction evidence

- [ ] Record a per-surface retained/moved proposal with actual consumers and
      invariants; assign implementation steps/follow-ups with no unowned row.
- [ ] Show the full alias → ticket → implementation path and the editable
      local alternative for each moved procedure.
- [ ] Preserve authoring's post-exit transaction and no-secret environment;
      skill update's provenance/adaptation and PR behavior; promotion's
      validation-before-removal and attachment behavior.
- [ ] Identify coordinator/wrapper deletions and estimate full production
      scope at a named revision; no claim of reduction before implementation.
- [ ] Update user owners and microkernel placement when decisions land.
      Carry forward authoring/ticket/create, skill-manager, recurring,
      publication and packaging tests with required full-suite/native receipts.

## Context

Read `coga-dev/microkernel/objectives`, `coga-dev/packaging`,
`coga-dev/testing`, and package-owned `coga/tickets/authoring`,
`coga/skill-management`, `coga/recurring/templates`, `coga/edge-code`,
`coga/script-tickets` and `coga/state-publication` under
`src/coga/resources/templates/coga/bootstrap/contexts/`.

Definition discovery and complete local copies now have their own ticket,
`make-packaged-behavior-discoverable-and-editable`; do not hide that work inside
`skill *`. Authoring migration consumes the launch session boundary, while
classification and promotion design can proceed independently. Drop stale
archive/twin edits, the "thin gh wrapper" assumption and cosmetic alias cleanup.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Close the two residual rows of the "Open command placements" table:

- **`coga ticket`**: write the co-versioning proof for its current head, or
  move it to the edge. The current split is the `bootstrap/ticket` interview
  target, `coga.authoring` finalize (validation and sync after the agent
  exits), and `commands/ticket.py`, the argument-to-draft coordinator that
  calls finalize inline. A plain `launch bootstrap/ticket` alias cannot
  replace it because the head drafts a ticket on the fly and owns the
  post-exit phase.
- **`skill *`**: record its explicit classification as a thin wrapper over
  `gh skill`, either external tooling (extractable as a `gh` extension) or
  a co-versioned package command, with the owner direction recorded.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      classify unnecessary coordinator/wrapper layers as well as placement,
      identify concrete deletions or reuse of existing authoring/finalization
      primitives, and estimate the kernel and total production-code impact.
      Hand implementation to the migration follow-up with that baseline;
      preserve validation and post-exit finalization, and keep `skill *`
      migration outside this classification ticket.

- [ ] `ticket` has a written co-versioning proof in `coga-dev/microkernel`,
      or is moved to the edge with unchanged behavior and tests.
- [ ] `skill *` has an explicit classification and reason in
      `coga-dev/microkernel`.
- [ ] Both rows leave the local-only `coga-dev/microkernel` table;
      `docs/archive/cli-extension-audit.md`, `coga/tickets/authoring`,
      `coga/skill-management` and the `coga/cli` index match.
- [ ] Any migration found here becomes its own follow-up ticket.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Already settled and out of scope (Dream W39 F48): default aliases are argv
sugar; fresh `init` is kernel; `delete` is a thin head over the `delete-task`
recipe; bare `recurring` is a thin head over `recurring-scan`.

##### Premise check (2026-10-16, pull-forward to v1)

- Delivered in part (Dream W39 F48): aliases, `init`, `delete`, bare
  `recurring` are classified in extension-model and the audit. Scope narrowed
  to `ticket` and `skill *`, the two surfaces still in the open table.

Previous ref: `microkernel/residual-command-surfaces` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
