---
title: Move work orchestration commands to tickets
status: draft
owner: nicktoper
agent: codex
contexts:
  - coga-dev/microkernel/objectives
  - coga-dev/principles
  - coga/megalaunch
  - coga/checkout-cleanup
  - coga/notifications
  - coga/recurring/scheduling
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

Move queue and notification procedure policy into command tickets while
retaining the shared executor, admission and completion primitives they need.
Remaining command heads are `megalaunch` and `slack`; `retire` has already
moved. This refreshed scope is proposed for owner review.

### Objectives advanced

Hackability and ticket ownership: a repo can change queue selection, retry/
drain policy and FYI formatting by editing their tickets and scripts.
Simplification: reuse launch preparation and failure/publication machinery
instead of preserving a second supervisor inside the queue implementation.

### Premise check against main

Snapshot: `49b34b229` (2026-11-12); physical line counts include blanks/comments.

1. `commands/megalaunch.py` (641 lines), `megalaunch.py` (2,311) and
   `commands/slack.py` (94) remain; the `retire` command module is gone.
2. Megalaunch imports `coga.launch`, not `commands/launch.py`. `pick` remains
   an alias. `retire` is already `launch bootstrap/retire --`; its packaged
   script calls the public launch service where it needs an agent session.
3. The current obligations are below. The removed retire follow-up is
   provenance, not an implementation dependency.
4. `953d14094` delivered the retire move. Drop that migration and its stale
   "pending review" branch from this ticket. Queue and FYI placement remain open.

### Current inventory and proposed boundary

| Responsibility | Source | Proposed home |
| --- | --- | --- |
| Interactive picker, saved selection, owner filters, candidate ordering | `commands.megalaunch`, `megalaunch.launchable_candidates`, `save_selection`, `load_selection` | Megalaunch command ticket and script |
| Batch selection, dependency drain, liveness defaults and timeout classification | `run_megalaunch`, `_run_sweep`, `_drain_satisfied_blockers`, `_chain_stop_result` | Queue-owned deterministic policy |
| Activation, re-blocking and per-step preparation | `_activate_for_launch`, `_reblock_unresolved`, `_launch_until_stop` alongside analogous launch paths | Reuse the reviewed shared transition/session boundary; remove real duplication |
| Generation claims, held-child proof, admission/release and recovery | `_revalidate_launch_claim_before_spawn`, `_admit_launch_claim_after_release`, launch's reconciliation | Shared package invariant; expose only the operation needed by the edge queue |
| FYI operands, text and notification choice | `commands.slack.slack` | Script command ticket over shared notification/audit helpers |
| Bootstrap-session completion after a successful FYI | `slack` calls `emit_done_marker` for a bootstrap target | Generic verified completion primitive; coordinate with launch/lifecycle before moving the head |

### Proposed changes

Ship one bootstrap command ticket per moved procedure and use fixed aliases.
Stateless invocations create no tracking task merely to run a command. Queue
policy may create or author real work when that is already its behavior.
Move whole policy implementations, not import-only facades pointing back to
the old core command. Wheel delivery must support the full local fork supplied
by the customization ticket.

Megalaunch must keep durable claims and fresh revalidation around actual child
execution. The presence of those guarantees justifies a shared admission
primitive, not every picker or scheduling choice. Preserve saved selections,
dependency handling, owner skips, failure evidence and native terminal behavior.
The current queue remains agent-oriented; a generic script/agent queue redesign
is separate scope unless required and explicitly accepted during design.

For `slack`, moving only the formatting is straightforward; replacing the
whole head is conditional. A bootstrap script clears an outer supervisor's
sentinel. Its nested invocation therefore cannot currently finish that outer
agent session as the existing head does. Keep completion guarded and explicit;
do not copy ambient authority into the child or drop the completion behavior.
Ordinary task FYIs remain non-terminal, and failed delivery retains its current
failure/audit semantics.

### Acceptance and reduction evidence

- [ ] Each moved procedure has an editable ticket/script and alias; core
      imports neither that implementation nor a repo path to it.
- [ ] Queue policy is separated from actual launch-claim, process, lifecycle
      and publication invariants; retained operations have concrete consumers.
- [ ] At least one duplicated launch preparation/re-block path is removed or
      handed to the launch/lifecycle owner with a precise dependency.
- [ ] `slack` works inside ordinary and bootstrap supervised sessions with
      unchanged completion, streams, failure and audit behavior.
- [ ] Preserve picker behavior on POSIX and Windows; exercise queue claims,
      publication conflicts, failures and dependency drain in existing tests.
- [ ] Report whole-system reduction; update `coga/megalaunch`, notification
      owners, CLI index and local microkernel placement. Apply full Linux and
      native Windows verification where required.

## Context

