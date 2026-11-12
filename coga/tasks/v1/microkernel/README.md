# Microkernel

V1 group for a ticket-centred microkernel: a small executor runs tickets,
which carry scripts or agent prompts and the workflows and skills they use.
Most user-facing commands become aliases to those tickets. Settling command
placement serves that architecture and a program more people can read.

## Status

Pulled back into v1 by the owner on 2026-11-12: hackability is a base promise
of the open-source 1.0, and a contributor got lost customizing the peer-review
step (the bundled workflow lived only in the package, and the hidden
`checkout_policy.py` table silently dropped a customized step to manual
checkout). The whole group gates `v1/43`: the "Open command placements" table
in `coga-dev/microkernel` must be empty before publication. This supersedes the
2026-10-27 deferral; the decision is recorded in `coga-dev/current-direction`.

The [refresh](01-refresh-the-microkernel-designs-against-current-ma.md) now
proposes revised scopes against `main` at `49b34b229` (2026-11-12). Each child
contains its four-question premise check, source inventory, proposed boundary,
objective contribution, and concrete simplifications. Earlier designs and
review receipts remain in each ticket's Superseded designs section.

These are proposals awaiting owner review. No child implementation resumes
before the owner accepts the refreshed scope; accepting the group does not
advance a child's own frozen workflow or owner gate.

## Objectives (owner, clarified 2026-11-12)

The [microkernel objectives](../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md)
own this group's direction: hackable and accessible behavior, as much behavior
as possible in tickets, and a simpler program people can read. That context
also owns the fresh-repo peer-review acceptance case and the design criteria.

## The boundary

The implemented boundary is owned by `coga-dev/microkernel`. It is the
starting inventory, not a promise that every existing command, recipe, or
caller-specific policy must remain in core. The linked objectives
ask the refresh to propose the smallest useful executor and shared primitives,
with behavior carried by tickets wherever possible. Preserve the current
transaction, completion, and failure guarantees when proposing smaller heads
or moving policy. The owner reviews the concrete retained set before any
child implementation resumes.

The "Open command placements" table in `coga-dev/microkernel` must be empty:
every listed head is moved to a ticket/alias or has a concrete reason to remain
a generic kernel primitive. Closing the table alone is insufficient: the
customization path and whole-program simplification must also meet the
objectives above. Wheel distribution by itself does not make behavior editable.

It is a v1 release prerequisite (owner decision 2026-11-12).

## Reduction objective

