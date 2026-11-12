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

The designs below are stale. `refresh-the-microkernel-designs-against-current-ma`
runs the premise check and refreshes every design first; no child
implementation resumes before the owner accepts that refresh.

At the October 16 pull-forward, each draft was
premise-checked against `main` @ `5d72ffe6e` with the `_v2/README.md`
procedure, reusing Dream 2026-W39 findings F46-F49 and F53 and the W40
correction to F49; each ticket's blackboard records its own outcome.

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
- When a placement changes, update in the same PR the local-only
  `coga-dev/microkernel`, `docs/archive/cli-extension-audit.md`, the
  `coga/cli` index, and the topic that owns the moved command. Update
  packaged twins only for user topics.
- Split implementation by command shape after design review; one PR per
  move.

## Child tickets and order

0. `v1/microkernel/refresh-the-microkernel-designs-against-current-ma` —
   premise-check and refresh every design below; goes first.
0. `v1/microkernel/declare-each-workflow-step-s-checkout-policy-in-th` —
   move step checkout policy from `checkout_policy.py` into workflow files.
   Independent of the command heads; may run in parallel with the refresh.
1. `v1/microkernel/launch-decomposition` — split
   `src/coga/commands/launch.py` into executor substrate plus caller policy.
   Goes first: the others need a stable executor API. Paused at the owner's
   `review-design` gate with a stale inventory; see its blackboard.
2. `v1/microkernel/lifecycle-verbs-to-ticket-operations` — narrowed
   to `block`/`unblock` (kernel by registration, not by the launch-closure
   test) and the `owner` head. `mark` and `bump` stay kernel.
3. `v1/microkernel/work-orchestration-commands-to-tickets` —
   `megalaunch`, `slack`; `retire` is split out to
   `microkernel/move-retire-to-a-command-ticket`.
4. `v1/microkernel/read-report-commands-as-ticket-workflows` —
   `show`, `status`, `validate`, `usage`, `recurring list`.
5. `v1/microkernel/support-commands-boundary` — `secret get`,
   `uninstall`.
6. `v1/microkernel/residual-command-surfaces` — narrowed to `ticket`
   and the `skill *` classification.

Tickets 3-6 can run in parallel once 1 lands.

## Related work

- `v1/microkernel/gigantic-refactor-move-recurring-recipes-out-of-co` (in progress) moves
  single-ticket recurring jobs out of `runner.RECIPES`; part of this group since
  2026-11-12. It owns the recipe registry; the tickets above own command heads. Neither edits the other's
  surface.
- `_v2/marketing/demo-hackability-ask-claude-to-add-a-command-live` (still parked) depends on
  this set: the demo shows a new command landing entirely at the edge.

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