`launch-decomposition` owns the session/admission API and generic completion
seam; this ticket owns queue policy. The lifecycle sibling owns state operations.
The recurring-recipes sibling owns registry contractions, not this queue.
`recurring promote` is assigned to residual command surfaces; recurring
admission and scheduling are not silently added to this ticket.

Read `coga-dev/microkernel/objectives`, `coga-dev/testing` and the package-owned
topics under `src/coga/resources/templates/coga/bootstrap/contexts/coga/`:
`megalaunch`, `notifications`, `notifications/producers`, `script-tickets`,
`state-publication`, and the launch/checkouts contracts.

Drop the already-shipped retire move, removed digest/project commands and
duplicate live/package definitions. Do not infer current retire behavior from
the old canceled-ticket design. Defer a new queue framework or policy-free
file shuffle that does not serve the objectives.

<!-- coga:blackboard -->

The blackboard is a notepad to be written to often as the human and agent works through a task.

## Superseded designs

### 2026-11-12 — Design before the current-main refresh

Superseded by: the refreshed Description and Context above, proposed for owner review.
Reason: source, distribution and caller boundaries changed; the owner clarified
the objectives in `coga-dev/microkernel/objectives`. Historical commands,
paths, approvals and test receipts below are evidence, not current instructions.

#### Description

Settle the placement of the in-package heads that orchestrate work:
`coga retire`, `coga megalaunch` (and its `pick` alias), and `coga slack`.
Move each head's single-consumer substance to the edge (command ticket,
`ticket.py`, `src/coga_edge/`) behind a thin creator/launcher/alias, or
record why it must be co-versioned with the package.

##### Acceptance criteria

- [ ] Apply the group's [reduction objective](README.md#reduction-objective):
      simplify duplicated launch/orchestration scaffolding and unnecessary
      wrappers in `megalaunch` and `slack` using the shared launch boundary.
      Count their edge implementations in the before/after total; moving
      queue policy out of core alone is a placement gain, not less code to
      maintain. Keep recurring recipes and the executor outside this scope.

- [ ] The design defines one shared creator/launcher/alias pattern for these
      heads, so they do not each invent a migration shape.
- [x] `retire` is split into a concrete follow-up with exact acceptance
      criteria: `microkernel/move-retire-to-a-command-ticket` (2026-10-16).
      Its state rule stays: a canceled ticket gets a retire task; a done
      ticket is deleted in place.
- [ ] `megalaunch` and `slack` are each moved or given a co-versioning proof
      in `coga-dev/microkernel`. Megalaunch's queue selection, liveness
      defaults and timeout classification are caller policy, not executor
      substrate.
- [ ] Implementation is split per command shape after design review.
- [ ] Human-visible side effects stay durable (blackboards, `coga/log.md`,
      sync commits, notifications).
- [ ] The three heads leave (retire through its follow-up) the "Open command placements" table (both
      copies); `coga/megalaunch`, `coga/checkout-cleanup`,
      `coga/notifications` and the `coga/cli` index match; tests pass.
      Retire's exit is implemented on branch `retire-command-ticket`
      (`microkernel/move-retire-to-a-command-ticket`, pending review and
      merge): the row there names only `megalaunch`, `slack`.

#### Context

Group: `microkernel/README.md` (v1 scope since 2026-10-16).

Prior art: `ticket` (command head plus `bootstrap/ticket` and
`coga.authoring` finalize), `bootstrap/recurring-scan`, the `delete-task`
recipe, `bootstrap/resolve-conflicts` and `bootstrap/address-pr-comments`
command tickets reached by aliases.

Depends on `v1/microkernel/launch-decomposition` for a public
one-session API (megalaunch currently imports the session runner out of
`commands/launch.py`). Does not touch `runner.RECIPES`: that registry is
owned by `v1/microkernel/gigantic-refactor-move-recurring-recipes-out-of-co`.

Out of scope: `skill *`, `create`, the launch executor, recurring recipes.

##### Premise check (2026-10-16, pull-forward to v1)

- Subject exists: `src/coga/commands/{retire,megalaunch,slack}.py`,
  `src/coga/megalaunch.py`.
- Stale surfaces removed (Dream W39 F47): `coga digest` (removed by
  `remov-digest-in-recurring`) and `coga project` (removed by
  `remove-coga-build-and-project`). Bare `coga recurring` is already a thin
  head over the `recurring-scan` recipe, so recurring maintenance left scope.
- Not delivered: all three heads are still listed in extension-model's
  "Open command placements".

Previous ref: `microkernel/work-orchestration-commands-to-tickets` (renamed 2026-10-27); earlier audit lines retain that ref. Parked by the owner for v2; this work does not gate v1.

Created under `v2/cleanup-core-commands/` as part of the command-surface breakdown.