The 2026-10-22 reduction objective is retained in the standing context's
[simplification goal](../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md#a-simpler-program-people-can-read)
and [evaluation criteria](../../../../docs/contexts/coga-dev/microkernel/objectives/SKILL.md#evaluating-a-proposed-change).
Use those criteria for each child's design and implementation evidence.

## Ground rules

- Commands operate on durable tickets, not untracked side effects. Keep CLI
  entrypoints thin; move single-consumer substance to the edge.
- Moving logic out of the kernel moves it unchanged (extension-model
  "No inversion"): deterministic Python stays Python.
- When a placement changes, update the local-only `coga-dev/microkernel`,
  the package-owned `coga/cli` index and the owning user contract. Shipped
  definitions have one package owner; local copies are deliberate overrides.
  Archive auditing is not part of this group and requires an explicit request.
- Split implementation by command shape after design review; one PR per
  move.

## Child scopes proposed for review

| Ticket | Current-main verdict and proposed remainder | Objectives advanced |
| --- | --- | --- |
| [Checkout declaration](02-declare-each-workflow-step-s-checkout-policy-in-th.md) | Not shipped. Own the step field, freeze/validation, selection, legacy fallback and workflow guidance; launch only consumes it | Hackability, ticket ownership, simpler policy |
| [Launch decomposition](03-launch-decomposition.md) | Part shipped: the CLI/service split is done. Focus on the shared session boundary, generic stateless command semantics and removal of caller-specific duplication | All three |
| [Recurring recipes](04-gigantic-refactor-move-recurring-recipes-out-of-co.md) | Distribution prerequisite shipped; five job moves remain. Audit all 12 entries and propose a second pass on two command adapters | Ticket ownership, hackability, simpler registry/reporting |
| [Editable packaged behavior](05-make-packaged-behavior-discoverable-and-editable.md) | New gap ticket. Resolve effective sources and obtain complete local overrides, including implementation behind wheel shims | All three |
| [Read/report commands](06-read-report-commands-as-ticket-workflows.md) | Rendering partly shared already. Move report policy only after a generic stateless path preserves read-only behavior | All three |
| [Support commands](07-support-commands-boundary.md) | Secret inspection is an edge candidate; uninstall needs a bounded recovery proof before an ordinary alias can replace it | Ticket ownership, hackability, fewer redundant wrappers |
| [Residual commands](08-residual-command-surfaces.md) | Guided authoring and skill tooling remain; assign the previously unowned `recurring promote` row here | All three |
| [Work orchestration](09-work-orchestration-commands-to-tickets.md) | Retire already moved. Remaining queue/FYI policy must use shared admission and completion primitives | All three |
| [Lifecycle operations](10-lifecycle-verbs-to-ticket-operations.md) | Prepared writes partly delivered. Retain proven transition/completion operations; separate bulk/procedure policy where useful | Smaller kernel responsibility, editable procedure, less duplicate state handling |

The refresh parent accounts for this whole table and its own handoff; the new
accessibility draft is included in scope review, not silently added to execution.

## Proposed execution order

1. **Owner scope review of the refresh.** Confirm the revised boundaries and
   the new accessibility ticket before activating or advancing child work.
2. **Remove the first customization barrier.** Implement checkout declaration
   independently. In the launch ticket, settle the minimal stateless read/write
   and completion requirements with their actual consumers. The initial five
   recurring job moves can proceed independently using the delivered wheel
   mechanism and their own publication/fork tests.
3. **Complete the fresh-user path.** Implement effective-source inspection and
   complete local copying on the generic stateless path, then run the one-agent
   peer-review acceptance case with checkout declaration. This makes the user's
   ability to customize an early deliverable.
4. **Move the bounded command policies.** Read/report and secret inspection
   depend on the stateless contract, not every launch refactor. Authoring uses
   the shared one-session and guarded publication primitives. Classify skills
   and promotion, then choose their bounded implementation follow-ups. Review the remaining recipe
   adapters with the same contracts. Uninstall's recovery proof can proceed
   independently.
5. **Converge the orchestration paths.** Move megalaunch policy after its shared
   admission/session operations are stable. Move any session-ending FYI or
   lifecycle adapter only after verified completion identity survives the
   command-ticket boundary. Lifecycle transaction review and safe bulk-policy
   separation need not wait for a cosmetic module split.

There is no blanket dependency on completing all of launch-decomposition.
Each child owns its detailed dependency and acceptance contract. Splitting the
work this way delivers customization early while retaining the invariants
needed by later moves.

## Related work

- `_v2/marketing/demo-hackability-ask-claude-to-add-a-command-live` (still parked) depends on
  this set: the demo shows a new command landing entirely at the edge.
- `coga/edge-code` owns the already-shipped delivery/fork contract. Its retired
  implementation ticket is no longer a blocking design prerequisite.

## History

- 2026-07: created as the core-command breakdown; parked to `_v2/` on
  2026-07-27 as off the execution path.
- 2026-09-10: `coga digest` removed outright (`remov-digest-in-recurring`).
- `coga project` and `coga build`'s command were removed
  (`remove-coga-build-and-project`); `build` is now an alias.
- 2026-10-16: pulled forward into v1 and renamed from `cleanup-core-commands/`
  to `microkernel/`; older log lines and tickets use the old slugs.
- 2026-10-27: parked under `v1/microkernel/` to focus v1 on first users.
- 2026-11-12: pulled back into v1 as `v1/microkernel/` with the recurring-recipes
  refactor; the whole group gates the 1.0.
- 2026-11-12: objectives moved to their standing Coga-dev owner; refreshed
  child scopes and the accessibility gap are proposed for owner review.
